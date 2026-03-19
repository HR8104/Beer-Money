import random
import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from ..models import UserProfile, UserRole, EmployerProfile
from ..forms import StudentProfileForm
from ..utils import get_admin_emails, get_session_email


def _clear_otp_session(request):
    request.session.pop('otp', None)
    request.session.pop('otp_email', None)
    request.session.pop('otp_created', None)

def register_user(request):
    """Save the one-time registration form."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    if not email:
        return JsonResponse({'success': False, 'message': 'Not logged in.'}, status=401)

    try:
        data = json.loads(request.body)
        try:
            profile = UserProfile.objects.get(email=email)
            form = StudentProfileForm(data, instance=profile)
        except UserProfile.DoesNotExist:
            form = StudentProfileForm(data)

        if form.is_valid():
            profile = form.save(commit=False)
            profile.email = email
            profile.mark_registered_from(UserProfile.RegistrationPlatform.WEB)
            profile.save()
            return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})
        else:
            return JsonResponse({'success': False, 'message': f'Validation failed: {form.errors.as_text()}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Operation failed: {str(e)}'})

def send_otp(request):
    """Generate a 6-digit OTP, store in session, and email it."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)

    if not email or '@' not in email:
        return JsonResponse({'success': False, 'message': 'Please enter a valid email address.'})

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Store OTP + expiry in session
    request.session['otp'] = otp
    request.session['otp_email'] = email
    request.session['otp_created'] = timezone.now().isoformat()

    # Send email
    try:
        send_mail(
            subject='Your Beer Money Login OTP',
            message=f'Your OTP is: {otp}\n\nThis code expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n\nIf you did not request this, please ignore this email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        # Fallback: log to console for development
        print(f"[DEV] OTP for {email}: {otp}")
        print(f"[DEV] Email send error: {e}")
        # Still return success so the user can proceed during development
        return JsonResponse({
            'success': True,
            'message': f'OTP sent to {email}. (Dev mode — check server console if email fails)',
        })

    return JsonResponse({'success': True, 'message': f'OTP sent to {email}.'})

def verify_otp(request):
    """Verify the OTP the user entered against the session."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        entered_otp = data.get('otp', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)

    stored_otp = request.session.get('otp')
    stored_email = request.session.get('otp_email', '').strip().lower()
    otp_created = request.session.get('otp_created')

    if not stored_otp or not otp_created:
        return JsonResponse({'success': False, 'message': 'No OTP found. Please request a new one.'})

    # Check expiry
    created_dt = datetime.fromisoformat(otp_created)
    if timezone.is_naive(created_dt):
        created_dt = timezone.make_aware(created_dt, timezone.get_current_timezone())
    if timezone.now() - created_dt > timedelta(minutes=settings.OTP_EXPIRY_MINUTES):
        # Clear expired OTP
        _clear_otp_session(request)
        return JsonResponse({'success': False, 'message': 'OTP has expired. Please request a new one.'})

    if entered_otp != stored_otp:
        return JsonResponse({'success': False, 'message': 'Incorrect OTP. Please try again.'})

    # OTP is correct — log user in via session
    request.session['user_email'] = stored_email
    request.session['is_authenticated'] = True

    # Check for existing role, or fall back to student (default)
    role_obj, created = UserRole.objects.get_or_create(email=stored_email)
    
    if created and stored_email in get_admin_emails():
        role_obj.role = UserRole.Roles.ADMIN
        role_obj.save()

    if role_obj.is_frozen:
        return JsonResponse({'success': False, 'message': 'Your account is frozen. Please contact support.'}, status=403)

    is_admin = (role_obj.role == UserRole.Roles.ADMIN)
    request.session['is_admin'] = is_admin
    request.session['user_role'] = role_obj.role

    # Clear OTP data
    _clear_otp_session(request)

    # Redirect based on role
    if role_obj.role == UserRole.Roles.ADMIN:
        redirect_url = '/admin-dashboard/'
    elif role_obj.role == UserRole.Roles.EMPLOYER:
        redirect_url = '/employer-dashboard/'
    else:
        redirect_url = '/home/'

    return JsonResponse({'success': True, 'message': 'Login successful!', 'redirect': redirect_url})

def resend_otp(request):
    """Resend OTP using the email already stored in session."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    email = request.session.get('otp_email', '').strip().lower()
    if not email:
        return JsonResponse({'success': False, 'message': 'No email found. Please enter your email first.'})

    # Generate new OTP
    otp = str(random.randint(100000, 999999))
    request.session['otp'] = otp
    request.session['otp_created'] = timezone.now().isoformat()

    try:
        send_mail(
            subject='Your Beer Money Login OTP (Resent)',
            message=f'Your new OTP is: {otp}\n\nThis code expires in {settings.OTP_EXPIRY_MINUTES} minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"[DEV] Resent OTP for {email}: {otp}")
        print(f"[DEV] Email send error: {e}")
        return JsonResponse({'success': True, 'message': f'OTP resent to {email}. (Dev mode)'})

    return JsonResponse({'success': True, 'message': f'New OTP sent to {email}.'})

def update_profile(request):
    """General API to update profile fields (e.g., profile icon)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    if not email:
        return JsonResponse({'success': False, 'message': 'Not logged in.'}, status=401)

    try:
        data = json.loads(request.body)
        profile_picture_url = data.get('profile_picture_url', '').strip() or None
        
        # Try updating UserProfile first
        try:
            student = UserProfile.objects.get(email=email)
            student.profile_picture_url = profile_picture_url
            student.save()
            return JsonResponse({'success': True, 'message': 'Student profile updated!'})
        except UserProfile.DoesNotExist:
            # Try updating EmployerProfile
            try:
                employer = EmployerProfile.objects.get(email=email)
                employer.profile_picture_url = profile_picture_url
                employer.save()
                return JsonResponse({'success': True, 'message': 'Employer profile updated!'})
            except EmployerProfile.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Profile not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
