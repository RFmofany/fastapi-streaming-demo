import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_stream_returns_ordered_sse_chunks():
    with client.stream("POST", "/api/chat/stream", json={"prompt": "hello"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        body = "".join(response.iter_text())

    events = [line[6:] for line in body.split("\n\n") if line.startswith("data: ")]
    assert events[-1] == "[DONE]"
    chunks = [json.loads(event) for event in events[:-1]]
    assert len(chunks) >= 10
    assert [chunk["index"] for chunk in chunks] == list(range(len(chunks)))
    combined = "".join(chunk["delta"] for chunk in chunks)
    assert "You asked: hello" in combined


def test_chat_stream_requires_prompt():
    with client.stream("POST", "/api/chat/stream", json={"prompt": ""}) as response:
        assert response.status_code == 400
        body = "".join(response.iter_text())
    assert "prompt is required" in body


def test_numbers_stream_is_ndjson():
    response = client.get("/api/numbers/stream?count=5")
    assert response.status_code == 200
    assert response.text.splitlines() == ["0", "1", "2", "3", "4"]


def test_export_stream_has_csv_headers_and_rows():
    response = client.get("/api/export/stream?rows=10")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="scores.csv"'
    lines = response.text.strip().splitlines()
    assert lines[0] == "id,name,score"
    assert len(lines) == 11
    assert lines[1] == "0,user-0,0"
