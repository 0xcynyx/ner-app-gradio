import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

SAMPLE = "Joko Widodo lahir di Surakarta, HP 081234567890, NIK 3204012509900001"


@pytest.fixture()
def client(monkeypatch):
    """Boot the app against the rule based backend so tests need no model."""
    monkeypatch.setenv("NER_BACKEND", "fake")
    monkeypatch.setenv("NER_FRONTEND_DIR", "does-not-exist")
    with TestClient(create_app()) as instance:
        yield instance


def test_health_reports_the_active_backend(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["backend"] == "fake"


def test_meta_exposes_labels_strategies_and_formats(client):
    body = client.get("/api/meta").json()
    assert {"PER", "LOC", "EMAIL", "PHONE", "SSN", "GENDER", "DATE_TIME"} == {
        item["code"] for item in body["labels"]
    }
    assert "pseudonym" in body["strategies"]
    assert "csv" in body["formats"]


def test_analyze_returns_entities_with_valid_offsets(client):
    body = client.post("/api/analyze", json={"text": SAMPLE}).json()
    assert body["stats"]["total"] > 0
    for entity in body["entities"]:
        assert body["text"][entity["start"] : entity["end"]] == entity["text"]


def test_analyze_finds_the_structured_identifiers(client):
    body = client.post("/api/analyze", json={"text": SAMPLE}).json()
    labels = {entity["label"] for entity in body["entities"]}
    assert {"PHONE", "SSN"} <= labels


def test_empty_text_is_accepted_and_empty(client):
    body = client.post("/api/analyze", json={"text": ""}).json()
    assert body["entities"] == []


def test_redact_removes_the_identifiers(client):
    body = client.post("/api/redact", json={"text": SAMPLE, "strategy": "label"}).json()
    assert "081234567890" not in body["text"]
    assert body["replaced"] > 0


def test_redact_rejects_unknown_strategy(client):
    assert client.post("/api/redact", json={"text": SAMPLE, "strategy": "bogus"}).status_code == 422


def test_batch_processes_each_document(client):
    payload = {"items": [{"id": "a", "text": SAMPLE}, {"id": "b", "text": "tidak ada apa apa"}]}
    body = client.post("/api/batch", json=payload).json()
    assert body["documents"] == 2
    assert [item["id"] for item in body["items"]] == ["a", "b"]


def test_batch_over_the_limit_is_rejected(client, monkeypatch):
    items = [{"id": str(i), "text": "x"} for i in range(200)]
    assert client.post("/api/batch", json={"items": items}).status_code == 422


def test_export_returns_a_csv_attachment(client):
    response = client.post("/api/export", json={"text": SAMPLE, "format": "csv"})
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert "label,text" in response.text.replace(" ", "")


def test_export_rejects_unknown_format(client):
    assert client.post("/api/export", json={"text": SAMPLE, "format": "xml"}).status_code == 422


def test_upload_txt_treats_each_line_as_a_document(client):
    files = {"file": ("docs.txt", "Joko di Bandung\nemail a@b.co\n", "text/plain")}
    body = client.post("/api/upload", files=files).json()
    assert body["documents"] == 2


def test_upload_csv_uses_the_text_column(client):
    csv_body = "id,text\n1,Joko di Bandung\n2,HP 081234567890\n"
    files = {"file": ("docs.csv", csv_body, "text/csv")}
    body = client.post("/api/upload", files=files).json()
    assert body["documents"] == 2
    assert body["entities"] > 0


def test_upload_without_rows_is_rejected(client):
    files = {"file": ("empty.txt", "\n\n", "text/plain")}
    assert client.post("/api/upload", files=files).status_code == 422


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("NER_MIN_SCORE", "0.75")
    monkeypatch.setenv("NER_CORS_ORIGINS", "https://a.test, https://b.test")
    settings = Settings.load()
    assert settings.min_score == 0.75
    assert settings.origins() == ["https://a.test", "https://b.test"]
