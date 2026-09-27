from pathlib import Path

from sqlalchemy import text

from app.db import engine
from app.embeddings import get_embedder

MANUALS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "manuals"
BATCH_SIZE = 50

# Parsing the manual files to extract metadata and body content

def parse_manual(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    codes = meta.get("service_codes", "").strip("[]")
    meta["service_codes"] = [c.strip() for c in codes.split(",") if c.strip()]
    return meta, body

# output will be tuple of (metadata dict, body string)


def split_sections(body: str) -> list[tuple[str, str]]:
    sections = []
    heading, lines = None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading and "".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif heading:
            lines.append(line)
    if heading and "".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))
    return sections

def build_chunks() -> list[dict]:
    chunks = []
    for path in sorted(MANUALS_DIR.glob("*.md")):
        meta, body = parse_manual(path)
        for heading, content in split_sections(body):
            chunks.append({
                "doc_id": meta["doc_id"],
                "title": meta["title"],
                "category": meta["category"],
                "service_codes": meta["service_codes"],
                "heading": heading,
                "content": content,
                "embed_text": f"{meta['title']} — {heading}\n{content}",
            })
    return chunks

def embed_all(texts: list[str]) -> list[list[float]]:
    embedder = get_embedder()
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors.extend(embedder.embed(texts[i:i + BATCH_SIZE]))
    return vectors

def main() -> None:
    chunks = build_chunks()
    vectors = embed_all([c["embed_text"] for c in chunks])
    dimensions = get_embedder().dimensions
  
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS manual_chunks"))
        conn.execute(text(f"""
            CREATE TABLE manual_chunks (
                id            serial PRIMARY KEY,
                doc_id        text NOT NULL,
                title         text NOT NULL,
                category      text,
                service_codes text[] NOT NULL,
                heading       text NOT NULL,
                content       text NOT NULL,
                embedding     vector({dimensions}) NOT NULL
            )
        """))
        conn.execute(
            text("""
                INSERT INTO manual_chunks
                    (doc_id, title, category, service_codes, heading, content, embedding)
                VALUES
                    (:doc_id, :title, :category, :service_codes, :heading, :content,
                     CAST(:embedding AS vector))
            """),
            [
                {
                    "doc_id": c["doc_id"], "title": c["title"], "category": c["category"],
                    "service_codes": c["service_codes"], "heading": c["heading"],
                    "content": c["content"], "embedding": str(v),
                }
                for c, v in zip(chunks, vectors)
            ],
        )
    print(f"ingested {len(chunks)} chunks from {len(set(c['doc_id'] for c in chunks))} manuals "
          f"(dimensions={dimensions})")


if __name__ == "__main__":
    main()
