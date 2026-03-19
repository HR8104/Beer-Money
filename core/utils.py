from django.conf import settings
from django.utils import timezone
from django.db.models import Q
import json
from datetime import datetime
from urllib import error, parse, request as urlrequest

from .models import AdminLog, Gig, TelegramRegistration


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


def post_gig_to_telegram_channel(gig):
    """Publish a gig announcement to configured Telegram channel."""
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
    channel_id = getattr(settings, "TELEGRAM_CHANNEL_ID", "").strip()
    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")

    if not bot_token or not channel_id:
        return False, "Telegram channel posting is not configured."

    apply_url = ""
    if bot_username:
        apply_url = f"https://t.me/{bot_username}?start=apply_{gig.id}"

    date_txt = gig.date.strftime("%d %b %Y") if gig.date else "Not specified"
    time_txt = gig.time.strftime("%I:%M %p") if gig.time else "Not specified"
    description = (gig.description or "").strip()
    if len(description) > 450:
        description = f"{description[:447]}..."

    message = (
        f"New Gig Posted\n\n"
        f"Title: {gig.title}\n"
        f"Company: {gig.employer.company_name}\n"
        f"Earnings: {gig.earnings or 'Not specified'}\n"
        f"Date: {date_txt}\n"
        f"Time: {time_txt}\n\n"
        f"{description}\n\n"
        "Registered students can apply from the button below."
    )

    payload = {
        "chat_id": channel_id,
        "text": message,
    }
    if apply_url:
        payload["reply_markup"] = json.dumps(
            {"inline_keyboard": [[{"text": "Apply via Bot", "url": apply_url}]]}
        )

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    encoded = parse.urlencode(payload).encode("utf-8")
    req = urlrequest.Request(api_url, data=encoded, method="POST")

    try:
        with urlrequest.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except error.URLError as exc:
        return False, f"Telegram request failed: {exc}"
    except Exception as exc:
        return False, f"Telegram response parse failed: {exc}"

    if not data.get("ok"):
        return False, data.get("description", "Telegram API returned an error.")
    return True, "Posted to Telegram channel."


def send_telegram_text(chat_id, text):
    """Send plain Telegram message to a specific chat id."""
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return False, "Telegram bot token not configured."

    payload = {"chat_id": str(chat_id), "text": text}
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    encoded = parse.urlencode(payload).encode("utf-8")
    req = urlrequest.Request(api_url, data=encoded, method="POST")

    try:
        with urlrequest.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except error.URLError as exc:
        return False, f"Telegram request failed: {exc}"
    except Exception as exc:
        return False, f"Telegram response parse failed: {exc}"

    if not data.get("ok"):
        return False, data.get("description", "Telegram API returned an error.")
    return True, "Sent"


def notify_selected_student_on_telegram(application):
    """Notify selected student on Telegram with employer contact details and guidance note."""
    link = TelegramRegistration.objects.select_related("student").filter(
        student=application.student
    ).first()
    if not link:
        return False, "Student not linked to Telegram."

    employer = application.gig.employer
    message = (
        "Congratulations! You are selected for a gig.\n\n"
        f"Gig: {application.gig.title}\n"
        f"Company: {employer.company_name}\n"
        f"Employer Email: {employer.email}\n"
        f"Employer Phone: {employer.phone}\n\n"
        "Note: Don't contact employer directly. They will contact you within 5-10 hours."
    )
    return send_telegram_text(link.telegram_chat_id, message)


def auto_close_expired_gigs(employer=None):
    """
    Auto-close ACTIVE gigs whose date+time has already passed.
    Returns number of gigs updated.
    """
    now = timezone.localtime()
    today = now.date()
    current_time = now.time().replace(second=0, microsecond=0)

    qs = Gig.objects.filter(status=Gig.Status.ACTIVE).exclude(date__isnull=True).exclude(time__isnull=True)
    if employer is not None:
        qs = qs.filter(employer=employer)

    expired = qs.filter(Q(date__lt=today) | Q(date=today, time__lte=current_time))
    return expired.update(status=Gig.Status.CLOSED, updated_at=timezone.now())


def is_gig_expired(gig):
    """Return True if gig date+time is in the past."""
    if not gig.date or not gig.time:
        return False
    gig_dt = timezone.make_aware(
        datetime.combine(gig.date, gig.time),
        timezone.get_current_timezone(),
    )
    return gig_dt <= timezone.localtime()
