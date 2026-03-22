import asyncio
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update

from core.decorators import admin_only
from core.security import get_client_ip, security_event
from core.telegram_bot import get_application

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "").strip()
    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "").strip()

    if expected_secret and received_secret != expected_secret:
        security_event(
            event="telegram_webhook_rejected",
            level="warning",
            reason="bad_secret",
            ip=get_client_ip(request),
        )
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))

        async def run_update():
            ptb_app = get_application()
            async with ptb_app:
                update = Update.de_json(payload, ptb_app.bot)
                await ptb_app.process_update(update)

        asyncio.run(run_update())
        return JsonResponse({"status": "ok"})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception:
        logger.exception("Telegram webhook failed")
        security_event(
            event="telegram_webhook_error",
            level="error",
            ip=get_client_ip(request),
        )
        return JsonResponse({"error": "Webhook processing failed"}, status=500)


@admin_only
def set_webhook(request):
    host = request.get_host()
    scheme = "https" if not request.is_secure() else request.scheme
    webhook_url = f"{scheme}://{host}/telegram-webhook/"

    async def run_setup():
        ptb_app = get_application()
        async with ptb_app:
            return await ptb_app.bot.set_webhook(
                url=webhook_url,
                secret_token=getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "").strip() or None,
            )

    try:
        success = asyncio.run(run_setup())
    except Exception:
        logger.exception("set_webhook failed")
        return HttpResponse("Failed to set webhook", status=500)

    if success:
        security_event(event="telegram_webhook_set", actor="admin", url=webhook_url)
        return HttpResponse(f"Webhook set successfully to {webhook_url}")
    return HttpResponse("Failed to set webhook", status=500)
