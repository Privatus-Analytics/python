"""Starlette and FastAPI support: a Jinja2Templates helper and an ASGI middleware.

    from fastapi.templating import Jinja2Templates
    from privatus_analytics import Config
    from privatus_analytics.starlette import PrivatusAnalyticsMiddleware, setup_templates

    config = Config(site_id="pa_YOURSITEID")
    templates = setup_templates(Jinja2Templates(directory="templates"), config)
    app.add_middleware(PrivatusAnalyticsMiddleware, config=config)  # optional auto inject

The middleware is plain ASGI, so it works with any ASGI app.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, MutableMapping, Optional

from privatus_analytics.core import Config, inject_tag, should_inject
from privatus_analytics.jinja import ConfigSource, config_getter, install, render_for_request

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def setup_templates(templates: Any, config: ConfigSource = None) -> Any:
    """Adds the Privatus template globals and filters to a ``Jinja2Templates`` object."""
    install(templates.env, config)
    return templates


def _request_for(scope: Scope) -> Any:
    try:
        from starlette.requests import Request
    except ImportError:  # pragma: no cover - plain ASGI without Starlette
        return scope
    return Request(scope)


def _header(headers: Any, name: bytes) -> Optional[str]:
    for key, value in headers or []:
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class PrivatusAnalyticsMiddleware:
    """Adds the script tag just before ``</head>`` in HTML responses.

    Does nothing unless the ``auto_inject`` setting is ``True``.
    """

    def __init__(self, app: ASGIApp, config: ConfigSource = None) -> None:
        self.app = app
        self.get_config = config_getter(config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        config = self.get_config()
        if scope["type"] != "http" or not config.auto_inject or not config.should_render():
            await self.app(scope, receive, send)
            return

        requested_with = _header(scope.get("headers"), b"x-requested-with")
        start: Optional[Message] = None
        chunks: list[bytes] = []
        passthrough = False

        async def wrapped_send(message: Message) -> None:
            nonlocal start, passthrough
            if passthrough:
                await send(message)
                return
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                if should_inject(
                    message["status"],
                    _header(headers, b"content-type"),
                    _header(headers, b"content-encoding"),
                    requested_with,
                ):
                    start = message
                else:
                    passthrough = True
                    await send(message)
                return
            if message["type"] != "http.response.body" or start is None:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if message.get("more_body", False):
                return
            await self._finish(scope, config, start, b"".join(chunks), send)

        await self.app(scope, receive, wrapped_send)

    async def _finish(self, scope: Scope, config: Config, start: Message, body: bytes, send: Send) -> None:
        charset = "utf-8"
        content_type = _header(start.get("headers"), b"content-type") or ""
        for part in content_type.split(";")[1:]:
            key, _, value = part.strip().partition("=")
            if key.lower() == "charset" and value:
                charset = value.strip("\"'")
        try:
            document = body.decode(charset)
        except (LookupError, UnicodeDecodeError):
            document = None
        if document is not None:
            tag = render_for_request(config, _request_for(scope))
            updated = inject_tag(document, tag)
            if updated is not document:
                body = updated.encode(charset)
        headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
        headers.append((b"content-length", str(len(body)).encode("latin-1")))
        await send({**start, "headers": headers})
        await send({"type": "http.response.body", "body": body, "more_body": False})
