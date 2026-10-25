# Changelog

## 1.0.0 - 2026-10-25

- Initial release.
- Framework-free core: `render_tag`, `event_attrs`, `click_attr`, `page_props_json`, `page_props_script`, `queue_stub` and `inject_tag`.
- Django app with the `{% privatus_analytics %}`, `{% privatus_event %}` and `{% privatus_click %}` template tags, and an optional middleware that adds the tag to the head of HTML responses (off by default).
- Jinja2 globals and filters, a Flask extension and an optional `after_request` hook.
- Starlette and FastAPI support: a `Jinja2Templates` helper and an optional ASGI middleware.
- Page props: send groups such as plan or role with every pageview and event.
- Uses the framework's Content Security Policy nonce when there is one.
- With `queue_stub` on, a tag that is off still prints the queue stub (and nothing else), so `privatus.track` calls never fail in development.
- Skips Django when `DEBUG` is on, Flask in debug or testing mode, and everything else outside production by default.
