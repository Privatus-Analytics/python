"""Jinja2 globals and filters. Used by the Flask and Starlette integrations, or on its own.

    from privatus_analytics.jinja import install
    install(env, {"site_id": "pa_YOURSITEID"})

Then in a template::

    {{ privatus_analytics() }}
    <button {{ privatus_event("Export CSV", format="csv") }}>Export</button>
    <a {{ privatus_click("pricing.cta") }} href="/pricing">Pricing</a>
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Union

from jinja2 import Environment, pass_context
from jinja2.runtime import Context

from privatus_analytics._request import find_nonce
from privatus_analytics.core import Config, SafeHTML, click_attr, event_attrs, render_tag

ConfigSource = Union[Config, Mapping[str, Any], Callable[[], Config], None]


def config_getter(source: ConfigSource) -> Callable[[], Config]:
    """Turns a Config, a dict of settings or a function into a function that returns a Config."""
    if callable(source) and not isinstance(source, Config):
        return source
    config = source if isinstance(source, Config) else Config.from_mapping(source)
    return lambda: config


def render_for_request(config: Config, request: Any = None, context_nonce: Any = None, **overrides: Any) -> SafeHTML:
    """Renders the tag for one request, using the framework nonce when there is one."""
    if not overrides.get("nonce"):
        nonce = find_nonce(request, context_nonce)
        if nonce:
            overrides["nonce"] = nonce
    return render_tag(config, request=request, **overrides)


def install(env: Environment, config: ConfigSource = None) -> Environment:
    """Adds ``privatus_analytics``, ``privatus_event`` and ``privatus_click`` to a Jinja2 environment.

    ``privatus_event`` and ``privatus_click`` are also added as filters:
    ``{{ "pricing.cta" | privatus_click }}``.
    """
    get_config = config_getter(config)

    @pass_context
    def privatus_analytics(context: Context, **overrides: Any) -> SafeHTML:
        return render_for_request(get_config(), context.get("request"), context.get("csp_nonce"), **overrides)

    def privatus_event(name: Any, props: Optional[Mapping[str, Any]] = None, **more_props: Any) -> SafeHTML:
        return event_attrs(name, props, **more_props)

    env.globals["privatus_analytics"] = privatus_analytics
    env.globals["privatus_event"] = privatus_event
    env.globals["privatus_click"] = click_attr
    env.filters["privatus_event"] = privatus_event
    env.filters["privatus_click"] = click_attr
    return env
