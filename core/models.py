from django.db import models


class UserProfile(models.Model):
    class RegistrationPlatform(models.TextChoices):
        WEB = "web", "Web"
        TELEGRAM = "telegram", "Telegram"
        BOTH = "both", "Both"

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    dob = models.DateField()
    college = models.CharField(max_length=200)
    about = models.TextField(max_length=500, blank=True)
    skills = models.CharField(max_length=500, help_text="Comma-separated skills")
    intro_video_url = models.URLField(blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    is_banned = models.BooleanField(default=False)
    registration_platform = models.CharField(
        max_length=20,
        choices=RegistrationPlatform.choices,
        default=RegistrationPlatform.WEB,
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def mark_registered_from(self, source: str) -> None:
        source = (source or "").strip().lower()
        if source not in {
            self.RegistrationPlatform.WEB,
            self.RegistrationPlatform.TELEGRAM,
        }:
            return
        if self.registration_platform == self.RegistrationPlatform.BOTH:
            return
        if self.registration_platform != source:
            self.registration_platform = self.RegistrationPlatform.BOTH
        else:
            self.registration_platform = source


class UserRole(models.Model):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        EMPLOYER = 'EMPLOYER', 'Employer'
        STUDENT = 'STUDENT', 'Student'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.STUDENT)
    is_frozen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class EmployerProfile(models.Model):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    profile_picture_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.company_name})"


class Gig(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
        DRAFT = 'DRAFT', 'Draft'

    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='gigs')
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gigs/', blank=True, null=True)
    description = models.TextField()
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    earnings = models.CharField(max_length=50, default="", help_text="e.g. ₹500 or $10/hr")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='applications')
    suitability_note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('gig', 'student')

class AdminLog(models.Model):
    admin_email = models.EmailField()
    action = models.CharField(max_length=50)
    target = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.admin_email}: {self.action} on {self.target}"


class TelegramRegistration(models.Model):
    telegram_user_id = models.BigIntegerField(unique=True)
    telegram_chat_id = models.BigIntegerField()
    telegram_username = models.CharField(max_length=150, blank=True, null=True)
    telegram_first_name = models.CharField(max_length=150, blank=True, null=True)
    telegram_last_name = models.CharField(max_length=150, blank=True, null=True)
    student = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="telegram_registration",
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.telegram_username or f"id:{self.telegram_user_id}"
        return f"{username} -> {self.student.email}"


class TelegramEmailOTP(models.Model):
    email = models.EmailField()
    telegram_user_id = models.BigIntegerField()
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "telegram_user_id"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.telegram_user_id})"


class BotState(models.Model):
    key = models.CharField(max_length=255, unique=True, default="tg_persistence")
    user_data = models.JSONField(default=dict)
    chat_data = models.JSONField(default=dict)
    bot_data = models.JSONField(default=dict)
    conversations = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key
