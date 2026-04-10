# Beer Money

Beer Money is a Django-based platform designed to connect employers with students for short-term gigs and tasks. It features a dual-platform registration system allowing users to sign up via the web interface or an integrated Telegram bot.

## Core Features

- **User Roles:**
  - **Student:** Can browse and apply to gigs, manage their profile, and register via web or Telegram.
  - **Employer:** Can create profiles, post gigs, manage applications, and review students.
  - **Admin:** Can oversee operations, freeze accounts, ban users, and manage staff and gigs.
- **Authentication:** Features an OTP-based authentication system.
- **Telegram Bot Integration:** Fully integrated Telegram bot for ease of registration, notifications, and interaction.
- **Review System:** Both employers and students can leave reviews after an application/gig is completed.
- **Dashboard Interfaces:** Dedicated dashboards tailored to Admins, Employers, and Students.

## Tech Stack

- **Backend Framework:** Django (Version 5.1.15)
- **Database:** PostgreSQL (with `psycopg` connector)
- **Telegram Bot:** `python-telegram-bot`
- **Static Files:** `Whitenoise` for serving static assets.
- **Images:** `Pillow` for handling profile and gig image uploads.
- **Other libraries:** `djangorestframework`, `djangorestframework-simplejwt`

## Project Structure

- `beermoney/`: The main Django project configuration directory containing settings, routing (`urls.py`), and ASGI/WSGI configs.
- `core/`: The core application module that houses the business logic.
  - `models.py`: Database schemas including `UserProfile`, `EmployerProfile`, `Gig`, `Application`, `Review`, `TelegramRegistration`, etc.
  - `urls.py`: URL mappings for web pages, APIs, and Webhook endpoints for Telegram.
  - `views/`: Contains view controllers split by domain (`main.py`, `admin.py`, `auth.py`, `employer.py`, `student.py`, `telegram.py`, `reviews.py`).
  - `templates/`: HTML templates for the application pages.
  - `static/`: Static assets such as CSS, JS, and image assets.
  - `telegram_bot.py`: Handles Telegram Bot interaction and logic.
- `requirements.txt`: Project dependencies.
- `manage.py`: Django command-line utility.

## Setup Instructions

1. **Clone the repository.**
2. **Create a virtual environment** and activate it.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in necessary database, SMTP, and Telegram Bot credentials.
   ```bash
   cp .env.example .env
   ```
5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```
6. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```

## Webhooks setup (for Telegram)

The application uses webhooks for its Telegram bot. Ensure your application is running on a publicly accessible HTTPS URL mapping to `/set-telegram-webhook/` to initialize this feature.

## Security

Please see the `SECURITY.md` file for security policies and reporting vulnerabilities.
