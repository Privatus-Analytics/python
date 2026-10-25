"""Conformance example app for privatus-analytics (Flask).

Built by the conformance suite (https://github.com/Privatus-Analytics/conformance).
See its CONTRACT.md for what each route must render. The site id and script
host come from PRIVATUS_SITE_ID and PRIVATUS_SCRIPT_HOST.
"""

from __future__ import annotations

import os

from flask import Flask, Response, render_template, request

from privatus_analytics.flask import PrivatusAnalytics

PAGE_PROPS = {"plan": "pro", "role": "admin", "beta": True, "seats": 3}
NASTY = "</script><script>window.__pwned=1</script>\u2028\u2029&<>\"'"
NONCE = "testnonce"
SCRIPT_HOST = os.environ.get("PRIVATUS_SCRIPT_HOST", "https://privatusstats.com").rstrip("/")

AUTO_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Auto inject</title>
</head>
<body><h1>Auto inject</h1><p>No tag in the template. The middleware adds it.</p></body>
</html>
"""


def create_app(*, auto_inject: bool = False) -> Flask:
    app = Flask(__name__)
    # Forced on, so the tag prints whatever the environment.
    app.config["PRIVATUS_ANALYTICS"] = {"enabled": True, "auto_inject": auto_inject}
    PrivatusAnalytics(app)

    @app.before_request
    def set_nonce() -> None:
        # Where Flask-Talisman keeps its nonce. The package finds it there.
        request.csp_nonce = NONCE

    @app.after_request
    def content_security_policy(response: Response) -> Response:
        response.headers["Content-Security-Policy"] = f"script-src 'nonce-{NONCE}' {SCRIPT_HOST}"
        return response

    return app


app = create_app()
auto_app = create_app(auto_inject=True)


@app.get("/")
def home() -> str:
    return render_template("home.html", page_props=PAGE_PROPS)


@app.get("/event")
def event() -> str:
    return render_template("event.html", page_props=PAGE_PROPS)


@app.get("/nasty")
def nasty() -> str:
    return render_template("nasty.html", page_props={**PAGE_PROPS, "nasty": NASTY}, nasty=NASTY)


@app.get("/off")
def off() -> str:
    return render_template("off.html", page_props=PAGE_PROPS)


@auto_app.get("/auto")
def auto() -> str:
    return AUTO_PAGE


def application(environ, start_response):
    """Sends /auto to the app with auto inject on, everything else to the main app."""
    target = auto_app if environ.get("PATH_INFO") == "/auto" else app
    return target(environ, start_response)
