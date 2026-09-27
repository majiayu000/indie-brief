from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from indie_brief.auth import authorized, presented_token
from indie_brief.config import Settings
from indie_brief.errors import BriefError
from indie_brief.models import Feed
from indie_brief.rank import apply_focus, split_focus
from indie_brief.store import read_latest


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="indie-brief", version="0.1.0")

    @app.exception_handler(BriefError)
    def handle_brief_error(_request: Request, exc: BriefError) -> JSONResponse:
        status = 404 if exc.code == "NO_SNAPSHOT" else 400
        return JSONResponse(
            status_code=status,
            content={"code": exc.code, "message": exc.message},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/today", response_model=Feed)
    def today(
        focus: str = "",
        authorization: Annotated[str | None, Header()] = None,
    ) -> Feed:
        if not authorized(presented_token(authorization), settings.api_keys):
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "缺少有效的 API key"},
            )
        return apply_focus(read_latest(settings.data_dir), split_focus(focus))

    return app
