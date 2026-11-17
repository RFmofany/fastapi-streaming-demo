# FastAPI Streaming Demo

A small demo of three streaming patterns in FastAPI:

1. **Token stream over SSE** — `POST /api/chat/stream` sends one `data:` event per token, then `data: [DONE]`.
2. **Line stream** — `GET /api/numbers/stream?count=20` streams newline-delimited JSON.
3. **File stream** — `GET /api/export/stream?rows=1000` streams a generated CSV with `Content-Disposition: attachment`, so the download starts before the file is fully built.

The browser page at `/` consumes the SSE endpoint with `fetch()` + `ReadableStream` and prints tokens as they arrive.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/`.

## Test

```bash
python -m pytest -q
```

Result on my machine:

```text
.....                                                                    [100%]
5 passed in 1.55s
```

The tests cover the health check, SSE ordering and `[DONE]` termination, the missing-prompt path, NDJSON output, and CSV streaming headers/rows.

## Notes

- The token generator is deliberately fake (`fake_llm`) so the demo has no external API dependency. It yields one word every 40 ms, which is enough to see the transport behavior.
- `X-Accel-Buffering: no` is set so Nginx-style proxies do not buffer the SSE stream.
- The CSV generator uses `await asyncio.sleep(0)` every 500 rows to yield control back to the event loop; without that a huge export would block the server while building the string.
- `StreamingResponse` is used for all three endpoints; no WebSocket, because the requirement is a streaming HTTP API.
