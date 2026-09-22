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
                         ├──▶ OpenAI API (chat + function calling, embeddings)
                         └──▶ Postgres 16 + pgvector (docs, chunks, sessions)
```

The agent loop is **OpenAI function calling with a loop we own**: send the conversation
plus tool schemas, execute any tool calls the model returns, append the results, repeat
until the model answers without calling a tool. Owning the loop keeps the guardrails in
§7 (confirmation gates, iteration caps) in our code rather than a framework's.

Answers stream so long responses do not hit HTTP timeouts.

## 4. Agents

| Agent | Model (config key) | Responsibility |
|---|---|---|
| `triage` | `OPENAI_FAST_MODEL` (`gpt-5.4-mini`) | Classify intent, detect out-of-scope or abusive input, strip obvious PII before the main loop. Cheap gate, no tools. |
| `service_agent` | `OPENAI_MODEL` (`gpt-5.5`) | Primary loop. Owns the conversation, calls tools, produces the grounded answer with citations. |
| `summarizer` | `OPENAI_FAST_MODEL` (`gpt-5.4-mini`) | Condenses a closed session into a one-paragraph record for the ticket trail. No tools. |

Conventions that apply to every agent:

- The finish reason is checked before reading output. A refusal or content-filter stop
  surfaces a generic apology and escalates — we never retry the same prompt.
- Model IDs come from config, never hardcoded at a call site, so swapping models is an
  `.env` change.

## 5. Tools

| Tool | Input | Returns | Side effect | Gate |
|---|---|---|---|---|
| `search_knowledge_base` | `query: str`, `top_k: int = 5` | chunks with `document_id`, `score`, `text` | none | none |
| `get_order_status` | `order_id: str` | status, dates, line items | none | caller's session must own the order |
| `create_ticket` | `subject`, `body`, `priority` | `ticket_id` | **write** | §7 confirmation |
| `escalate_to_human` | `reason`, `session_id` | queue position | **write** | §7 confirmation |

All function schemas set `strict: true` with `additionalProperties: false`, so arguments
are schema-valid on arrival. Arguments are parsed with `json.loads` — never string-matched.
Parallel tool calls are expected; every call gets a result keyed to its call ID, including
failures, which return an error payload rather than being dropped.

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

**Loop bounds.** Max 8 tool iterations per turn and a per-turn token ceiling. Hitting
either ends the turn with an escalation offer, not a truncated answer.

**Secrets.** The OpenAI key and database credentials live in `.env`, which is
git-ignored. Credentials are never placed in a prompt or a tool description.

**Logging.** Prompts and completions are logged with customer identifiers redacted.

**Cost.** `triage` runs on the fast model before the expensive loop so out-of-scope
traffic never reaches the main model.

## 8. Data model (pgvector)

```
documents(id, title, source_uri, created_at)
chunks(id, document_id → documents.id, ordinal, text, embedding vector(1536))
sessions(id, created_at, closed_at, summary)
messages(id, session_id → sessions.id, role, content, tool_calls jsonb, created_at)
```

Embeddings come from OpenAI `text-embedding-3-small` (1536 dimensions, config key
`OPENAI_EMBEDDING_MODEL`). An HNSW index on `chunks.embedding` backs cosine similarity
search. Changing the embedding model changes the dimension and requires re-embedding
every chunk, so treat it as a migration, not a config tweak.

## 9. Open questions

- Chunking strategy: fixed-token windows vs. heading-aware splits.
- Whether `/v1/chat` streams Server-Sent Events or returns a single JSON body.
- Auth on the public endpoints — none exists yet.
- Where the orders API lives, and how session-to-order ownership is proven.
