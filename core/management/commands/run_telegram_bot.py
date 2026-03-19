from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.forms import ValidationError as FormValidationError
from django.utils import timezone
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.forms import StudentProfileForm
from core.utils import is_gig_expired
from core.models import (
    Application as GigApplication,
    Gig,
    TelegramEmailOTP,
    TelegramRegistration,
    UserProfile,
    UserRole,
)


(
    APPLY_BRIEF,
    EMAIL,
    EMAIL_OTP,
    FULL_NAME,
    MOBILE,
    GENDER,
    DOB,
    COLLEGE,
    ABOUT,
    SKILLS,
    INTRO_VIDEO_URL,
    PROFILE_PICTURE_URL,
    CONFIRM,
) = range(13)


def _normalize_text(value: str) -> str:
    return value.strip()


def _parse_date(value: str) -> date | None:
    parts = value.strip().split("-")
    if len(parts) != 3:
        return None
    try:
        y, m, d = [int(piece) for piece in parts]
        return date(y, m, d)
    except ValueError:
        return None


def _is_valid_phone(value: str) -> bool:
    cleaned = value.strip()
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def _get_telegram_registration_by_user(telegram_user_id: int) -> TelegramRegistration | None:
    return TelegramRegistration.objects.filter(telegram_user_id=telegram_user_id).first()


def _get_profile_by_email(email: str) -> UserProfile | None:
    return UserProfile.objects.filter(email=email).first()


def _email_linked_to_other_telegram(email: str, telegram_user_id: int) -> bool:
    link = TelegramRegistration.objects.filter(student__email=email).first()
    if not link:
        return False
    return link.telegram_user_id != telegram_user_id


def _send_email_otp(email: str, telegram_user_id: int) -> tuple[bool, str]:
    otp = str(random.randint(100000, 999999))
    expiry_minutes = int(getattr(settings, "OTP_EXPIRY_MINUTES", 5))
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

    TelegramEmailOTP.objects.filter(email=email, telegram_user_id=telegram_user_id).delete()
    TelegramEmailOTP.objects.create(
        email=email,
        telegram_user_id=telegram_user_id,
        otp_code=otp,
        expires_at=expires_at,
    )

    try:
        send_mail(
            subject="Beer Money Telegram Verification OTP",
            message=(
                f"Your OTP is: {otp}\n\n"
                f"This code expires in {expiry_minutes} minutes.\n\n"
                "If you did not request this verification, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        return False, f"Could not send OTP email: {exc}"
    return True, ""


def _verify_email_otp(email: str, telegram_user_id: int, otp_code: str) -> tuple[bool, str]:
    otp_obj = (
        TelegramEmailOTP.objects.filter(email=email, telegram_user_id=telegram_user_id, is_verified=False)
        .order_by("-created_at")
        .first()
    )
    if not otp_obj:
        return False, "No OTP found. Send /start to request a new OTP."

    if timezone.now() > otp_obj.expires_at:
        otp_obj.delete()
        return False, "OTP expired. Send /start to request a new OTP."

    if otp_obj.otp_code != otp_code:
        return False, "Incorrect OTP. Please try again."

    otp_obj.is_verified = True
    otp_obj.save(update_fields=["is_verified"])
    return True, ""


def _link_existing_web_user_to_telegram(email: str, user: Any, chat: Any) -> tuple[bool, str]:
    with transaction.atomic():
        existing_for_user = TelegramRegistration.objects.filter(telegram_user_id=user.id).first()
        if existing_for_user:
            return False, "This Telegram account is already registered."

        profile = UserProfile.objects.filter(email=email).first()
        if not profile:
            return False, "No web profile found for this email."

        existing_for_profile = TelegramRegistration.objects.filter(student=profile).first()
        if existing_for_profile:
            return False, "This email is already linked to another Telegram account."

        TelegramRegistration.objects.create(
            telegram_user_id=user.id,
            telegram_chat_id=chat.id,
            telegram_username=user.username or "",
            telegram_first_name=user.first_name or "",
            telegram_last_name=user.last_name or "",
            student=profile,
        )
        profile.mark_registered_from(UserProfile.RegistrationPlatform.TELEGRAM)
        profile.save(update_fields=["registration_platform"])
        UserRole.objects.get_or_create(email=email, defaults={"role": UserRole.Roles.STUDENT})
    return True, ""


def _create_new_telegram_registration(payload: dict[str, Any], user: Any, chat: Any) -> tuple[bool, str]:
    with transaction.atomic():
        if TelegramRegistration.objects.filter(telegram_user_id=user.id).exists():
            return False, "This Telegram account is already registered."

        if UserProfile.objects.filter(email=payload["email"]).exists():
            return False, "This email already exists on web. Use /start and verify via OTP."

        form = StudentProfileForm(payload)
        if not form.is_valid():
            return False, f"Validation failed: {form.errors.as_text()}"

        profile = form.save(commit=False)
        profile.email = payload["email"]
        profile.registration_platform = UserProfile.RegistrationPlatform.TELEGRAM
        profile.save()
        UserRole.objects.get_or_create(
            email=payload["email"], defaults={"role": UserRole.Roles.STUDENT}
        )
        TelegramRegistration.objects.create(
            telegram_user_id=user.id,
            telegram_chat_id=chat.id,
            telegram_username=user.username or "",
            telegram_first_name=user.first_name or "",
            telegram_last_name=user.last_name or "",
            student=profile,
        )
    return True, ""


def _validate_apply_eligibility_by_telegram_user(
    telegram_user_id: int, gig_id: int
) -> tuple[bool, str]:
    link = TelegramRegistration.objects.select_related("student").filter(
        telegram_user_id=telegram_user_id
    ).first()
    if not link:
        return False, "Please complete registration first using /start."

    student = link.student
    if student.is_banned:
        return False, "Your account is banned. Please contact support."

    role = UserRole.objects.filter(email=student.email).first()
    if role and role.is_frozen:
        return False, "Your account is frozen. Please contact support."

    gig = Gig.objects.select_related("employer").filter(id=gig_id).first()
    if not gig:
        return False, "Gig not found."
    if gig.status == Gig.Status.ACTIVE and is_gig_expired(gig):
        gig.status = Gig.Status.CLOSED
        gig.save(update_fields=["status", "updated_at"])
    if gig.status != Gig.Status.ACTIVE:
        return False, "This gig is no longer active."

    already_applied = GigApplication.objects.filter(gig=gig, student=student).exists()
    if already_applied:
        return False, "You already applied for this gig."

    return True, f"Gig found: {gig.title}"


def _submit_gig_application_with_brief(
    telegram_user_id: int, gig_id: int, suitability_note: str
) -> tuple[bool, str]:
    note = (suitability_note or "").strip()
    if len(note) < 10:
        return False, "Please write at least 10 characters in your brief."

    with transaction.atomic():
        link = TelegramRegistration.objects.select_related("student").filter(
            telegram_user_id=telegram_user_id
        ).first()
        if not link:
            return False, "Please complete registration first using /start."

        student = link.student
        if student.is_banned:
            return False, "Your account is banned. Please contact support."

        role = UserRole.objects.filter(email=student.email).first()
        if role and role.is_frozen:
            return False, "Your account is frozen. Please contact support."

        gig = Gig.objects.select_related("employer").filter(id=gig_id).first()
        if not gig:
            return False, "Gig not found."
        if gig.status == Gig.Status.ACTIVE and is_gig_expired(gig):
            gig.status = Gig.Status.CLOSED
            gig.save(update_fields=["status", "updated_at"])
        if gig.status != Gig.Status.ACTIVE:
            return False, "This gig is no longer active."

        if GigApplication.objects.filter(gig=gig, student=student).exists():
            return False, "You already applied for this gig."

        GigApplication.objects.create(
            gig=gig,
            student=student,
            suitability_note=note,
        )
    return True, "Application sent successfully."


registration_by_user_async = sync_to_async(_get_telegram_registration_by_user)
profile_by_email_async = sync_to_async(_get_profile_by_email)
email_linked_to_other_telegram_async = sync_to_async(_email_linked_to_other_telegram)
send_email_otp_async = sync_to_async(_send_email_otp)
verify_email_otp_async = sync_to_async(_verify_email_otp)
link_existing_web_user_async = sync_to_async(_link_existing_web_user_to_telegram)
create_new_telegram_registration_async = sync_to_async(_create_new_telegram_registration)
validate_apply_eligibility_async = sync_to_async(_validate_apply_eligibility_by_telegram_user)
submit_gig_application_with_brief_async = sync_to_async(_submit_gig_application_with_brief)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user or not update.message:
        return ConversationHandler.END

    start_payload = context.args[0] if context.args else ""
    if start_payload.startswith("apply_"):
        gig_id_raw = start_payload.replace("apply_", "", 1).strip()
        if not gig_id_raw.isdigit():
            await update.message.reply_text("Invalid apply link. Please try again from channel.")
            return ConversationHandler.END

        gig_id = int(gig_id_raw)
        ok, apply_message = await validate_apply_eligibility_async(user.id, gig_id)
        if not ok:
            await update.message.reply_text(apply_message, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        context.user_data.clear()
        context.user_data["pending_apply_gig_id"] = gig_id
        await update.message.reply_text(
            "Please write a brief on why you are suitable for this gig:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return APPLY_BRIEF

    existing = await registration_by_user_async(user.id)
    if existing:
        await update.message.reply_text(
            "Your Telegram is already linked. Registration is complete."
        )
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "Welcome to Beer Money student registration.\n"
        "Enter your email address:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EMAIL


async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return EMAIL
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    email = _normalize_text(update.message.text).lower()
    try:
        validate_email(email)
    except FormValidationError:
        await update.message.reply_text("Please enter a valid email address.")
        return EMAIL

    existing_profile = await profile_by_email_async(email)
    context.user_data["email"] = email

    if existing_profile:
        already_linked_elsewhere = await email_linked_to_other_telegram_async(email, user.id)
        if already_linked_elsewhere:
            await update.message.reply_text(
                "This email is already linked to another Telegram account."
            )
            context.user_data.clear()
            return ConversationHandler.END

        success, error_message = await send_email_otp_async(email, user.id)
        if not success:
            await update.message.reply_text(error_message)
            context.user_data.clear()
            return ConversationHandler.END
        await update.message.reply_text(
            "We found this email in web registration.\n"
            "A one-time OTP has been sent to your email.\n"
            "Please enter the 6-digit OTP:"
        )
        return EMAIL_OTP

    await update.message.reply_text("Enter your full name:")
    return FULL_NAME


async def handle_apply_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return APPLY_BRIEF
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    gig_id = context.user_data.get("pending_apply_gig_id")
    if not gig_id:
        await update.message.reply_text("Apply session expired. Please try the channel button again.")
        context.user_data.clear()
        return ConversationHandler.END

    brief = _normalize_text(update.message.text)
    if len(brief) < 10:
        await update.message.reply_text("Please write at least 10 characters.")
        return APPLY_BRIEF

    ok, message = await submit_gig_application_with_brief_async(user.id, int(gig_id), brief)
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


async def handle_email_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return EMAIL_OTP
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return ConversationHandler.END

    otp_code = _normalize_text(update.message.text)
    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text("Please enter a valid 6-digit OTP.")
        return EMAIL_OTP

    email = context.user_data.get("email", "")
    if not email:
        await update.message.reply_text("Session expired. Send /start again.")
        return ConversationHandler.END

    verified, verify_message = await verify_email_otp_async(email, user.id, otp_code)
    if not verified:
        await update.message.reply_text(verify_message)
        return EMAIL_OTP

    linked, link_message = await link_existing_web_user_async(email, user, chat)
    if not linked:
        await update.message.reply_text(link_message, reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        "Verification complete. Your web and Telegram registrations are now linked.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def handle_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return FULL_NAME
    full_name = _normalize_text(update.message.text)
    if len(full_name) < 2:
        await update.message.reply_text("Full name looks too short. Please re-enter.")
        return FULL_NAME
    context.user_data["full_name"] = full_name
    await update.message.reply_text("Enter your mobile number (digits only):")
    return MOBILE


async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return MOBILE
    mobile = _normalize_text(update.message.text)
    if not _is_valid_phone(mobile):
        await update.message.reply_text("Please enter a valid mobile number (7-15 digits).")
        return MOBILE
    context.user_data["mobile"] = mobile
    keyboard = [["male", "female", "other"]]
    await update.message.reply_text(
        "Select your gender:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return GENDER


async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return GENDER
    gender = _normalize_text(update.message.text).lower()
    if gender not in {"male", "female", "other"}:
        await update.message.reply_text("Please choose: male, female, or other.")
        return GENDER
    context.user_data["gender"] = gender
    await update.message.reply_text(
        "Enter your date of birth in YYYY-MM-DD format:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DOB


async def handle_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return DOB
    parsed = _parse_date(_normalize_text(update.message.text))
    if not parsed:
        await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD.")
        return DOB
    if parsed >= date.today():
        await update.message.reply_text("Date of birth must be in the past.")
        return DOB
    context.user_data["dob"] = parsed.isoformat()
    await update.message.reply_text("Enter your college name:")
    return COLLEGE


async def handle_college(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return COLLEGE
    college = _normalize_text(update.message.text)
    if len(college) < 2:
        await update.message.reply_text("Please enter a valid college name.")
        return COLLEGE
    context.user_data["college"] = college
    await update.message.reply_text("Write a short about/bio (or type `skip`):")
    return ABOUT


async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ABOUT
    about = _normalize_text(update.message.text)
    context.user_data["about"] = "" if about.lower() == "skip" else about
    await update.message.reply_text("Enter your skills (comma separated):")
    return SKILLS


async def handle_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return SKILLS
    skills = _normalize_text(update.message.text)
    if len(skills) < 2:
        await update.message.reply_text("Please enter at least one skill.")
        return SKILLS
    context.user_data["skills"] = skills
    await update.message.reply_text("Enter intro video URL (or type `skip`):")
    return INTRO_VIDEO_URL


async def handle_intro_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return INTRO_VIDEO_URL
    intro_video_url = _normalize_text(update.message.text)
    context.user_data["intro_video_url"] = (
        "" if intro_video_url.lower() == "skip" else intro_video_url
    )
    await update.message.reply_text("Enter profile picture URL (or type `skip`):")
    return PROFILE_PICTURE_URL


async def handle_profile_picture_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return PROFILE_PICTURE_URL
    profile_picture_url = _normalize_text(update.message.text)
    context.user_data["profile_picture_url"] = (
        "" if profile_picture_url.lower() == "skip" else profile_picture_url
    )
    summary = (
        "Please confirm your details:\n\n"
        f"Email: {context.user_data.get('email')}\n"
        f"Full Name: {context.user_data.get('full_name')}\n"
        f"Mobile: {context.user_data.get('mobile')}\n"
        f"Gender: {context.user_data.get('gender')}\n"
        f"DOB: {context.user_data.get('dob')}\n"
        f"College: {context.user_data.get('college')}\n"
        f"About: {context.user_data.get('about') or '(empty)'}\n"
        f"Skills: {context.user_data.get('skills')}\n"
        f"Intro Video URL: {context.user_data.get('intro_video_url') or '(empty)'}\n"
        f"Profile Picture URL: {context.user_data.get('profile_picture_url') or '(empty)'}\n\n"
        "Reply with `yes` to submit, or `no` to cancel."
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return CONFIRM
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return ConversationHandler.END

    answer = _normalize_text(update.message.text).lower()
    if answer != "yes":
        await update.message.reply_text(
            "Registration cancelled. Send /start to begin again.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    payload: dict[str, Any] = {
        "email": context.user_data["email"],
        "full_name": context.user_data["full_name"],
        "mobile": context.user_data["mobile"],
        "gender": context.user_data["gender"],
        "dob": context.user_data["dob"],
        "college": context.user_data["college"],
        "about": context.user_data["about"],
        "skills": context.user_data["skills"],
        "intro_video_url": context.user_data["intro_video_url"] or None,
        "profile_picture_url": context.user_data["profile_picture_url"] or None,
    }

    ok, message = await create_new_telegram_registration_async(payload, user, chat)
    if not ok:
        await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        "Telegram registration completed successfully.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text(
            "Registration cancelled.",
            reply_markup=ReplyKeyboardRemove(),
        )
    context.user_data.clear()
    return ConversationHandler.END


class Command(BaseCommand):
    help = "Run Telegram bot for one-time student registration."

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN is missing. Add it to your environment/.env file."
            )

        app = Application.builder().token(token).build()
        conv = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                APPLY_BRIEF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_apply_brief)],
                EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
                EMAIL_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email_otp)],
                FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_name)],
                MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mobile)],
                GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender)],
                DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dob)],
                COLLEGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_college)],
                ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_about)],
                SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_skills)],
                INTRO_VIDEO_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intro_video_url)
                ],
                PROFILE_PICTURE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_picture_url)
                ],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirm)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv)
        self.stdout.write(self.style.SUCCESS("Telegram bot started. Press Ctrl+C to stop."))
        app.run_polling()
