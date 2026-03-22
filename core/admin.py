from django.contrib import admin
from .models import (
    UserProfile,
    UserRole,
    EmployerProfile,
    Gig,
    Application,
    Review,
    AdminLog,
    TelegramRegistration,
    TelegramEmailOTP,
    BotState,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "registration_platform", "registered_at", "is_banned")
    list_filter = ("registration_platform", "is_banned")
    search_fields = ("full_name", "email")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "is_frozen", "created_at")
    list_filter = ("role", "is_frozen")
    search_fields = ("email",)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company_name", "email", "created_at")
    search_fields = ("full_name", "company_name", "email")


@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "status", "date", "earnings", "created_at")
    list_filter = ("status", "date")
    search_fields = ("title", "employer__company_name")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("gig", "student", "status", "applied_at")
    list_filter = ("status",)
    search_fields = ("gig__title", "student__email")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("application", "reviewer_email", "reviewee_email", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("reviewer_email", "reviewee_email")


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ("admin_email", "action", "target", "timestamp")
    list_filter = ("action",)
    search_fields = ("admin_email", "target")


@admin.register(TelegramRegistration)
class TelegramRegistrationAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "telegram_username", "student", "registered_at")
    search_fields = ("telegram_user_id", "telegram_username", "student__email")


@admin.register(TelegramEmailOTP)
class TelegramEmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "telegram_user_id", "otp_code", "expires_at", "is_verified", "created_at")
    list_filter = ("is_verified",)
    search_fields = ("email", "telegram_user_id")


@admin.register(BotState)
class BotStateAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
