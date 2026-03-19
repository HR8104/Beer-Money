import json
from django.shortcuts import render
from django.http import JsonResponse
from ..models import UserProfile, UserRole, EmployerProfile, Gig, Application
from ..decorators import employer_only, staff_only
from ..forms import GigForm, EmployerProfileForm
from ..utils import get_session_email, log_admin_action

@employer_only
def employer_dashboard_view(request):
    """Dashboard specifically for Employers."""
    email = get_session_email(request)

    # Try to find employer profile, or allow registration
    try:
        employer = EmployerProfile.objects.get(email=email)
        is_registered = True
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
    
    # Get only accepted/hired students
    hired = Application.objects.filter(gig__employer=employer, status=Application.Status.ACCEPTED).order_by('-updated_at') if employer else []

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
            'hired_count': hired.count()
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
            gig.save()
            log_admin_action(request, 'POST_GIG', gig.title, f"Gig created by {employer.email}")
            return JsonResponse({'success': True, 'message': 'Gig posted successfully!', 'id': gig.id})
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
        data = {
            'id': gig.id,
            'title': gig.title,
            'description': gig.description,
            'date': str(gig.date) if gig.date else '',
            'time': str(gig.time) if gig.time else '',
            'earnings': gig.earnings,
            'image_url': gig.image.url if gig.image else '',
            'status': gig.status
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
        gig_id = request.POST.get('gig_id') or request.POST.get('id')
        gig = Gig.objects.get(id=gig_id, employer__email=email)

        form = GigForm(request.POST, request.FILES, instance=gig)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Gig updated successfully!'})
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
        elif action == 'REJECT':
            application.status = Application.Status.REJECTED
        
        application.save()
        return JsonResponse({'success': True, 'message': f'Application {action.lower()}ed!'})
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
