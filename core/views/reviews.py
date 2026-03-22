import json
import logging
from django.http import JsonResponse
from ..decorators import role_required
from ..models import Application, Review, UserRole
from ..utils import get_session_email, log_admin_action, get_admin_emails

logger = logging.getLogger(__name__)

@role_required([UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER, UserRole.Roles.STUDENT])
def submit_review(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)
    
    email = get_session_email(request)
    if not email:
        return JsonResponse({'success': False, 'message': 'Not authenticated.'}, status=401)
    
    try:
        data = json.loads(request.body)
        app_id = data.get('application_id')
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '').strip()
        
        if not (1 <= rating <= 5):
            return JsonResponse({'success': False, 'message': 'Invalid rating. Please provide 1-5.'})
            
        application = Application.objects.get(id=app_id)
        
        # Check if the user is either the employer or the student of this application
        is_employer = (application.gig.employer.email == email)
        is_student = (application.student.email == email)
        
        if not (is_employer or is_student):
             return JsonResponse({'success': False, 'message': 'Unauthorized.'})
        
        if application.status != Application.Status.COMPLETED:
             return JsonResponse({'success': False, 'message': 'Gig not completed yet.'})
        
        reviewee_email = application.student.email if is_employer else application.gig.employer.email
        
        Review.objects.update_or_create(
            application=application,
            reviewer_email=email,
            defaults={
                'reviewee_email': reviewee_email,
                'rating': rating,
                'comment': comment
            }
        )
        
        log_admin_action(request, 'SUBMIT_REVIEW', application.gig.title, f"Review submitted by {email} for {reviewee_email}")
        
        return JsonResponse({'success': True, 'message': 'Review submitted successfully!'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid rating. Please provide 1-5.'})
    except Application.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Application not found.'})
    except Exception as e:
        logger.exception("submit_review failed for %s", email)
        return JsonResponse({'success': False, 'message': 'Review submission failed. Please try again.'}, status=500)

@role_required([UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER, UserRole.Roles.STUDENT])
def get_reviews_for_application(request):
    """Optional: View to get both reviews for an application."""
    app_id = request.GET.get('application_id')
    if not (app_id and str(app_id).isdigit()):
        return JsonResponse({'success': False, 'message': 'Invalid application id.'}, status=400)

    email = get_session_email(request)
    try:
        application = Application.objects.get(id=app_id)

        is_admin = email in get_admin_emails() or UserRole.objects.filter(
            email=email, role=UserRole.Roles.ADMIN
        ).exists()
        is_owner = email in {application.student.email, application.gig.employer.email}
        if not (is_admin or is_owner):
            return JsonResponse({'success': False, 'message': 'Unauthorized.'}, status=403)

        reviews = application.reviews.all()
        data = []
        for r in reviews:
            data.append({
                'reviewer': r.reviewer_email,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({'success': True, 'reviews': data})
    except Application.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Application not found.'})
    except Exception as e:
        logger.exception("get_reviews_for_application failed for %s", email)
        return JsonResponse({'success': False, 'message': 'Could not fetch reviews.'}, status=500)
