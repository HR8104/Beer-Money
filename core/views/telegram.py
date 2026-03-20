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
            ptb_app = get_application()
            update = Update.de_json(json.loads(request.body.decode('utf-8')), ptb_app.bot)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if not ptb_app._initialized:
                loop.run_until_complete(ptb_app.initialize())
                
            loop.run_until_complete(ptb_app.process_update(update))
            loop.close()
            
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def set_webhook(request):
    host = request.get_host()
    # Provide an option to force HTTPS if sitting behind a proxy (like PythonAnywhere)
    scheme = "https" if not request.is_secure() else request.scheme
    webhook_url = f"{scheme}://{host}/telegram-webhook/"
    
    ptb_app = get_application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(ptb_app.bot.set_webhook(url=webhook_url))
    loop.close()
    
    if success:
        return HttpResponse(f"Webhook set successfully to {webhook_url}")
    return HttpResponse("Failed to set webhook")
