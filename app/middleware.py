"""Bound request bodies before multipart parsing can consume unbounded storage."""

from fastapi import HTTPException
from starlette.responses import JSONResponse


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
