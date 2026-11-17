from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    return render(request, "config/home.html")


@require_GET
def login_page(request):
    return render(request, "config/login.html")


@require_GET
def favicon(request):
    return HttpResponse(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#198754"/>'
            '<path d="M17 16h30v7H25v8h19v7H25v10h22v7H17z" fill="#fff"/>'
            "</svg>"
        ),
        content_type="image/svg+xml",
    )
