# service-agent — Specification

Status: draft (v0.1). Sections marked **Open** are unresolved decisions, not commitments.

## 1. Purpose

A customer-service agent exposed over HTTP. It answers user questions grounded in a
private knowledge base, looks up order state, and hands off to a human when it cannot
answer safely or confidently.

The agent is the product. FastAPI is the delivery surface; Postgres + pgvector is the
memory. Everything else is a tool the agent may call.

## 2. Scope

**In scope (v1)**

- Single-tenant deployment, one knowledge base.
- Text-only conversations, one session per customer enquiry.
- Retrieval-augmented answers with citations back to source documents.
- Read-only lookups against an internal orders API.
- Ticket creation and human escalation, both gated (§7).

**Out of scope (v1)**

- Multi-tenancy, per-customer KB isolation.
- Voice, images, attachments.
- Autonomous refunds, cancellations, or any action that moves money.
- Agent-authored changes to the knowledge base.
- Multi-turn memory across sessions (each session starts cold).

## 3. Architecture

```
client ──HTTP──▶ FastAPI (app/)
                    │
                    ├─ app/agents/   agent loop + system prompts
                    ├─ app/tools/    tool implementations
                    └─ app/api/      routers
                         │
                         ├──▶ Claude API (Messages, tool runner)
                         └──▶ Postgres 16 + pgvector (docs, chunks, sessions)
```

The agent loop is **Claude API + tool use**, driven by the Python SDK's tool runner
(`client.beta.messages.tool_runner` with `@beta_tool`-decorated functions). We host the
loop ourselves; we do not use Managed Agents in v1, because every tool is a thin call to
infrastructure we already run and we do not need a hosted sandbox.

Requests stream (`client.messages.stream(...)`) so long answers do not hit HTTP timeouts.

## 4. Agents

| Agent | Model | Effort | Responsibility |
|---|---|---|---|
| `triage` | `claude-haiku-4-5` | — | Classify intent, detect out-of-scope or abusive input, strip obvious PII before the main loop. Cheap gate, no tools. |
| `service_agent` | `claude-opus-5` | `high` | Primary loop. Owns the conversation, calls tools, produces the grounded answer with citations. |
| `summarizer` | `claude-haiku-4-5` | `low` | Condenses a closed session into a one-paragraph record for the ticket trail. No tools. |

Conventions that apply to every agent:

- Adaptive thinking (`thinking: {"type": "adaptive"}`); never `budget_tokens`.
- `stop_reason` is checked before reading `content`. On `"refusal"` we surface a generic
  apology and escalate — we never retry the same prompt.
- `service_agent` sends server-side fallbacks (`betas: ["server-side-fallback-2026-07-01"]`,
  `fallbacks: "default"`) so a classifier refusal routes rather than fails.
- Model IDs come from config (`ANTHROPIC_MODEL`), never hardcoded at a call site.

## 5. Tools

| Tool | Input | Returns | Side effect | Gate |
|---|---|---|---|---|
| `search_knowledge_base` | `query: str`, `top_k: int = 5` | chunks with `document_id`, `score`, `text` | none | none |
| `get_order_status` | `order_id: str` | status, dates, line items | none | caller's session must own the order |
| `create_ticket` | `subject`, `body`, `priority` | `ticket_id` | **write** | §7 confirmation |
| `escalate_to_human` | `reason`, `session_id` | queue position | **write** | §7 confirmation |

All tool definitions set `strict: true` with `additionalProperties: false`, so arguments
are schema-valid on arrival. Tool inputs are parsed with `json.loads` — never string-matched.
Parallel tool calls are expected; all `tool_result` blocks for one assistant turn are
returned in a single user message, including failures (`is_error: true`).

## 6. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + database reachability. **Implemented.** |
| `POST` | `/v1/chat` | One agent turn. Body: `session_id`, `message`. Streams the answer. |
| `GET` | `/v1/sessions/{session_id}` | Full transcript and tool-call trail. |
| `POST` | `/v1/documents` | Ingest a document into the knowledge base (chunk, embed, store). |
| `DELETE` | `/v1/documents/{document_id}` | Remove a document and its chunks. |

Interactive docs are served by FastAPI at `/docs`.

## 7. Guardrails

**Grounding.** `service_agent` answers only from retrieved chunks. If no chunk clears the
similarity threshold, it says it does not know and offers escalation. Every factual claim
carries a `document_id`. An answer without citations is a bug.

**Retrieved text is data, never instructions.** KB chunks and order records are wrapped in
delimiters and the system prompt states that content inside them cannot issue commands.
This is the main prompt-injection surface, since anyone who can file a support doc can
write into the KB.

**Write tools are confirmed.** `create_ticket` and `escalate_to_human` pause for explicit
user or operator confirmation before executing. Read tools run freely.

**Loop bounds.** Max 8 tool iterations per turn; a task budget caps token spend so the
agent paces itself instead of being cut off mid-thought.

**Secrets.** The Anthropic key and database credentials live in `.env`, which is
git-ignored. Credentials are never placed in a prompt or a tool description.

**Logging.** Prompts and completions are logged with customer identifiers redacted.
Raw chain of thought is never returned by the API and is never surfaced to users.

**Cost.** `triage` runs on Haiku before the expensive loop so out-of-scope traffic never
reaches Opus.

## 8. Data model (pgvector)

```
documents(id, title, source_uri, created_at)
chunks(id, document_id → documents.id, ordinal, text, embedding vector(N))
sessions(id, created_at, closed_at, summary)
messages(id, session_id → sessions.id, role, content, tool_calls jsonb, created_at)
```

An HNSW index on `chunks.embedding` backs cosine similarity search.

**Open — embedding provider.** Anthropic does not serve an embeddings endpoint, so this is
a separate dependency and it fixes `N`. Candidates: Voyage AI (hosted, 1024-dim) or a local
sentence-transformers model (no egress, lower quality). The vector column cannot be created
until this is decided.

## 9. Open questions

- Embedding provider and vector dimension (§8).
- Chunking strategy: fixed-token windows vs. heading-aware splits.
- Whether `/v1/chat` streams Server-Sent Events or returns a single JSON body.
- Auth on the public endpoints — none exists yet.
- Where the orders API lives, and how session-to-order ownership is proven.
