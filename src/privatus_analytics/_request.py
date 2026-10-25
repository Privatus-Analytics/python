"""Small helpers shared by the framework integrations."""

from __future__ import annotations

from typing import Any, Optional


def find_nonce(request: Any = None, context_nonce: Any = None) -> Optional[str]:
    """Finds the Content Security Policy nonce the framework made for this request.

    Looks at a ``csp_nonce`` template value first (Django 6, Flask-Talisman),
    then ``request.csp_nonce`` (django-csp, Flask-Talisman), then
    ``request.state.csp_nonce`` (Starlette and FastAPI).
    """
    for value in (
        context_nonce,
        getattr(request, "csp_nonce", None),
        getattr(getattr(request, "state", None), "csp_nonce", None),
    ):
        if callable(value):
            value = value()
        if value:
            return str(value)
    return None
