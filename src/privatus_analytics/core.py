"""Framework-free core: settings, the script tag and the HTML attribute helpers.

Nothing here sends a request, sets a cookie or reads anything about a visitor.
It only builds HTML strings.
"""

from __future__ import annotations

import dataclasses
import html
import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Union

logger = logging.getLogger("privatus_analytics")

DEFAULT_HOST = "https://privatusstats.com"
MODULES = ("engage", "auto", "vitals", "clicks", "ask")
SPA_MODES = ("auto", "history", "hash", "off")
MARKER = "/js/pa.js"
PROPS_FUNCTION = "privatusPageProps"

MAX_EVENT_NAME = 120
MAX_KEY = 64
MAX_PROPS = 30
MAX_VALUE = 500
MAX_LIST_ITEMS = 30

QUEUE_STUB_JS = (
    "window.privatus=window.privatus||{q:[]};"
    "['track','pageview','props','optOut','optIn','ready'].forEach(function(m){"
    "window.privatus[m]=window.privatus[m]||function(){"
    "window.privatus.q.push([m,Array.prototype.slice.call(arguments)])}})"
)

_CLICK_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,100}")
_KEY_CHARS = re.compile(r"[^a-z0-9_]")
_ATTRIBUTE_NAME = re.compile(r"[A-Za-z_:][-A-Za-z0-9_:.]*")
_HEAD_CLOSE = re.compile(r"</head>", re.IGNORECASE)
_JSON_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}

Props = Union[Mapping[str, Any], Callable[[Any], Optional[Mapping[str, Any]]], None]


class SafeHTML(str):
    """A string of ready-made HTML.

    Django, Jinja2 and MarkupSafe all see the ``__html__`` method and print the
    string as it is, without escaping it a second time.
    """

    __slots__ = ()

    def __html__(self) -> str:
        return self


@dataclass
class Config:
    """Settings for the tracking script. Every setting is optional except the site id."""

    #: The site id (starts with ``pa_``). Falls back to ``PRIVATUS_SITE_ID``.
    site_id: Optional[str] = None
    #: Origin that serves ``/js/pa.js``. Falls back to ``PRIVATUS_SCRIPT_HOST``.
    script_host: Optional[str] = None
    #: Tracker modules, for example ``["engage", "auto"]``. ``None`` keeps the tracker default.
    modules: Optional[Iterable[str]] = None
    #: Path globs the tracker never counts, for example ``["/admin/*"]``.
    excluded_paths: Optional[Iterable[str]] = field(default_factory=list)
    #: Hostnames to count. ``None`` counts every host.
    domains: Optional[Iterable[str]] = None
    #: One of auto, history, hash, off. ``None`` keeps the tracker default.
    spa: Optional[str] = None
    #: ``True`` turns off the automatic pageview.
    manual: bool = False
    #: ``True`` or ``False`` forces the tag on or off. ``None`` uses the environment.
    enabled: Optional[bool] = None
    #: Environments that get the tag when ``enabled`` is ``None`` and no framework decides.
    enabled_environments: Iterable[str] = ("production",)
    #: The current environment. Falls back to ``PRIVATUS_ENV``, then ``development``.
    environment: Optional[str] = None
    #: ``True`` adds the tag to the head of HTML responses with a middleware.
    auto_inject: bool = False
    #: Other ``data-*`` attributes, for example ``{"data-mask": "/orders/*->/orders/:id"}``.
    extra_attributes: Mapping[str, Any] = field(default_factory=dict)
    #: Content Security Policy nonce. Framework nonces are used first when they exist.
    nonce: Optional[str] = None
    #: Page properties sent with every pageview and event. A dict, or a function
    #: that gets the request and returns a dict.
    props: Props = None
    #: ``True`` prints the ``window.privatus`` queue stub before the tag.
    queue_stub: bool = False

    @classmethod
    def from_mapping(cls, mapping: Optional[Mapping[str, Any]] = None, **extra: Any) -> Config:
        """Builds a Config from a dict, such as Django or Flask settings.

        Unknown keys raise ``TypeError`` so typos do not go unnoticed.
        """
        values = dict(mapping or {})
        values.update(extra)
        names = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(values) - names)
        if unknown:
            raise TypeError(f"Unknown Privatus Analytics setting(s): {', '.join(unknown)}")
        return cls(**values)

    def resolved_site_id(self) -> Optional[str]:
        value = str(self.site_id or "").strip()
        if not value:
            value = os.environ.get("PRIVATUS_SITE_ID", "").strip()
        return value or None

    def resolved_script_host(self) -> str:
        value = str(self.script_host or "").strip()
        if not value:
            value = os.environ.get("PRIVATUS_SCRIPT_HOST", "").strip()
        if not value:
            value = DEFAULT_HOST
        return value[:-1] if value.endswith("/") else value

    def is_enabled(self) -> bool:
        """Whether the tag should print in the current environment."""
        if self.enabled is not None:
            return bool(self.enabled)
        environment = self.environment or os.environ.get("PRIVATUS_ENV", "").strip() or "development"
        return environment in [str(name) for name in _as_list(self.enabled_environments) or []]

    def should_render(self) -> bool:
        return self.resolved_site_id() is not None and self.is_enabled()


def render_tag(config: Optional[Config] = None, *, request: Any = None, **overrides: Any) -> SafeHTML:
    """Builds the script tag, plus the page props script and queue stub when asked.

    ``overrides`` replaces any Config setting for this one call. ``props`` is
    merged on top of the configured props instead of replacing them.
    When the tag is off (disabled, or no site id) it prints only the queue
    stub when ``queue_stub`` is on, so ``privatus.track`` calls in your own
    JavaScript do not fail in development, and otherwise nothing.
    """
    base = config if config is not None else Config()
    call_props = overrides.pop("props", None)
    config = dataclasses.replace(base, **overrides) if overrides else base
    if not config.should_render():
        return queue_stub(nonce=config.nonce) if config.queue_stub else SafeHTML("")

    props = _resolve_props(base.props, request)
    if call_props is not None:
        props.update(_resolve_props(call_props, request))
    props_json = page_props_json(props)

    parts = []
    if config.queue_stub:
        parts.append(queue_stub(nonce=config.nonce))
    if props_json != "{}":
        parts.append(_inline_script(f"window.{PROPS_FUNCTION}=function(){{return {props_json}}}", config.nonce))
    parts.append(_script_tag(config, with_props=props_json != "{}"))
    return SafeHTML("\n".join(parts))


def tag_attributes(config: Config, *, with_props: bool = False) -> dict[str, Any]:
    """The attributes of the tracker script tag, in order. ``True`` means a bare attribute."""
    attrs: dict[str, Any] = {
        "defer": True,
        "src": f"{config.resolved_script_host()}{MARKER}",
        "data-site": config.resolved_site_id(),
    }
    for name, attribute in (
        ("modules", "data-modules"),
        ("excluded_paths", "data-exclude"),
        ("domains", "data-domains"),
    ):
        values = _as_list(getattr(config, name))
        # None keeps the tracker default. An empty modules list loads none.
        if values is not None and (name == "modules" or values):
            attrs[attribute] = ",".join(values)
    spa = str(config.spa or "")
    if spa in SPA_MODES and spa != "auto":
        attrs["data-spa"] = spa
    if config.manual is True:
        attrs["data-manual"] = "true"
    if with_props:
        attrs["data-props"] = PROPS_FUNCTION
    for name, value in (config.extra_attributes or {}).items():
        if value is None or not _ATTRIBUTE_NAME.fullmatch(str(name)):
            continue
        attrs[str(name)] = value
    if config.nonce:
        attrs["nonce"] = config.nonce
    return attrs


def event_attrs(name: Any, props: Optional[Mapping[str, Any]] = None, **more_props: Any) -> SafeHTML:
    """Attributes that make the tracker send a custom event on click (or on submit for a form).

    ``event_attrs("Export CSV", {"format": "csv"})`` gives
    ``data-privatus-event="Export CSV" data-privatus-prop-format="csv"``.
    """
    event = str(name if name is not None else "").strip()[:MAX_EVENT_NAME]
    if not event:
        return SafeHTML("")
    merged = dict(props or {})
    merged.update(more_props)
    parts = [f'data-privatus-event="{_escape(event)}"']
    for key, value in _normalise(merged, _attribute_value).items():
        parts.append(f'data-privatus-prop-{key}="{_escape(value)}"')
    return SafeHTML(" ".join(parts))


def click_attr(name: Any) -> SafeHTML:
    """Names an element for click maps: ``data-privatus-click="pricing.cta"``.

    Names may use letters, digits and ``_ . : -``, up to 100 characters.
    Anything else prints nothing and logs a warning.
    """
    value = str(name if name is not None else "")
    if not _CLICK_NAME.fullmatch(value):
        logger.warning(
            "Privatus Analytics: click name %r is not valid. Use 1 to 100 letters, digits, _ . : or -.", value
        )
        return SafeHTML("")
    return SafeHTML(f'data-privatus-click="{value}"')


def page_props_json(props: Optional[Mapping[str, Any]]) -> str:
    """Page props as JSON that is safe to put inside a ``<script>`` element."""
    text = json.dumps(_normalise(props or {}, _json_value), ensure_ascii=False, separators=(",", ":"))
    for char, escaped in _JSON_ESCAPES.items():
        text = text.replace(char, escaped)
    return text


def page_props_script(props: Optional[Mapping[str, Any]], nonce: Optional[str] = None) -> SafeHTML:
    """The inline script that defines ``window.privatusPageProps``. Empty when there are no props."""
    props_json = page_props_json(props)
    if props_json == "{}":
        return SafeHTML("")
    return _inline_script(f"window.{PROPS_FUNCTION}=function(){{return {props_json}}}", nonce)


def queue_stub(nonce: Optional[str] = None) -> SafeHTML:
    """The official ``window.privatus`` queue stub, so calls made before the tracker loads are kept."""
    return _inline_script(QUEUE_STUB_JS, nonce)


def inject_tag(document: str, tag: str) -> str:
    """Puts ``tag`` just before the first ``</head>``.

    Leaves the document alone when the tag is empty, there is no ``</head>``,
    or the page already loads ``/js/pa.js``.
    """
    if not tag or MARKER in document or not _HEAD_CLOSE.search(document):
        return document
    return _HEAD_CLOSE.sub(lambda _match: f"{tag}\n</head>", document, count=1)


def should_inject(
    status: int, content_type: Optional[str], content_encoding: Optional[str], requested_with: Any
) -> bool:
    """The response checks shared by every auto inject middleware."""
    if status != 200 or content_encoding:
        return False
    if not str(content_type or "").lower().startswith("text/html"):
        return False
    return str(requested_with or "").lower() != "xmlhttprequest"


# Helpers


def _script_tag(config: Config, *, with_props: bool) -> str:
    parts = []
    for name, value in tag_attributes(config, with_props=with_props).items():
        if value is True:
            parts.append(name)
        else:
            text = "false" if value is False else str(value)
            parts.append(f'{name}="{_escape(text)}"')
    return f"<script {' '.join(parts)}></script>"


def _inline_script(body: str, nonce: Optional[str]) -> SafeHTML:
    nonce_attr = f' nonce="{_escape(nonce)}"' if nonce else ""
    return SafeHTML(f"<script{nonce_attr}>{body}</script>")


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _as_list(value: Any) -> Optional[list[str]]:
    """``None`` stays ``None``. Anything else becomes a clean list of strings."""
    if value is None:
        return None
    items = [value] if isinstance(value, (str, bytes)) else list(value)
    result = []
    for item in items:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result


def _resolve_props(props: Props, request: Any) -> dict[str, Any]:
    if callable(props):
        props = props(request)
    return dict(props or {})


def _normalise_key(key: Any) -> str:
    return _KEY_CHARS.sub("_", str(key).lower())[:MAX_KEY]


def _normalise(props: Mapping[str, Any], convert: Callable[[Any], Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in props.items():
        name = _normalise_key(key)
        value = convert(value)
        if not name or value is None:
            continue
        if name not in result and len(result) >= MAX_PROPS:
            continue
        result[name] = value
    return result


def _scalar_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _attribute_value(value: Any) -> Optional[str]:
    if isinstance(value, (list, tuple, set, frozenset)):
        text = ",".join(t for t in (_scalar_text(item) for item in value) if t is not None)
    else:
        text = _scalar_text(value)
    return None if text is None else text[:MAX_VALUE]


def _json_scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    return str(value)[:MAX_VALUE]


def _json_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_json_scalar(item) for item in value]
        return [item for item in items if item is not None][:MAX_LIST_ITEMS]
    return _json_scalar(value)
