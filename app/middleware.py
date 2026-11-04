"""Bound request bodies before multipart parsing can consume unbounded storage."""

from fastapi import HTTPException
from starlette.responses import JSONResponse


class StaticCacheMiddleware:
    """Make browsers revalidate static assets so UI fixes appear on reload."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/static/"):
            return await self.app(scope, receive, send)

        async def revalidating_send(message):
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                headers.append((b"cache-control", b"no-cache"))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, revalidating_send)


class BodySizeLimitMiddleware:
    def __init__(self, app, limit=11 * 1024 * 1024):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in {
            "POST",
            "PUT",
            "PATCH",
        }:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = -1
        if length < 0 or length > self.limit:
            response = JSONResponse(
                {"detail": "Request body exceeds the 11 MB transport limit."},
                status_code=413,
                headers={"Cache-Control": "no-store"},
            )
            return await response(scope, receive, send)
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.limit:
                    raise HTTPException(
                        413, "Request body exceeds the 11 MB transport limit."
                    )
            return message

        await self.app(scope, bounded_receive, send)
