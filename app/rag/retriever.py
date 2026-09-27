from langfuse import observe
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.embeddings import get_embedder

@observe(name="search_manuals")
def search(db: Session, question: str, k: int = 3) -> list[dict]:
    query_vector = str(get_embedder().embed([question])[0])
    rows = db.execute(
        text("""
            SELECT doc_id, title, heading, content, service_codes,
                   1 - (embedding <=> CAST(:q AS vector)) AS score
            FROM manual_chunks
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :k
        """),
        {"q": query_vector, "k": k},
    ).mappings().all()
    return [dict(row) for row in rows]