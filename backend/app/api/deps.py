"""Container access for routes, set once at startup and injected by FastAPI."""

from __future__ import annotations

from fastapi import Request

from app.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
