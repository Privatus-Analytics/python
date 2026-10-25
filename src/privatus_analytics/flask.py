"""Flask extension.

    from privatus_analytics.flask import PrivatusAnalytics

    app.config["PRIVATUS_ANALYTICS"] = {"site_id": "pa_YOURSITEID"}
    PrivatusAnalytics(app)

The tag prints only when the app is not in debug or testing mode, unless the
``enabled`` setting says otherwise.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from flask import Flask, Response, current_app, request

from privatus_analytics.core import Config, SafeHTML, inject_tag, should_inject
from privatus_analytics.jinja import install, render_for_request

CONFIG_KEY = "PRIVATUS_ANALYTICS"


class PrivatusAnalytics:
    """Adds the template globals and the optional auto inject hook to a Flask app."""

    def __init__(self, app: Optional[Flask] = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.extensions["privatus_analytics"] = self
        install(app.jinja_env, self.config)
        app.after_request(self._after_request)

    def config(self, app: Optional[Flask] = None) -> Config:
        """The settings for the current app, read from ``app.config["PRIVATUS_ANALYTICS"]``."""
        app = app or current_app
        config = Config.from_mapping(app.config.get(CONFIG_KEY))
        if config.enabled is None:
            config = dataclasses.replace(config, enabled=not (app.debug or app.testing))
        return config

    def tag(self, **overrides: Any) -> SafeHTML:
        """The tag for the current request, for use outside templates."""
        return render_for_request(self.config(), request, **overrides)

    def _after_request(self, response: Response) -> Response:
        config = self.config()
        if not config.auto_inject or response.is_streamed or response.direct_passthrough:
            return response
        if not should_inject(
            response.status_code,
            response.headers.get("Content-Type"),
            response.headers.get("Content-Encoding"),
            request.headers.get("X-Requested-With"),
        ):
            return response
        tag = render_for_request(config, request)
        if not tag:
            return response
        document = response.get_data(as_text=True)
        updated = inject_tag(document, tag)
        if updated is not document:
            response.set_data(updated)
        return response
