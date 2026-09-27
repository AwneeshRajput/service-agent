import pytest

from app.db import SessionLocal
from app.rag.retriever import search

CASES = [
    ("my brakes are grinding", "brakes"),
    ("car won't start, it just clicks", "battery-12v"),
    ("the AC is blowing warm air", "air-conditioning"),
    ("check engine light is flashing", "engine-warning-light"),
    ("tyre is wearing on the inside edge", "tyres"),
    ("clunking noise over bumps", "suspension"),
    ("gearbox slips when I accelerate", "transmission"),
]


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.mark.parametrize("question, expected_doc", CASES)
def test_search_finds_right_manual(db, question, expected_doc):
    results = search(db, question, k=3)
    assert expected_doc in [r["doc_id"] for r in results]
