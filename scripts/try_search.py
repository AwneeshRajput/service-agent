import sys

from app.db import SessionLocal
from app.rag.retriever import search

with SessionLocal() as db:
    for r in search(db, " ".join(sys.argv[1:]), k=3):
        print(f"{r['score']:.3f}  {r['doc_id']:22} {r['heading']}")
