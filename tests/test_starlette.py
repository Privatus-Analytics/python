import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.testclient import TestClient

from privatus_analytics import Config
from privatus_analytics.starlette import PrivatusAnalyticsMiddleware, setup_templates
from tests.conftest import SITE, SNIPPET

LAYOUT = (
    "<html><head><title>Home</title>{{ privatus_analytics() }}</head><body>"
    '<button {{ privatus_event("Export CSV", {"format": "csv"}) }}>Export</button>'
    "<a {{ privatus_click('pricing.cta') }} href=\"/pricing\">Pricing</a></body></html>"
)


@pytest.fixture
def make_client(tmp_path):
    (tmp_path / "home.html").write_text(LAYOUT)

    def build(config):
        templates = setup_templates(Jinja2Templates(directory=str(tmp_path)), config)

        async def home(request):
            nonce = request.query_params.get("nonce")
            if nonce:
                request.state.csp_nonce = nonce
            return templates.TemplateResponse(request, "home.html")

        async def plain(request):
            return HTMLResponse("<html><head><title>Plain</title></head><body>Hi</body></html>")

        async def bare(request):
            return HTMLResponse("<p>No head here</p>")

        async def data(request):
            return JSONResponse({"ok": True})

        async def stream(request):
            async def parts():
                yield b"<html><head><title>S</title>"
                yield b"</head><body>Streamed</body></html>"

            return StreamingResponse(parts(), media_type="text/html")

        routes = [
            Route("/", home),
            Route("/plain", plain),
            Route("/bare", bare),
            Route("/data", data),
            Route("/stream", stream),
        ]
        app = Starlette(routes=routes, middleware=[Middleware(PrivatusAnalyticsMiddleware, config=config)])
        return TestClient(app)

    return build


def test_the_tag_and_attributes_print_in_templates(make_client):
    body = make_client(Config(site_id=SITE, enabled=True)).get("/").text
    assert SNIPPET in body
    assert body.index(SNIPPET) < body.index("</head>")
    assert '<button data-privatus-event="Export CSV" data-privatus-prop-format="csv">' in body
    assert '<a data-privatus-click="pricing.cta" href="/pricing">' in body


def test_the_tag_prints_nothing_outside_production(make_client, monkeypatch):
    client = make_client(Config(site_id=SITE))
    assert "pa.js" not in client.get("/").text
    monkeypatch.setenv("PRIVATUS_ENV", "production")
    assert SNIPPET in client.get("/").text


def test_a_settings_dict_works(make_client):
    assert SNIPPET in make_client({"site_id": SITE, "enabled": True}).get("/").text


def test_the_nonce_comes_from_request_state(make_client):
    assert 'nonce="stnonce"' in make_client(Config(site_id=SITE, enabled=True)).get("/?nonce=stnonce").text


def test_props_function_gets_the_request(make_client):
    config = Config(site_id=SITE, enabled=True, props=lambda request: {"path": request.url.path})
    assert 'return {"path":"/"}' in make_client(config).get("/").text


def test_the_middleware_does_nothing_by_default(make_client):
    assert "pa.js" not in make_client(Config(site_id=SITE, enabled=True)).get("/plain").text


def test_the_middleware_adds_the_tag(make_client):
    response = make_client(Config(site_id=SITE, enabled=True, auto_inject=True)).get("/plain")
    assert f"{SNIPPET}\n</head>" in response.text
    assert response.headers["content-length"] == str(len(response.content))


def test_the_middleware_handles_streamed_html(make_client):
    response = make_client(Config(site_id=SITE, enabled=True, auto_inject=True)).get("/stream")
    assert f"{SNIPPET}\n</head>" in response.text


def test_the_middleware_leaves_other_responses_alone(make_client):
    client = make_client(Config(site_id=SITE, enabled=True, auto_inject=True))
    assert client.get("/").text.count("/js/pa.js") == 1
    assert "pa.js" not in client.get("/data").text
    assert client.get("/bare").text == "<p>No head here</p>"
    assert "pa.js" not in client.get("/plain", headers={"X-Requested-With": "XMLHttpRequest"}).text


def test_the_middleware_adds_nothing_when_disabled(make_client):
    assert "pa.js" not in make_client(Config(site_id=SITE, auto_inject=True)).get("/plain").text
