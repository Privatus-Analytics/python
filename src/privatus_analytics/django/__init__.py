"""Django app. Add ``"privatus_analytics.django"`` to ``INSTALLED_APPS``.

Settings go in ``PRIVATUS_ANALYTICS = {...}``. The tag prints only when
``DEBUG`` is off, unless the ``enabled`` setting says otherwise.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from privatus_analytics._request import find_nonce
from privatus_analytics.core import Config, SafeHTML, render_tag


def get_config() -> Config:
    """The settings from ``settings.PRIVATUS_ANALYTICS``, read fresh on every call."""
    from django.conf import settings

    config = Config.from_mapping(getattr(settings, "PRIVATUS_ANALYTICS", None))
    if config.enabled is None:
        config = dataclasses.replace(config, enabled=not settings.DEBUG)
    return config


def render(request: Any = None, context_nonce: Any = None, **overrides: Any) -> SafeHTML:
    """The tag for one request, with the CSP nonce from django-csp or Django when there is one."""
    if not overrides.get("nonce"):
        nonce = find_nonce(request, context_nonce)
        if nonce:
            overrides["nonce"] = nonce
    return render_tag(get_config(), request=request, **overrides)
