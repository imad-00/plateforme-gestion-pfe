import pytest
from django.db import connection


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/api/health/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["database"] == "ok"


def test_docs_endpoint(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_database_connection():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        row = cursor.fetchone()

    assert row == (1,)
