from django.shortcuts import redirect
from functools import wraps
from django.http import JsonResponse
from .models import UserRole
from .utils import get_session_email, is_api_request

def role_required(allowed_roles):
    """
    Decorator to restrict access based on UserRole.
    Expects 'user_email' in session.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            email = get_session_email(request)
            if not email:
                if is_api_request(request):
                    return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)
                return redirect('login')
            
            # Always check current role status in DB (freeze may change)
            role_obj = UserRole.objects.filter(email=email).first()
            if role_obj and role_obj.is_frozen:
                if is_api_request(request):
                    return JsonResponse({'success': False, 'message': 'Account is frozen.'}, status=403)
                return redirect('login')

            # Check cached role in session or fetch from DB
            user_role = request.session.get('user_role')

            if not user_role:
                if role_obj:
                    user_role = role_obj.role
                    request.session['user_role'] = user_role
                else:
                    user_role = UserRole.Roles.STUDENT # Default fallback
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # If not allowed, redirect to their default home
            if is_api_request(request):
                return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
                
            if user_role == UserRole.Roles.ADMIN:
                return redirect('admin_dashboard')
            elif user_role == UserRole.Roles.EMPLOYER:
                return redirect('employer_dashboard')
            else:
                return redirect('home')
                
        return _wrapped_view
    return decorator

# Specific shortcuts
def admin_only(view_func):
    return role_required([UserRole.Roles.ADMIN])(view_func)

def employer_only(view_func):
    return role_required([UserRole.Roles.EMPLOYER])(view_func)

def student_only(view_func):
    return role_required([UserRole.Roles.STUDENT])(view_func)

def staff_only(view_func):
    return role_required([UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER])(view_func)
