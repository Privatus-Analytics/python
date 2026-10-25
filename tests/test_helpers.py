import logging

from privatus_analytics import SafeHTML, click_attr, event_attrs, page_props_json, page_props_script


def test_event_attrs_basic():
    result = event_attrs("Export CSV", {"format": "csv", "source": "toolbar"})
    assert result == (
        'data-privatus-event="Export CSV" data-privatus-prop-format="csv" data-privatus-prop-source="toolbar"'
    )
    assert isinstance(result, SafeHTML)


def test_event_attrs_keyword_props():
    assert event_attrs("Signup", plan="pro") == 'data-privatus-event="Signup" data-privatus-prop-plan="pro"'


def test_event_name_is_trimmed_and_cut():
    assert event_attrs("  Saved  ") == 'data-privatus-event="Saved"'
    assert event_attrs("x" * 200) == f'data-privatus-event="{"x" * 120}"'


def test_empty_event_name_renders_nothing():
    assert event_attrs("") == ""
    assert event_attrs("   ", {"a": 1}) == ""
    assert event_attrs(None) == ""


def test_event_prop_keys_are_normalised():
    result = event_attrs("E", {"Plan Type": "a", "feature-flag": "b", "k" * 80: "c"})
    assert 'data-privatus-prop-plan_type="a"' in result
    assert 'data-privatus-prop-feature_flag="b"' in result
    assert f'data-privatus-prop-{"k" * 64}="c"' in result


def test_event_prop_values_become_strings():
    result = event_attrs("E", {"on": True, "off": False, "n": 3, "f": 1.5, "tags": ["a", "b"], "none": None})
    assert 'data-privatus-prop-on="true"' in result
    assert 'data-privatus-prop-off="false"' in result
    assert 'data-privatus-prop-n="3"' in result
    assert 'data-privatus-prop-f="1.5"' in result
    assert 'data-privatus-prop-tags="a,b"' in result
    assert "none" not in result


def test_event_prop_values_are_cut_and_escaped():
    result = event_attrs('Say "hi" <b>', {"v": "y" * 600, "q": "a&b"})
    assert 'data-privatus-event="Say &quot;hi&quot; &lt;b&gt;"' in result
    assert f'data-privatus-prop-v="{"y" * 500}"' in result
    assert 'data-privatus-prop-q="a&amp;b"' in result


def test_at_most_30_event_props():
    result = event_attrs("E", {f"p{i}": i for i in range(40)})
    assert result.count("data-privatus-prop-") == 30
    assert "p29" in result
    assert "p30" not in result


def test_click_attr():
    assert click_attr("pricing.cta") == 'data-privatus-click="pricing.cta"'
    assert click_attr("a:b-c_d") == 'data-privatus-click="a:b-c_d"'
    assert isinstance(click_attr("x"), SafeHTML)


def test_invalid_click_names_render_nothing_and_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="privatus_analytics"):
        assert click_attr("has space") == ""
        assert click_attr('"><script>') == ""
        assert click_attr("") == ""
        assert click_attr("x" * 101) == ""
    assert "not valid" in caplog.text


def test_page_props_json_keeps_types():
    props = {"Plan": "pro", "seats": 5, "beta": True, "ratio": 0.5, "flags": ["a", "b"], "gone": None}
    assert page_props_json(props) == '{"plan":"pro","seats":5,"beta":true,"ratio":0.5,"flags":["a","b"]}'


def test_page_props_json_is_safe_in_a_script():
    result = page_props_json({"x": "</script><b>&\u2028\u2029"})
    assert result == '{"x":"\\u003c/script\\u003e\\u003cb\\u003e\\u0026\\u2028\\u2029"}'
    assert "</script>" not in result


def test_page_props_limits():
    many = page_props_json({f"p{i}": i for i in range(40)})
    assert many.count(":") == 30
    lists = page_props_json({"l": list(range(50)), "s": "z" * 600, "nan": float("nan")})
    assert lists.count(",") == 30
    assert '"s":"' + "z" * 500 + '"' in lists
    assert "nan" not in lists


def test_page_props_script():
    assert page_props_script({}) == ""
    assert page_props_script({"plan": "pro"}, nonce="n") == (
        '<script nonce="n">window.privatusPageProps=function(){return {"plan":"pro"}}</script>'
    )
