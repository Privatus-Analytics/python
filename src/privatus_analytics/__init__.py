"""Adds the cookieless Privatus Analytics tracking script to Python web apps.

The package only prints HTML: the browser script tag and HTML attributes.
It never sends events from the server, sets no cookies and reads nothing
about your visitors.
"""

from privatus_analytics.core import (
    DEFAULT_HOST,
    Config,
    SafeHTML,
    click_attr,
    event_attrs,
    inject_tag,
    page_props_json,
    page_props_script,
    queue_stub,
    render_tag,
)

__version__ = "1.0.1"

__all__ = [
    "DEFAULT_HOST",
    "Config",
    "SafeHTML",
    "__version__",
    "click_attr",
    "event_attrs",
    "inject_tag",
    "page_props_json",
    "page_props_script",
    "queue_stub",
    "render_tag",
]
