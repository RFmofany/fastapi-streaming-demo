import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(title="Streaming API Demo", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent


def sse(payload: dict | str) -> str:
    data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n"


async def fake_llm(prompt: str):
    """Just enough of a token stream to exercise the transport layer."""
    answer = (
        f"You asked: {prompt}\n"
        "This response is produced chunk by chunk on the server, "
        "so the client can render it before the request finishes."
    )
    for index, word in enumerate(answer.split(" ")):
        await asyncio.sleep(0.04)
        yield {"index": index, "delta": word + (" " if index < len(answer.split(" ")) - 1 else "")}


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat/stream")
async def chat_stream(body: dict):
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return StreamingResponse(
            iter([sse({"error": "prompt is required"}), sse("[DONE]")]),
            media_type="text/event-stream",
            status_code=400,
        )

    async def event_generator():
        try:
            async for chunk in fake_llm(prompt):
                yield sse(chunk)
            yield sse("[DONE]")
        except asyncio.CancelledError:
            # Client went away; stop producing.
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/numbers/stream")
async def numbers_stream(count: int = Query(default=20, ge=1, le=200)):
    async def generate():
        for i in range(count):
            await asyncio.sleep(0.02)
            yield f"{i}\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/api/export/stream")
async def export_stream(rows: int = Query(default=1000, ge=1, le=100000)):
    """Stream a generated CSV so the browser can start downloading immediately."""

    async def generate():
        yield "id,name,score\n"
        for i in range(rows):
            if i % 500 == 0:
                await asyncio.sleep(0)
            yield f"{i},user-{i},{i % 100}\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="scores.csv"'},
    )
