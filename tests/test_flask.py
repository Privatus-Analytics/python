import pytest
from flask import Flask, jsonify, render_template_string

from privatus_analytics.flask import PrivatusAnalytics
from tests.conftest import SITE, SNIPPET

LAYOUT = (
    "<html><head><title>Home</title>{{ privatus_analytics() }}</head><body>"
    '<button {{ privatus_event("Export CSV", format="csv") }}>Export</button>'
    "<a {{ 'pricing.cta' | privatus_click }} href=\"/pricing\">Pricing</a></body></html>"
)


def make_app(settings=None, testing=False, debug=False):
    app = Flask(__name__)
    app.testing = testing
    app.debug = debug
    if settings is not None:
        app.config["PRIVATUS_ANALYTICS"] = settings
    PrivatusAnalytics(app)

    @app.route("/")
    def home():
        return render_template_string(LAYOUT)

    @app.route("/plain")
    def plain():
        return "<html><head><title>Plain</title></head><body>Hi</body></html>"

    @app.route("/bare")
    def bare():
        return "<p>No head here</p>"

    @app.route("/data")
    def data():
        return jsonify(ok=True)

    @app.route("/nonce")
    def nonce():
        from flask import request

        request.csp_nonce = "flasknonce"
        return render_template_string("{{ privatus_analytics() }}")

    return app


def get(app, path, **kwargs):
    return app.test_client().get(path, **kwargs)


def test_the_tag_prints_in_the_head():
    body = get(make_app({"site_id": SITE}), "/").get_data(as_text=True)
    assert SNIPPET in body
    assert body.index(SNIPPET) < body.index("</head>")
    assert '<button data-privatus-event="Export CSV" data-privatus-prop-format="csv">' in body
    assert '<a data-privatus-click="pricing.cta" href="/pricing">' in body


@pytest.mark.parametrize(("testing", "debug"), [(True, False), (False, True)])
def test_the_tag_prints_nothing_in_debug_or_testing(testing, debug):
    body = get(make_app({"site_id": SITE}, testing=testing, debug=debug), "/").get_data(as_text=True)
    assert "pa.js" not in body
    assert "data-privatus-event" in body


def test_enabled_forces_the_tag_on_in_testing():
    body = get(make_app({"site_id": SITE, "enabled": True}, testing=True), "/").get_data(as_text=True)
    assert SNIPPET in body


def test_the_tag_prints_nothing_without_a_site_id():
    assert "pa.js" not in get(make_app(), "/").get_data(as_text=True)


def test_the_nonce_comes_from_the_request():
    assert 'nonce="flasknonce"' in get(make_app({"site_id": SITE}), "/nonce").get_data(as_text=True)


def test_props_function_gets_the_request():
    app = make_app({"site_id": SITE, "props": lambda request: {"path": request.path}})
    body = get(app, "/").get_data(as_text=True)
    assert 'return {"path":"/"}' in body


def test_the_extension_tag_method():
    app = make_app({"site_id": SITE})
    with app.test_request_context("/"):
        assert app.extensions["privatus_analytics"].tag() == SNIPPET


def test_the_auto_inject_hook_does_nothing_by_default():
    assert "pa.js" not in get(make_app({"site_id": SITE}), "/plain").get_data(as_text=True)


def test_the_auto_inject_hook_adds_the_tag():
    response = get(make_app({"site_id": SITE, "auto_inject": True}), "/plain")
    body = response.get_data(as_text=True)
    assert f"{SNIPPET}\n</head>" in body
    assert response.headers["Content-Length"] == str(len(response.get_data()))


def test_the_auto_inject_hook_leaves_other_responses_alone():
    app = make_app({"site_id": SITE, "auto_inject": True})
    assert get(app, "/").get_data(as_text=True).count("/js/pa.js") == 1
    assert "pa.js" not in get(app, "/data").get_data(as_text=True)
    assert get(app, "/bare").get_data(as_text=True) == "<p>No head here</p>"
    assert "pa.js" not in get(app, "/plain", headers={"X-Requested-With": "XMLHttpRequest"}).get_data(as_text=True)


def test_the_auto_inject_hook_adds_nothing_in_debug():
    app = make_app({"site_id": SITE, "auto_inject": True}, debug=True)
    assert "pa.js" not in get(app, "/plain").get_data(as_text=True)
