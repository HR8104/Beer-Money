import json
import logging
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

security_logger = logging.getLogger("core.security")


def get_client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _cache_key(prefix: str, scope: str) -> str:
    return f"sec:{prefix}:{scope}"


def is_rate_limited(prefix: str, scope: str, limit: int, window_seconds: int) -> bool:
    key = _cache_key(prefix, scope)
    count = cache.get(key, 0)
    if count >= limit:
        return True
    if count == 0:
        cache.set(key, 1, timeout=window_seconds)
    else:
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, count + 1, timeout=window_seconds)
    return False


def set_lock(prefix: str, scope: str, timeout_seconds: int) -> None:
    cache.set(_cache_key(prefix, scope), 1, timeout=timeout_seconds)


def is_locked(prefix: str, scope: str) -> bool:
    return bool(cache.get(_cache_key(prefix, scope)))


def clear_security_key(prefix: str, scope: str) -> None:
    cache.delete(_cache_key(prefix, scope))


def security_event(event: str, level: str = "info", **data) -> None:
    payload = {"event": event, **data}
    message = json.dumps(payload, default=str)

    log_method = getattr(security_logger, level.lower(), security_logger.info)
    log_method(message)
    _mirror_event_to_admin_log(event=event, level=level, payload=payload)


def security_alert(event: str, message: str, *, email_subject: Optional[str] = None, **data) -> None:
    security_event(event=event, level="error", message=message, **data)

    recipients = getattr(settings, "SECURITY_ALERT_EMAILS", [])
    if not recipients:
        return

    try:
        send_mail(
            subject=email_subject or f"[BeerMoney Security Alert] {event}",
            message=f"{message}\n\nDetails: {json.dumps(data, default=str)}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=recipients,
            fail_silently=True,
        )
    except Exception:
        # Never break user flow because alert email failed.
        security_logger.exception("Failed to dispatch security alert email for event %s", event)


def _mirror_event_to_admin_log(event: str, level: str, payload: dict) -> None:
    """
    Mirror selected security/runtime events into AdminLog so admins can see them
    from the dashboard timeline.
    """
    if not getattr(settings, "SECURITY_MIRROR_TO_ADMIN_LOGS", True):
        return

    if event == "admin_action":
        return

    info_events = {
        "login_success",
        "otp_sent",
        "otp_resent",
    }
    should_mirror = level.lower() in {"warning", "error", "critical"} or event in info_events
    if not should_mirror:
        return

    try:
        from .models import AdminLog

        actor = payload.get("email") or payload.get("admin_email") or "system@beermoney.com"
        target = payload.get("scope") or payload.get("endpoint") or payload.get("ip") or payload.get("event")

        AdminLog.objects.create(
            admin_email=str(actor),
            action=f"SECURITY_{str(event).upper()}",
            target=str(target)[:200],
            details=json.dumps(payload, default=str)[:2000],
        )
    except Exception:
        security_logger.exception("Failed to mirror security event to AdminLog: %s", event)
