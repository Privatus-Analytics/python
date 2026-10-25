"""Optional middleware that adds the tag before ``</head>``.

Add ``"privatus_analytics.django.middleware.PrivatusAnalyticsMiddleware"`` to
``MIDDLEWARE`` and set ``"auto_inject": True``. Put it below ``GZipMiddleware``
in the list so it runs before the response is compressed.
"""

from __future__ import annotations

from typing import Any, Callable

from privatus_analytics.core import inject_tag, should_inject
from privatus_analytics.django import get_config, render


class PrivatusAnalyticsMiddleware:
    def __init__(self, get_response: Callable[[Any], Any]) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        response = self.get_response(request)
        config = get_config()
        if not config.auto_inject or getattr(response, "streaming", False) or not config.should_render():
            return response
        if not should_inject(
            response.status_code,
            response.get("Content-Type"),
            response.get("Content-Encoding"),
            request.headers.get("X-Requested-With"),
        ):
            return response

        charset = getattr(response, "charset", None) or "utf-8"
        try:
            document = response.content.decode(charset)
        except (LookupError, UnicodeDecodeError):
            return response
        updated = inject_tag(document, render(request))
        if updated is not document:
            response.content = updated.encode(charset)
            response["Content-Length"] = str(len(response.content))
        return response
