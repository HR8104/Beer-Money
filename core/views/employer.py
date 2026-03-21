import json
from django.shortcuts import render
from django.http import JsonResponse
from ..models import UserProfile, UserRole, EmployerProfile, Gig, Application
from ..decorators import employer_only, staff_only
from ..forms import GigForm, EmployerProfileForm
from ..utils import (
    auto_close_expired_gigs,
    get_session_email,
    is_gig_expired,
    log_admin_action,
    notify_selected_student_on_telegram,
    post_gig_to_telegram_channel,
)

@employer_only
def employer_dashboard_view(request):
    """Dashboard specifically for Employers."""
    email = get_session_email(request)

    # Try to find employer profile, or allow registration
    try:
        employer = EmployerProfile.objects.get(email=email)
        is_registered = True
        auto_close_expired_gigs(employer=employer)
    except EmployerProfile.DoesNotExist:
        employer = None
        is_registered = False

    # Stats and gigs
    gigs = Gig.objects.filter(employer=employer).order_by('-created_at') if employer else []
    
    total_gigs = gigs.count() if employer else 0
    active_gigs_count = Gig.objects.filter(employer=employer, status=Gig.Status.ACTIVE).count() if employer else 0
    total_applications = Application.objects.filter(gig__employer=employer).count() if employer else 0
    
    # Get pending applicants only
    applicants = Application.objects.filter(gig__employer=employer, status=Application.Status.PENDING).order_by('-applied_at') if employer else []
    
    # Get only accepted/hired/completed students
    hired = Application.objects.filter(gig__employer=employer, status__in=[Application.Status.ACCEPTED, Application.Status.COMPLETED]).order_by('-updated_at') if employer else []

    return render(request, 'core/employer_dashboard.html', {
        'email': email,
        'employer': employer,
        'is_registered': is_registered,
        'gigs': gigs,
        'applicants': applicants,
        'hired': hired,
        'stats': {
            'total_gigs': total_gigs,
            'active_gigs': active_gigs_count,
            'total_apps': total_applications,
            'hired_count': hired.count() if employer else 0
        }
    })

@employer_only
def post_gig(request):
    """Post a new gig (Employer only)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    try:
        employer = EmployerProfile.objects.get(email=email)
        
        # Use request.POST and request.FILES for multipart/form-data
        form = GigForm(request.POST, request.FILES)
        if form.is_valid():
            gig = form.save(commit=False)
            gig.employer = employer
            if not gig.location:
                gig.location = employer.location
            gig.save()
            
            # Post to telegram
            log_admin_action(request, 'POST_GIG', gig.title, f"Gig created by {employer.email}")
            channel_posted = False
            channel_message = ""
            if gig.status == Gig.Status.ACTIVE:
                channel_posted, channel_message = post_gig_to_telegram_channel(gig)
                if not channel_posted:
                    log_admin_action(
                        request,
                        "TELEGRAM_POST_FAILED",
                        gig.title,
                        f"Channel post failed for gig_id={gig.id}: {channel_message}",
                    )

            response_message = 'Gig posted successfully!'
            if gig.status == Gig.Status.ACTIVE and not channel_posted:
                response_message += f" Channel post failed: {channel_message}"

            return JsonResponse(
                {
                    'success': True,
                    'message': response_message,
                    'id': gig.id,
                    'telegram_channel_posted': channel_posted,
                }
            )
        else:
            errors = form.errors.as_text()
            return JsonResponse({'success': False, 'message': f'Validation failed: {errors}'})
            
    except EmployerProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Complete employer profile first.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@employer_only
def employer_manage_gig(request):
    """Close or delete a gig."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    try:
        data = json.loads(request.body)
        gig_id = data.get('gig_id')
        action = data.get('action', '').upper() # 'CLOSE' or 'DELETE'
        
        employer = EmployerProfile.objects.get(email=email)
        gig = Gig.objects.get(id=gig_id, employer=employer)
        
        if action == 'CLOSE':
            gig.status = Gig.Status.CLOSED
            gig.save()
            log_admin_action(request, 'CLOSE_GIG', gig.title, f"Gig closed by {email}")
            return JsonResponse({'success': True, 'message': 'Gig marked as closed.'})
        elif action == 'DELETE':
            gig.delete()
            return JsonResponse({'success': True, 'message': 'Gig deleted.'})
        
        return JsonResponse({'success': False, 'message': 'Invalid action.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@staff_only
def get_gig_details(request):
    """Get details of a single gig for editing."""
    email = get_session_email(request)
    gig_id = request.GET.get('id')
    try:
        # Allow admins or the owner employer
        is_admin = UserRole.objects.filter(email=email, role=UserRole.Roles.ADMIN).exists()
        if is_admin:
            gig = Gig.objects.get(id=gig_id)
        else:
            gig = Gig.objects.get(id=gig_id, employer__email=email)

        if gig.status == Gig.Status.ACTIVE and is_gig_expired(gig):
            gig.status = Gig.Status.CLOSED
            gig.save(update_fields=["status", "updated_at"])

        data = {
            'id': gig.id,
            'title': gig.title,
            'description': gig.description,
            'date': str(gig.date) if gig.date else '',
            'start_time': gig.start_time.strftime('%H:%M') if gig.start_time else '',
            'end_time': gig.end_time.strftime('%H:%M') if gig.end_time else '',
            'earnings': str(gig.earnings),
            'image_url': gig.image.url if gig.image else '',
            'status': gig.status,
            'location': gig.location
        }
        return JsonResponse({'success': True, 'data': data})
    except Gig.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Gig not found.'})

@employer_only
def update_gig(request):
    """Update existing gig fields."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    try:
        employer = EmployerProfile.objects.get(email=email)
        gig_id = request.POST.get('gig_id') or request.POST.get('id')
        mode = (request.POST.get('mode') or 'edit').strip().lower()
        gig = Gig.objects.get(id=gig_id, employer=employer)

        if mode == 'reuse':
            form = GigForm(request.POST, request.FILES) # Create NEW instance
        else:
            form = GigForm(request.POST, request.FILES, instance=gig)

        if form.is_valid():
            updated_gig = form.save(commit=False)
            updated_gig.employer = employer
            if mode == 'reuse':
                updated_gig.status = Gig.Status.ACTIVE
                # Copy old image if no new one uploaded
                if not updated_gig.image and gig.image:
                    updated_gig.image = gig.image
                # For reuse, if location is empty in form, pull from employer
                if not updated_gig.location:
                    updated_gig.location = employer.location
            updated_gig.save()
            return JsonResponse({'success': True, 'message': 'Gig ' + ('created' if mode == 'reuse' else 'updated') + ' successfully!'})
        else:
            return JsonResponse({'success': False, 'message': f'Validation failed: {form.errors.as_text()}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@employer_only
def manage_application(request):
    """Accept or Reject a student application."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    try:
        data = json.loads(request.body)
        app_id = data.get('application_id') or data.get('app_id')
        action = data.get('action') # 'ACCEPT' or 'REJECT'

        application = Application.objects.get(id=app_id, gig__employer__email=email)
        
        if action == 'ACCEPT':
            application.status = Application.Status.ACCEPTED
            log_admin_action(request, 'HIRE_STUDENT', application.student.email, f"Student hired for '{application.gig.title}'")
            notified, notify_message = notify_selected_student_on_telegram(application)
            if not notified:
                log_admin_action(
                    request,
                    "TELEGRAM_NOTIFY_FAILED",
                    application.student.email,
                    f"Selection notification failed for app_id={application.id}: {notify_message}",
                )
        elif action == 'REJECT':
            application.status = Application.Status.REJECTED
        elif action == 'COMPLETED':
            application.status = Application.Status.COMPLETED
            log_admin_action(request, 'COMPLETE_GIG', application.student.email, f"Gig completed by {application.student.email} for '{application.gig.title}'")
        
        application.save()
        return JsonResponse({'success': True, 'message': f'Application {action.lower() if action != "COMPLETED" else "marked as complete"}.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@employer_only
def register_employer(request):
    """Create or update employer profile."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    email = get_session_email(request)
    
    try:
        data = json.loads(request.body)
        try:
            employer = EmployerProfile.objects.get(email=email)
            form = EmployerProfileForm(data, instance=employer)
        except EmployerProfile.DoesNotExist:
            form = EmployerProfileForm(data)

        if form.is_valid():
            emp = form.save(commit=False)
            emp.email = email
            emp.save()
            return JsonResponse({'success': True, 'message': 'Profile saved!'})
        else:
            return JsonResponse({'success': False, 'message': f'Validation error: {form.errors.as_text()}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def get_employer_details(request):
    """Get public-ish details of an employer (for gig preview)."""
    emp_id = request.GET.get('id')
    try:
        e = EmployerProfile.objects.get(id=emp_id)
        data = {
            'id': e.id,
            'company_name': e.company_name,
            'full_name': e.full_name,
            'location': e.location,
            'email': e.email,
            'phone': e.phone,
            'profile_picture_url': e.profile_picture_url or '',
        }
        return JsonResponse({'success': True, 'data': data})
    except EmployerProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Not found.'})
