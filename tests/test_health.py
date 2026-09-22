from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app


class BrokenSession:
    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "development", "database": "ok"}


def test_health_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"
