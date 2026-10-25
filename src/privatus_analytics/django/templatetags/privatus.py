"""Template tags. Load them with ``{% load privatus %}``.

{% privatus_analytics %}
{% privatus_analytics modules="engage,auto" %}
<button {% privatus_event "Export CSV" format="csv" %}>Export</button>
<a {% privatus_click "pricing.cta" %} href="/pricing">Pricing</a>
"""

from __future__ import annotations

from typing import Any

from django import template

from privatus_analytics.core import SafeHTML, click_attr, event_attrs
from privatus_analytics.django import render

register = template.Library()


@register.simple_tag(takes_context=True)
def privatus_analytics(context: template.Context, **overrides: Any) -> SafeHTML:
    """Prints the script tag. Put it in the head of your base template."""
    return render(context.get("request"), context.get("csp_nonce"), **overrides)


@register.simple_tag
def privatus_event(name: Any, **props: Any) -> SafeHTML:
    """Prints ``data-privatus-event`` and ``data-privatus-prop-*`` attributes."""
    return event_attrs(name, props)


@register.simple_tag
def privatus_click(name: Any) -> SafeHTML:
    """Prints a ``data-privatus-click`` attribute for click maps."""
    return click_attr(name)
