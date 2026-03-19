from django.contrib import admin
from .models import TelegramRegistration


@admin.register(TelegramRegistration)
class TelegramRegistrationAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "telegram_username", "student", "registered_at")
    search_fields = ("telegram_user_id", "telegram_username", "student__email")
