# Privatus Analytics for Python

**Real visitor numbers for your Python web app. No cookies, no cookie pop-up, no bots.**

You want to know if people use your Python web app. But Google Analytics uses
cookies, so in many countries you must show a cookie pop-up first (the box that
asks visitors to say yes to cookies). Many people click no, so they never show
up in your numbers. Bots add fake visits on top.

This package adds the Privatus Analytics script to your Django, Flask, FastAPI
or Starlette app, with a template tag or a middleware that puts it in the page
head for you. The script sets no cookies and keeps no IP addresses. Bots are
filtered out before they are counted.

So you see how many real people came, which pages they looked at and where they
came from, on one simple dashboard. A report comes to your inbox each week, and
you can set alerts for when traffic jumps or drops. And you don't need a cookie
pop-up for your analytics.

**Free plan, no card:** 10,000 events a month (an event is a page view or an action you track) on up to 3 sites. [Start free at privatusanalytics.com](https://privatusanalytics.com).

- **No cookies.** No cookies and no hidden IDs on your visitors' devices, and no IP
  addresses are kept. Laws differ by country, so check your own legal advice.
- **Real people, not bots.** Known bots, data centers and spam visits are left
  out on every plan.
- **Small and fast.** The script is about 3 KB when compressed.

## What this package does

- Works with Django, Flask, FastAPI and Starlette.
- A template tag, and an optional middleware that puts the script in the
  `<head>` for you.
- The package only prints HTML: the browser script tag and a few HTML
  attributes. It never sends events from your server, sets no cookies and reads
  nothing about your visitors.

You need a Privatus Analytics account to see your reports, and there is a
free plan. [Sign up at privatusanalytics.com](https://privatusanalytics.com).

## Requirements

* Python 3.9 or later.
* Django 4.2 or later, Flask 2.3 or later, or Starlette 0.29 or later
  (FastAPI is built on Starlette). The core works with no framework at all.
* A Privatus Analytics site id (it starts with `pa_`). You find it under
  Site settings, Tracking.

## Install

```sh
pip install privatus-analytics
```

The package has no required dependencies. It uses the framework you already
have. For the full setup guide and every tracker option, see the
[Privatus Analytics docs](https://privatusanalytics.com/docs).

Set your site id with an environment variable:

```sh
PRIVATUS_SITE_ID=pa_YOURSITEID
```

or in your settings, as shown for each framework below.

## Add the tag

### Django

Add the app and your settings in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "privatus_analytics.django",
]

PRIVATUS_ANALYTICS = {
    "site_id": "pa_YOURSITEID",
}
```

Put the tag in the `<head>` of your base template:

```django
{% load privatus %}
<head>
  <title>My app</title>
  {% privatus_analytics %}
</head>
```

The tag prints only when `DEBUG` is off. It needs the `request` in the
template context (the default `django.template.context_processors.request`
adds it) for the nonce and for page props that depend on the request.

### Flask

```python
from flask import Flask
from privatus_analytics.flask import PrivatusAnalytics

app = Flask(__name__)
app.config["PRIVATUS_ANALYTICS"] = {"site_id": "pa_YOURSITEID"}
PrivatusAnalytics(app)  # or PrivatusAnalytics().init_app(app)
```

```jinja
<head>
  <title>My app</title>
  {{ privatus_analytics() }}
</head>
```

The tag prints only when the app is not in debug or testing mode.

### FastAPI and Starlette

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from privatus_analytics import Config
from privatus_analytics.starlette import setup_templates

config = Config(site_id="pa_YOURSITEID")
templates = setup_templates(Jinja2Templates(directory="templates"), config)
app = FastAPI()


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html")
```

Use `{{ privatus_analytics() }}` in the template, the same as Flask.
Starlette has no shared "production" switch, so the tag prints only when the
`PRIVATUS_ENV` environment variable is `production`, or when you set
`enabled=True` yourself, for example `Config(enabled=not settings.debug)`.

### Without a framework

```python
from privatus_analytics import Config, render_tag

html = render_tag(Config(site_id="pa_YOURSITEID", enabled=True))
```

To add the tag to any Jinja2 environment, call
`privatus_analytics.jinja.install(env, config)`.

### What it prints

In production it prints:

```html
<script defer src="https://privatusstats.com/js/pa.js" data-site="pa_YOURSITEID"></script>
```

The tag prints nothing when there is no site id, and nothing in development
(see below). The one exception is the queue stub: when you turn it on, it
still prints. Every value is HTML-escaped.

If your app uses a Content Security Policy (CSP, a list of rules that tells
the browser which scripts may run) with a nonce (a random code that marks a
script as allowed), the tag adds it for you. It looks for `request.csp_nonce`
(django-csp, Flask-Talisman), a `csp_nonce` template value (Django 6) and
`request.state.csp_nonce` (Starlette and FastAPI). You can also set the
`nonce` setting or pass `nonce=` to the tag.

### Or let the package add it

If you would rather not touch your templates, switch on auto inject:

```python
PRIVATUS_ANALYTICS = {"site_id": "pa_YOURSITEID", "auto_inject": True}
```

* Django: also add
  `"privatus_analytics.django.middleware.PrivatusAnalyticsMiddleware"` to
  `MIDDLEWARE`. Put it below `GZipMiddleware` in the list.
* Flask: nothing else to do. The extension adds an `after_request` hook.
* FastAPI and Starlette: add the ASGI middleware:

  ```python
  from privatus_analytics.starlette import PrivatusAnalyticsMiddleware

  app.add_middleware(PrivatusAnalyticsMiddleware, config=Config(site_id="pa_YOURSITEID", auto_inject=True))
  ```

It adds the tag just before `</head>` in uncompressed `text/html` responses
with status 200, and fixes the `Content-Length` header. It skips Ajax
requests (background requests sent by JavaScript), pages without a `<head>`,
and pages that already have the tag. Responses that have a
`Content-Encoding` header (compressed responses) are left alone, so add the
middleware where it runs before compression, or use the template tag.

## Configuration

Every setting is optional except the site id. Django reads them from
`settings.PRIVATUS_ANALYTICS`, Flask from `app.config["PRIVATUS_ANALYTICS"]`,
and Starlette takes a `Config(...)` or a plain dict. Unknown setting names
raise an error, so typos do not go unnoticed.

```python
PRIVATUS_ANALYTICS = {
    "site_id": "pa_YOURSITEID",  # or PRIVATUS_SITE_ID
    "script_host": "https://privatusstats.com",  # or PRIVATUS_SCRIPT_HOST
    "modules": ["engage", "auto", "vitals", "clicks", "ask"],
    "excluded_paths": ["/admin/*", "/preview/*"],
    "domains": ["example.com", "www.example.com"],
    "spa": "auto",  # auto, history, hash or off
    "manual": False,  # True turns off the automatic pageview
    "auto_inject": False,
    "extra_attributes": {"data-mask": "/orders/*->/orders/:id"},
    "props": lambda request: {"plan": "pro"},
}
```

| Setting | Default | What it does |
|---|---|---|
| `site_id` | `PRIVATUS_SITE_ID` | The `data-site` attribute. Nothing prints without it |
| `script_host` | `https://privatusstats.com` | Where `/js/pa.js` is served. Change it only if you host your own copy |
| `modules` | tracker default (`engage`) | The `data-modules` attribute. Setting it replaces the default, so keep `engage` for time on page and scroll depth. `[]` loads none |
| `excluded_paths` | none | The `data-exclude` attribute. Path patterns the tracker never counts |
| `domains` | all hosts | The `data-domains` attribute. Count only these hostnames |
| `spa` | `auto` | The `data-spa` attribute, for single-page apps |
| `manual` | `False` | The `data-manual` attribute |
| `enabled` | `None` | `True` or `False` forces the tag on or off. `None` uses the framework (see below) |
| `enabled_environments` | `("production",)` | Used when no framework decides. Compared with `environment` |
| `environment` | `PRIVATUS_ENV`, else `development` | The current environment when no framework decides |
| `auto_inject` | `False` | Adds the tag with a middleware |
| `extra_attributes` | `{}` | Any other `data-*` attribute. `True` prints the name alone |
| `nonce` | framework nonce | The CSP nonce, if your framework does not give one |
| `props` | `None` | Page props: a dict, or a function that gets the request and returns a dict |
| `queue_stub` | `False` | Prints the `window.privatus` queue stub before the tag |

Each tracker attribute is explained in the [script attributes
reference](https://privatusanalytics.com/docs/tracker/attributes), and the
modules in [Modules](https://privatusanalytics.com/docs/tracker/modules).

You can also change a setting for one page:

```django
{% privatus_analytics modules="engage,auto" excluded_paths="/preview/*" %}
```

```jinja
{{ privatus_analytics(modules=["engage", "auto"], excluded_paths=["/preview/*"]) }}
```

### Development and test

Your own clicking around should not reach your reports, so by default the tag
prints nothing:

* Django: when `DEBUG` is on.
* Flask: when `app.debug` or `app.testing` is on.
* Starlette, FastAPI and plain Python: unless `PRIVATUS_ENV=production`.

If `queue_stub` is on, the tag still prints the small queue stub (and nothing
else), so `privatus.track` calls in your own JavaScript keep working. They
wait in a queue and are never sent.

To see the tag while you build, set `"enabled": True`. The tracker also
ignores `localhost` unless you pass `data-allow-local` or `data-debug` (see
[Debug mode](https://privatusanalytics.com/docs/tracker/debug)):

```python
PRIVATUS_ANALYTICS = {"site_id": "pa_YOURSITEID", "enabled": True, "extra_attributes": {"data-debug": "true"}}
```

### Leaving people out

Use `excluded_paths` (the `data-exclude` attribute) for admin areas. To leave
out signed-in staff, print the tag only for everyone else:

```django
{% if not request.user.is_staff %}{% privatus_analytics %}{% endif %}
```

## Product analytics: see which features people use

### Buttons, links and forms

`privatus_event` prints the attributes that make the tracker send a custom
event when someone clicks the element:

```django
<button {% privatus_event "Report exported" format="csv" source="toolbar" %}>Export</button>
```

```jinja
<button {{ privatus_event("Report exported", format="csv", source="toolbar") }}>Export</button>
```

Both print:

```html
<button data-privatus-event="Report exported" data-privatus-prop-format="csv" data-privatus-prop-source="toolbar">Export</button>
```

Put it on a `<form>` and the event is sent when the form is submitted:

```django
<form method="post" {% privatus_event "Newsletter signup" list="weekly" %}>
```

The rules:

* The event name is trimmed and cut to 120 characters. An empty name prints
  nothing.
* Detail names (props) are made lowercase, any character other than `a-z`,
  `0-9` and `_` becomes `_`, and they are cut to 64 characters. At most 30
  props are kept.
* Values become text: `True` becomes `true`, numbers stay as written, and
  lists are joined with commas. `None` values are dropped. Values are cut to
  500 characters.
* These attributes print even when the tag is turned off. They do nothing
  without the tracker, and your development and production HTML stay the
  same.

In plain Python, use `event_attrs("Report exported", {"format": "csv"})`.

### Click maps

Give important elements a stable name so click maps can group clicks on them:

```django
<a {% privatus_click "pricing.cta" %} href="/pricing">See pricing</a>
```

```jinja
<a {{ privatus_click("pricing.cta") }} href="/pricing">See pricing</a>
```

This prints `data-privatus-click="pricing.cta"`. Names may use letters,
digits and `_ . : -`, up to 100 characters. Anything else prints nothing and
logs a warning on the `privatus_analytics` logger. In plain Python, use
`click_attr("pricing.cta")`. In Jinja2, `privatus_event` and `privatus_click`
also work as filters: `{{ "pricing.cta" | privatus_click }}`.

### Page props: plan, role and other groups

Page props are sent with every pageview and event on the page. Use them to
compare groups, such as plan, role, app version, feature flags or account
size. Set them in your settings as a function that gets the request:

```python
def privatus_props(request):
    if not request.user.is_authenticated:
        return {"plan": "visitor"}
    return {"plan": request.user.account.plan, "role": request.user.role, "app_version": "4.2"}


PRIVATUS_ANALYTICS = {"site_id": "pa_YOURSITEID", "props": privatus_props}
```

or pass them to one tag, which adds to the props from your settings:

```django
{% privatus_analytics props=page_props %}
```

The tag then prints a small script before the tracker, and points the tracker
at it with `data-props`:

```html
<script>window.privatusPageProps=function(){return {"plan":"pro","role":"admin"}}</script>
<script defer src="https://privatusstats.com/js/pa.js" data-site="pa_YOURSITEID" data-props="privatusPageProps"></script>
```

Detail names follow the same rules as events. Numbers and `True`/`False`
stay numbers and booleans, and lists stay lists (at most 30 items). The data
is escaped so it is safe inside a `<script>` element.

**Never put names, emails, user ids or anything else that points to one
person in props.** Privatus Analytics counts visitors without any id. Put groups
(plan, role), not people. The server also removes emails and long ids it
finds.

### Track from your own JavaScript

The package only loads the tracker. You can also send events from your own
scripts, as described in the [JavaScript API
docs](https://privatusanalytics.com/docs/tracker/javascript-api):

```js
privatus.track("Feature used", { feature: "export" });
```

If your code may run before the tracker has loaded, set `"queue_stub": True`.
The tag then prints this small script first (with your nonce), which keeps
the calls until the tracker is ready:

```html
<script>window.privatus=window.privatus||{q:[]};['track','pageview','props','optOut','optIn','ready'].forEach(function(m){window.privatus[m]=window.privatus[m]||function(){window.privatus.q.push([m,Array.prototype.slice.call(arguments)])}})</script>
```

The stub prints even when the tag is off (in development, or with
`"enabled": False`). Only the stub prints then: no tracker and no page
props. So your `privatus.track` calls never fail. They wait in the queue and
are never sent.

In plain Python, `queue_stub(nonce=...)` returns the same script.

### Naming events

Name events as "Noun verb", in the past tense, like `Report exported`,
`Invite sent` or `Plan upgraded`. Keep the name short and put details in
props (`format: csv`), so one event covers every variant. Then use them in:

* [Funnels](https://privatusanalytics.com/docs/features/funnels), to see where
  people drop off.
* [Click maps](https://privatusanalytics.com/docs/features/click-maps), to see
  what people click.
* [Goals](https://privatusanalytics.com/docs/features/goals), to count
  conversions.
* [Events](https://privatusanalytics.com/docs/events), for every event and
  its props.

## Privacy

The script sets no cookies and stores nothing in the browser. This package
sends nothing from your server and reads no IP addresses, browser details or
visitor ids. See the [privacy
documentation](https://privatusanalytics.com/docs/privacy) for what is
collected.

If you have a privacy policy, it should say which tools handle your visitors' data. You can paste this:

> This website uses [Privatus Analytics](https://privatusanalytics.com/privacy-analytics) to count visits. It
> does not use cookies and does not follow you from one website to another. Your IP address is used for a moment
> to count visits and is never stored.

Change it to fit your site. The [privacy policy generator](https://privatusanalytics.com/tools/privacy-policy-generator)
makes a longer version with your site's name in it.

## Development

The tests run in Docker, so your local Python does not matter:

```sh
./run-docker.sh
```

It runs the pytest suite against small Django, Flask and Starlette apps,
Ruff (the linter and formatter), and the package build.

## Contributing

Bug reports and pull requests are welcome at
https://github.com/Privatus-Analytics/python.

## License

MIT. See [LICENSE](LICENSE). Privatus Analytics is a product of Two Phase
LLC, Wyoming, USA.
