from django.core.management.base import BaseCommand
from core.telegram_bot import get_application

class Command(BaseCommand):
    help = "Run Telegram bot for one-time student registration (Long Polling)."

    def handle(self, *args, **options):
        app = get_application()
        self.stdout.write(self.style.SUCCESS("Telegram bot started in long-polling mode. Press Ctrl+C to stop."))
        app.run_polling()
