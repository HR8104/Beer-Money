from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from ..utils import get_session_email
from ..models import UserRole

def index(request):
    return render(request, 'core/index.html')

def login_view(request):
    return render(request, 'core/login.html')

def dashboard_view(request):
    """Redirect to the correct dashboard based on role."""
    email = get_session_email(request)
    if not email:
        return redirect('login')
    
    user_role = request.session.get('user_role')
    if not user_role:
        try:
            role_obj = UserRole.objects.get(email=email)
            user_role = role_obj.role
            request.session['user_role'] = user_role
        except UserRole.DoesNotExist:
            user_role = UserRole.Roles.STUDENT

    if user_role == UserRole.Roles.ADMIN:
        return redirect('admin_dashboard')
    if user_role == UserRole.Roles.EMPLOYER:
        return redirect('employer_dashboard')
    return redirect('home')

def logout_view(request):
    """Clear session and redirect to landing page."""
    request.session.flush()
    return redirect('index')


def robots_txt(request):
    """Serve robots.txt for search engine crawlers."""
    content = "\n".join(
        [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /api/",
            "Allow: /",
        ]
    )
    return HttpResponse(content, content_type="text/plain")


def security_txt(request):
    """Serve security.txt for responsible disclosure details."""
    host = request.get_host().split(":")[0]
    expires = (timezone.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    canonical = f"https://{host}/.well-known/security.txt"

    content = "\n".join(
        [
            f"Contact: mailto:security@{host}",
            f"Expires: {expires}",
            "Preferred-Languages: en",
            f"Canonical: {canonical}",
        ]
    )
    return HttpResponse(content, content_type="text/plain")
