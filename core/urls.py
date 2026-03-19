from django.urls import path
from .views import admin as admin_views
from .views import auth, employer, main, student

urlpatterns = [
    path('', main.index, name='index'),
    path('login/', main.login_view, name='login'),
    path('home/', student.home_view, name='home'),
    path('logout/', main.logout_view, name='logout'),
    path('dashboard/', main.dashboard_view, name='dashboard'),

    # API endpoints
    path('api/send-otp/', auth.send_otp, name='send_otp'),
    path('api/verify-otp/', auth.verify_otp, name='verify_otp'),
    path('api/resend-otp/', auth.resend_otp, name='resend_otp'),
    path('api/register/', auth.register_user, name='register_user'),

    # Admin endpoints
    path('admin-dashboard/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('api/admin/toggle-ban/', admin_views.admin_toggle_ban, name='admin_toggle_ban'),
    path('api/admin/delete-student/', admin_views.admin_delete_student, name='admin_delete_student'),
    path('api/admin/student/', admin_views.admin_get_student, name='admin_get_student'),
    path('api/admin/add-staff/', admin_views.admin_add_staff, name='admin_add_staff'),
    path('api/admin/delete-staff/', admin_views.admin_delete_staff, name='admin_delete_staff'),
    path('api/admin/toggle-freeze/', admin_views.admin_toggle_freeze, name='admin_toggle_freeze'),
    path('api/admin/delete-gig/', admin_views.admin_delete_gig, name='admin_delete_gig'),

    # Employer endpoints
    path('employer-dashboard/', employer.employer_dashboard_view, name='employer_dashboard'),
    path('api/register-employer/', employer.register_employer, name='register_employer'),
    path('api/post-gig/', employer.post_gig, name='post_gig'),
    path('api/employer/manage-gig/', employer.employer_manage_gig, name='employer_manage_gig'),
    path('api/employer/get-gig/', employer.get_gig_details, name='get_gig_details'),
    path('api/employer/update-gig/', employer.update_gig, name='update_gig'),
    path('api/employer/manage-application/', employer.manage_application, name='manage_application'),
    path('api/employer/details/', employer.get_employer_details, name='get_employer_details'),
    path('api/student/apply/', student.apply_to_gig, name='apply_to_gig'),
    path('api/update-profile/', auth.update_profile, name='update_profile'),
]
