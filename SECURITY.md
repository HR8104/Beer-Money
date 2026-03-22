# Security Guide (Simple + Technical)

This document explains how the project is protected, in plain language first, and technical details second.

## Why This Matters
Our app handles personal data (email, phone, student/employer details) and login verification (OTP). Security controls reduce the chance of:
- unauthorized access
- fake requests from bots
- account abuse (OTP spam/guessing)
- data leaks

---

## 1) Webhook Protection (Telegram)
### In simple terms
Only Telegram should be able to send bot updates to our server. Random internet users must be blocked.

### How we do it
- We require a secret token on Telegram webhook requests.
- If token is missing or wrong, request is rejected.

### Config
- `TELEGRAM_WEBHOOK_SECRET`

### Where in code
- `core/views/telegram.py`

---

## 2) Access Control (Who Can See What)
### In simple terms
Users should only see data they are allowed to see.

### How we do it
- Employer details endpoint requires login.
- Reviews endpoint requires login and ownership/admin rights.
- Unauthorized users get blocked.

### Where in code
- `core/views/employer.py`
- `core/views/reviews.py`

---

## 3) Safer Login OTP (Anti-Abuse)
### In simple terms
If someone repeatedly requests OTPs or guesses OTP codes, we slow/block them.

### How we do it
- Rate limits for OTP send/resend/verify.
- Temporary lockout after too many wrong OTP attempts.
- Security logs/alerts for suspicious activity.

### Important settings
- `OTP_SEND_RATE_LIMIT`
- `OTP_VERIFY_RATE_LIMIT`
- `OTP_RESEND_RATE_LIMIT`
- `OTP_VERIFY_MAX_FAILURES`
- `OTP_VERIFY_LOCKOUT_SECONDS`

### Where in code
- `core/views/auth.py`
- `core/security.py`

---

## 4) Browser + Cookie Security
### In simple terms
We force secure website behavior so user sessions/cookies are harder to steal.

### How we do it
- HTTPS redirects in production.
- Secure/HTTPOnly cookies.
- HSTS enabled.
- Security headers (CSP, Referrer-Policy, Permissions-Policy).

### Where in code
- `beermoney/settings.py`
- `core/middleware.py`

---

## 5) Error Safety
### In simple terms
Users should not see internal crash details. Attackers can use those details.

### How we do it
- Return safe generic error messages to users.
- Keep full technical details in server logs for developers.

### Where in code
- `core/views/auth.py`
- `core/views/employer.py`
- `core/views/reviews.py`
- `core/views/student.py`
- `core/views/telegram.py`

---

## 6) Monitoring and Alerts
### In simple terms
We keep a security activity trail and send alerts for dangerous patterns.

### How we do it
- Structured security logs (`core.security` logger).
- Optional email alerts for high-risk events (ex: OTP lockout).

### Config
- `SECURITY_LOG_LEVEL`
- `SECURITY_ALERT_EMAILS`

### Where in code
- `core/security.py`
- `core/utils.py`

---

## 7) Dependency Vulnerability Checks (Automated)
### In simple terms
Third-party packages can have known security issues. We scan for them automatically.

### How we do it
- GitHub Actions workflow runs `pip-audit` and `safety` on push/PR.

### Where in code
- `.github/workflows/security.yml`

---

## 8) Secret Management (Passwords/Tokens)
### In simple terms
Never hardcode passwords or tokens in code. Rotate them if exposed.

### Secrets to protect
- `SECRET_KEY`
- `EMAIL_HOST_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`

### If a secret might be leaked
1. Rotate it immediately in your hosting environment.
2. Restart the app.
3. Reconfigure webhook if Telegram secret changed.
4. Monitor logs for suspicious activity.

---

## 9) Security Tests (Proof It Works)
### In simple terms
We wrote tests that verify core protections stay active.

### Current coverage
- webhook secret enforcement
- endpoint auth rules
- object-level review authorization
- OTP rate limit
- OTP lockout

### Where in code
- `core/tests.py`

---

## 10) Non-Technical Checklist (Weekly)
Anyone on operations/product can follow this:
1. Confirm login/OTP works for normal users.
2. Confirm no unusual spikes in OTP failures.
3. Confirm no repeated webhook rejections from unknown sources.
4. Confirm dependency security workflow is passing on latest PRs.
5. Confirm security alert email inbox is monitored.

---

## Production Minimum Settings
Set these before go-live:
- `DEBUG=False`
- explicit `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` set
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS>0`
- `TELEGRAM_WEBHOOK_SECRET` set
- `SECURITY_ALERT_EMAILS` set

---

## Notes
- Security is continuous, not one-time. Revisit this document whenever we add new endpoints, integrations, or authentication flows.
