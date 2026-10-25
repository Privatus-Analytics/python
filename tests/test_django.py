import pytest
from django.template import Context, Template
from django.test import Client, RequestFactory, override_settings

from tests.conftest import SITE, SNIPPET

ON = {"site_id": SITE, "enabled": True}


def render(source, context=None):
    return Template("{% load privatus %}" + source).render(Context(context or {}))


@pytest.fixture
def client():
    return Client()


@override_settings(PRIVATUS_ANALYTICS=ON)
def test_the_tag_prints_in_the_head(client):
    body = client.get("/").content.decode()
    assert SNIPPET in body
    assert body.index(SNIPPET) < body.index("</head>")


@override_settings(PRIVATUS_ANALYTICS={"site_id": SITE}, DEBUG=True)
def test_the_tag_prints_nothing_when_debug_is_on(client):
    assert "pa.js" not in client.get("/").content.decode()


@override_settings(PRIVATUS_ANALYTICS={"site_id": SITE}, DEBUG=False)
def test_the_tag_prints_when_debug_is_off(client):
    assert SNIPPET in client.get("/").content.decode()


@override_settings(PRIVATUS_ANALYTICS={"enabled": True})
def test_the_tag_prints_nothing_without_a_site_id(client):
    assert "pa.js" not in client.get("/").content.decode()


@override_settings(PRIVATUS_ANALYTICS=ON)
def test_event_and_click_attributes_render(client):
    body = client.get("/").content.decode()
    assert '<button data-privatus-event="Export CSV" data-privatus-prop-format="csv">' in body
    assert '<a data-privatus-click="pricing.cta" href="/pricing">' in body


@override_settings(PRIVATUS_ANALYTICS={"site_id": SITE, "enabled": False})
def test_event_attributes_render_even_when_the_tag_is_off():
    assert render('{% privatus_event "Saved" %}') == 'data-privatus-event="Saved"'
    assert render("{% privatus_analytics %}") == ""


@override_settings(PRIVATUS_ANALYTICS=ON)
def test_tag_overrides_and_escaping():
    result = render('{% privatus_analytics modules="engage,auto" spa="hash" %}')
    assert 'data-modules="engage,auto"' in result
    assert 'data-spa="hash"' in result
    assert render("{% privatus_event name v=1 %}", {"name": "<b>"}) == (
        'data-privatus-event="&lt;b&gt;" data-privatus-prop-v="1"'
    )


@override_settings(PRIVATUS_ANALYTICS=ON)
def test_the_nonce_comes_from_django_csp():
    request = RequestFactory().get("/")
    request.csp_nonce = "fromcsp"
    result = Template("{% load privatus %}{% privatus_analytics %}").render(Context({"request": request}))
    assert 'nonce="fromcsp"' in result


@override_settings(PRIVATUS_ANALYTICS={**ON, "nonce": "fromsettings"})
def test_the_nonce_can_come_from_the_context_or_settings():
    assert 'nonce="fromcontext"' in render("{% privatus_analytics %}", {"csp_nonce": "fromcontext"})
    assert 'nonce="fromsettings"' in render("{% privatus_analytics %}")


@override_settings(PRIVATUS_ANALYTICS={**ON, "props": lambda request: {"plan": "pro", "path": request.path}})
def test_props_from_settings_get_the_request(client):
    body = client.get("/").content.decode()
    assert 'window.privatusPageProps=function(){return {"plan":"pro","path":"/"}}' in body
    assert 'data-props="privatusPageProps"' in body


@override_settings(PRIVATUS_ANALYTICS=ON)
def test_the_middleware_does_nothing_by_default(client):
    assert "pa.js" not in client.get("/plain").content.decode()


@override_settings(PRIVATUS_ANALYTICS={**ON, "auto_inject": True})
def test_the_middleware_adds_the_tag_when_switched_on(client):
    response = client.get("/plain")
    body = response.content.decode()
    assert f"{SNIPPET}\n</head>" in body
    assert response["Content-Length"] == str(len(response.content))


@override_settings(PRIVATUS_ANALYTICS={**ON, "auto_inject": True})
def test_the_middleware_does_not_add_a_second_tag(client):
    assert client.get("/").content.decode().count("/js/pa.js") == 1


@override_settings(PRIVATUS_ANALYTICS={**ON, "auto_inject": True})
def test_the_middleware_leaves_json_html_without_head_and_ajax_alone(client):
    assert "pa.js" not in client.get("/data").content.decode()
    assert client.get("/bare").content.decode() == "<p>No head here</p>"
    assert "pa.js" not in client.get("/plain", HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()


@override_settings(PRIVATUS_ANALYTICS={"site_id": SITE, "auto_inject": True}, DEBUG=True)
def test_the_middleware_adds_nothing_when_debug_is_on(client):
    assert "pa.js" not in client.get("/plain").content.decode()
