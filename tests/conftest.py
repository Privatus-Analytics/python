import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        SECRET_KEY="test-only",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF="tests.django_urls",
        INSTALLED_APPS=["django.contrib.contenttypes", "privatus_analytics.django"],
        MIDDLEWARE=["privatus_analytics.django.middleware.PrivatusAnalyticsMiddleware"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": False,
                "DIRS": [],
                "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
            }
        ],
        DATABASES={},
    )
    django.setup()

SITE = "pa_TEST123456"
SNIPPET = '<script defer src="https://privatusstats.com/js/pa.js" data-site="pa_TEST123456"></script>'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("PRIVATUS_SITE_ID", "PRIVATUS_SCRIPT_HOST", "PRIVATUS_ENV"):
        monkeypatch.delenv(name, raising=False)
