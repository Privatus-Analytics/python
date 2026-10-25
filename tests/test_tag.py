import pytest

from privatus_analytics import Config, SafeHTML, inject_tag, queue_stub, render_tag
from tests.conftest import SITE, SNIPPET


def tag(**settings):
    overrides = settings.pop("overrides", {})
    return render_tag(Config(site_id=SITE, enabled=True, **settings), **overrides)


def test_prints_the_basic_snippet():
    result = tag()
    assert result == SNIPPET
    assert isinstance(result, SafeHTML)
    assert result.__html__() == SNIPPET


def test_prints_nothing_without_a_site_id():
    assert render_tag(Config(enabled=True)) == ""


def test_prints_nothing_outside_the_enabled_environments():
    assert render_tag(Config(site_id=SITE)) == ""
    assert render_tag(Config(site_id=SITE, environment="production")) == SNIPPET


def test_works_without_any_config(monkeypatch):
    monkeypatch.setenv("PRIVATUS_SITE_ID", SITE)
    monkeypatch.setenv("PRIVATUS_ENV", "production")
    assert render_tag() == SNIPPET


def test_adds_modules_and_exclusions():
    result = tag(modules=["engage", "auto"], excluded_paths=["/admin/*", "/preview/*"])
    assert 'data-modules="engage,auto"' in result
    assert 'data-exclude="/admin/*,/preview/*"' in result


def test_an_empty_modules_list_loads_none():
    assert 'data-modules=""' in tag(modules=[])
    assert "data-modules" not in tag()


def test_adds_domains_spa_mode_and_manual_mode():
    result = tag(domains="example.com, www.example.com", spa="hash", manual=True)
    assert 'data-domains="example.com,www.example.com"' in result
    assert 'data-spa="hash"' in result
    assert 'data-manual="true"' in result


@pytest.mark.parametrize("spa", ["bogus", "auto", None])
def test_ignores_an_unknown_spa_mode_and_the_auto_default(spa):
    assert "data-spa" not in tag(spa=spa)


def test_escapes_attribute_values():
    assert 'data-exclude="/a&quot;b"' in tag(excluded_paths=['/a"b'])
    assert 'data-site="pa_&lt;x&gt;"' in render_tag(Config(site_id="pa_<x>", enabled=True))


def test_per_call_options_override_the_configuration():
    assert 'data-modules="vitals"' in tag(modules=["engage"], overrides={"modules": ["vitals"]})
    assert tag(overrides={"enabled": False}) == ""


def test_unknown_per_call_options_raise():
    with pytest.raises(TypeError):
        tag(overrides={"bogus": 1})


def test_adds_extra_attributes_and_a_nonce():
    result = tag(
        extra_attributes={"data-mask": "/orders/*->/orders/:id", "data-skip": None, 'bad"name': "x"},
        overrides={"nonce": "abc123"},
    )
    assert 'data-mask="/orders/*-&gt;/orders/:id"' in result
    assert 'nonce="abc123"' in result
    assert "data-skip" not in result
    assert "bad" not in result


def test_bare_extra_attribute():
    assert tag(extra_attributes={"data-debug": True}).endswith('data-site="pa_TEST123456" data-debug></script>')


def test_page_props_print_a_script_before_the_tag():
    result = tag(props={"plan": "pro", "role": "admin"})
    expected = (
        '<script>window.privatusPageProps=function(){return {"plan":"pro","role":"admin"}}</script>\n'
        '<script defer src="https://privatusstats.com/js/pa.js" data-site="pa_TEST123456" '
        'data-props="privatusPageProps"></script>'
    )
    assert result == expected


def test_page_props_from_a_function_get_the_request_and_merge_with_call_props():
    seen = []

    def props(request):
        seen.append(request)
        return {"plan": "pro", "role": "member"}

    result = render_tag(
        Config(site_id=SITE, enabled=True, props=props, nonce="n1"), request="REQ", props={"role": "admin"}
    )
    assert seen == ["REQ"]
    assert '<script nonce="n1">window.privatusPageProps=function(){return {"plan":"pro","role":"admin"}}' in result
    assert 'nonce="n1"></script>' in result


def test_empty_props_print_no_props_script():
    assert tag(props={}) == SNIPPET
    assert tag(props=lambda request: None) == SNIPPET
    assert tag(props={"gone": None}) == SNIPPET


def test_queue_stub_prints_first():
    result = tag(queue_stub=True, nonce="abc")
    assert result.startswith('<script nonce="abc">window.privatus=window.privatus||{q:[]};')
    assert result.endswith('nonce="abc"></script>')
    assert queue_stub().startswith("<script>window.privatus=")
    assert "['track','pageview','props','optOut','optIn','ready']" in queue_stub()


def test_inject_tag():
    assert (
        inject_tag("<html><HEAD></Head><body></body></html>", "<x>") == "<html><HEAD><x>\n</head><body></body></html>"
    )
    assert inject_tag("<p>No head</p>", "<x>") == "<p>No head</p>"
    page = '<head><script src="https://privatusstats.com/js/pa.js"></script></head>'
    assert inject_tag(page, "<x>") == page
    assert inject_tag("<head></head>", "") == "<head></head>"
