from django.http import HttpResponse, JsonResponse
from django.template import RequestContext, Template
from django.urls import path

LAYOUT = Template(
    "{% load privatus %}<html><head><title>Home</title>{% privatus_analytics %}</head>"
    '<body><button {% privatus_event "Export CSV" format="csv" %}>Export</button>'
    '<a {% privatus_click "pricing.cta" %} href="/pricing">Pricing</a></body></html>'
)


def home(request):
    return HttpResponse(LAYOUT.render(RequestContext(request)))


def plain(request):
    return HttpResponse("<html><head><title>Plain</title></head><body>Hi</body></html>")


def bare(request):
    return HttpResponse("<p>No head here</p>")


def data(request):
    return JsonResponse({"ok": True})


urlpatterns = [
    path("", home),
    path("plain", plain),
    path("bare", bare),
    path("data", data),
]
