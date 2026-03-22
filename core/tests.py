import json

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import Application, EmployerProfile, Gig, Review, UserProfile, UserRole


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class SecurityHardeningTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _login_as(self, email: str, role: str):
        UserRole.objects.update_or_create(email=email, defaults={"role": role})
        session = self.client.session
        session["user_email"] = email
        session["user_role"] = role
        session["is_authenticated"] = True
        session.save()

    def test_employer_details_requires_auth(self):
        response = self.client.get("/api/employer/details/?id=1")
        self.assertEqual(response.status_code, 401)

    def test_reviews_require_owner_or_admin(self):
        employer = EmployerProfile.objects.create(
            email="emp@example.com",
            full_name="Emp",
            phone="9999999999",
            company_name="Acme",
            location="City",
        )
        student_owner = UserProfile.objects.create(
            email="student1@example.com",
            full_name="Student One",
            mobile="8888888888",
            gender="male",
            dob="2000-01-01",
            college="College",
            about="About text",
            skills="python",
        )
        other_student = UserProfile.objects.create(
            email="student2@example.com",
            full_name="Student Two",
            mobile="7777777777",
            gender="female",
            dob="2001-01-01",
            college="College",
            about="About text",
            skills="design",
        )

        gig = Gig.objects.create(
            employer=employer,
            title="Campus Promo",
            description="Promote on campus",
            earnings="1000.00",
            status=Gig.Status.ACTIVE,
        )
        application = Application.objects.create(
            gig=gig,
            student=student_owner,
            status=Application.Status.COMPLETED,
            suitability_note="I am suitable because I have prior experience.",
        )
        Review.objects.create(
            application=application,
            reviewer_email=employer.email,
            reviewee_email=student_owner.email,
            rating=5,
            comment="Great work",
        )

        self._login_as(other_student.email, UserRole.Roles.STUDENT)
        response = self.client.get(f"/api/reviews/get/?application_id={application.id}")
        self.assertEqual(response.status_code, 403)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="supersecret")
    def test_telegram_webhook_rejects_without_valid_secret(self):
        response = self.client.post(
            "/telegram-webhook/",
            data=json.dumps({"update_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        response2 = self.client.post(
            "/telegram-webhook/",
            data=json.dumps({"update_id": 1}),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong",
        )
        self.assertEqual(response2.status_code, 401)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        OTP_SEND_RATE_LIMIT=1,
        OTP_RATE_LIMIT_WINDOW_SECONDS=300,
    )
    def test_send_otp_rate_limited(self):
        payload = {"email": "rate@test.com"}

        first = self.client.post(
            "/api/send-otp/",
            data=json.dumps(payload),
            content_type="application/json",
            REMOTE_ADDR="1.2.3.4",
        )
        second = self.client.post(
            "/api/send-otp/",
            data=json.dumps(payload),
            content_type="application/json",
            REMOTE_ADDR="1.2.3.4",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    @override_settings(
        OTP_VERIFY_MAX_FAILURES=2,
        OTP_VERIFY_LOCKOUT_SECONDS=300,
        OTP_VERIFY_RATE_LIMIT=10,
        OTP_RATE_LIMIT_WINDOW_SECONDS=300,
    )
    def test_verify_otp_locks_after_max_failures(self):
        session = self.client.session
        session["otp"] = "123456"
        session["otp_email"] = "lock@test.com"
        session["otp_created"] = timezone.now().isoformat()
        session.save()

        first = self.client.post(
            "/api/verify-otp/",
            data=json.dumps({"otp": "000000"}),
            content_type="application/json",
            REMOTE_ADDR="2.2.2.2",
        )
        second = self.client.post(
            "/api/verify-otp/",
            data=json.dumps({"otp": "111111"}),
            content_type="application/json",
            REMOTE_ADDR="2.2.2.2",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
