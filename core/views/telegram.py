import json
import asyncio
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.telegram_bot import get_application
from telegram import Update

@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode('utf-8'))
            
            async def run_update():
                ptb_app = get_application()
                # 'async with ptb_app' automatically starts/stops HTTPX client loops
                async with ptb_app:
                    update = Update.de_json(payload, ptb_app.bot)
                    await ptb_app.process_update(update)

            asyncio.run(run_update())
            
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def set_webhook(request):
    host = request.get_host()
    # Provide an option to force HTTPS if sitting behind a proxy (like PythonAnywhere/Render)
    scheme = "https" if not request.is_secure() else request.scheme
    webhook_url = f"{scheme}://{host}/telegram-webhook/"
    
    async def run_setup():
        ptb_app = get_application()
        async with ptb_app:
            return await ptb_app.bot.set_webhook(url=webhook_url)
            
    success = asyncio.run(run_setup())
    
    if success:
        return HttpResponse(f"Webhook set successfully to {webhook_url}")
    return HttpResponse("Failed to set webhook")
