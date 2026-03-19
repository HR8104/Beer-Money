from django.conf import settings

from .models import AdminLog


def get_session_email(request):
    """Return normalized authenticated email from session if present."""
    return request.session.get("user_email", "").strip().lower()


def get_admin_emails():
    """Return normalized master admin emails from settings."""
    return [email.strip().lower() for email in settings.ADMIN_EMAILS if email.strip()]


def is_api_request(request):
    """Detect API/AJAX requests that should return JSON instead of redirects."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or request.path.startswith("/api/")


def log_admin_action(request, action, target, details=""):
    """Utility function to record administrative actions."""
    admin_email = get_session_email(request) or "unknown@beermoney.com"
    AdminLog.objects.create(
        admin_email=admin_email,
        action=action,
        target=target,
        details=details,
    )
