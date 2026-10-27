"""The web layer (FastAPI) over `Demo`. Needs the optional `demo` extra: `uv pip install -e '.[demo]'`."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from picture_guard.demo.core import Demo, Limited, Rejected

STATIC = Path(__file__).resolve().parent / "static"


def visitor_of(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown"))


def create_app(demo: Demo, wake=None) -> FastAPI:
    app = FastAPI(title="Picture guard demo", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/", response_class=HTMLResponse)
    def page():
        return HTMLResponse((STATIC / "index.html").read_text(), headers={"Cache-Control": "no-store"})

    @app.get("/api/info")
    def info():
        return demo.info()

    @app.get("/api/sample/{name}")
    def sample(name: str):
        try:
            data = demo.sample_bytes(name)
        except Rejected:
            return JSONResponse({"error": "no such sample"}, status_code=404)
        return Response(data, media_type="image/png" if name.endswith(".png") else "image/jpeg")

    @app.post("/api/wake")
    def wake_models(request: Request):
        """Starts the GPU container while the visitor picks a picture. At most once every 3 minutes for the whole demo."""
        import time
        if wake is None or time.time() - demo.last_wake < 180:
            return {"woken": False}
        demo.last_wake = time.time()
        wake()
        return {"woken": True}

    @app.post("/api/protect")
    async def protect(request: Request, file: UploadFile | None = File(None), sample: str | None = Form(None)):
        try:
            if sample:
                data = demo.sample_bytes(sample)
            elif file is not None:
                data = await file.read(demo.info()["max_bytes"] + 1)
            else:
                raise Rejected("send a file or pick a sample")
            events = demo.protect_events(data, visitor_of(request))
            first = next(events)  # the checks run here, so a refusal is a proper HTTP error
        except Rejected as ex:
            return JSONResponse({"error": str(ex)}, status_code=400)
        except Limited as ex:
            return JSONResponse({"error": str(ex)}, status_code=429)

        def stream():
            yield json.dumps(first) + "\n"
            for ev in events:
                yield json.dumps(ev) + "\n"
        return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})

    @app.post("/api/ask")
    async def ask(request: Request):
        body = await request.json()
        try:
            return demo.ask(str(body.get("session", "")), str(body.get("question", "")), visitor_of(request))
        except Rejected as ex:
            return JSONResponse({"error": str(ex)}, status_code=400)
        except Limited as ex:
            return JSONResponse({"error": str(ex)}, status_code=429)

    return app
