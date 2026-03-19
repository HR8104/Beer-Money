import json

from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render

from ..decorators import admin_only, role_required
from ..models import AdminLog, Application, EmployerProfile, Gig, UserProfile, UserRole
from ..utils import get_admin_emails, get_session_email, log_admin_action


@admin_only
def admin_dashboard_view(request):
    """Master Admin Dashboard, only for users with ADMIN role."""
    email = get_session_email(request)

    students = UserProfile.objects.all().order_by("-registered_at")
    total_students = students.count()

    staff_members = UserRole.objects.filter(
        role__in=[UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER]
    ).order_by("-created_at")

    total_employers = UserRole.objects.filter(role=UserRole.Roles.EMPLOYER).count()
    total_admins = UserRole.objects.filter(role=UserRole.Roles.ADMIN).count()
    total_gigs = Gig.objects.count()
    frozen_emails = list(UserRole.objects.filter(is_frozen=True).values_list("email", flat=True))
    master_admin_emails = get_admin_emails()
    gigs = Gig.objects.all().order_by("-created_at")

    page = request.GET.get("page", 1)
    paginator = Paginator(students, 10)
    students_page = paginator.get_page(page)
    logs = AdminLog.objects.all().order_by("-timestamp")[:50]

    return render(
        request,
        "core/admin_dashboard.html",
        {
            "email": email,
            "students": students_page,
            "total_students": total_students,
            "total_employers": total_employers,
            "total_admins": total_admins,
            "total_gigs": total_gigs,
            "staff_members": staff_members,
            "gigs": gigs,
            "logs": logs,
            "total_pages": paginator.num_pages,
            "frozen_emails": frozen_emails,
            "master_admin_emails": master_admin_emails,
        },
    )


@admin_only
def admin_toggle_ban(request):
    """Toggle ban/unban a student."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

    try:
        profile = UserProfile.objects.get(id=student_id)
        profile.is_banned = not profile.is_banned
        profile.save()
        status = "banned" if profile.is_banned else "unbanned"

        log_admin_action(request, "TOGGLE_BAN", profile.email, f"Student {status}. Status: {profile.is_banned}")
        return JsonResponse(
            {
                "success": True,
                "message": f"{profile.full_name} has been {status}.",
                "is_banned": profile.is_banned,
            }
        )
    except UserProfile.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found."})


@admin_only
def admin_delete_student(request):
    """Delete a student profile."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

    try:
        profile = UserProfile.objects.get(id=student_id)
        name = profile.full_name
        email = profile.email
        profile.delete()

        log_admin_action(request, "DELETE_STUDENT", email, f"Student {name} deleted.")
        return JsonResponse({"success": True, "message": f"{name} has been removed."})
    except UserProfile.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found."})


@role_required([UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER, UserRole.Roles.STUDENT])
def admin_get_student(request):
    """Get details of a single student with privacy controls."""
    email = get_session_email(request)
    student_id = request.GET.get("id")
    try:
        profile = UserProfile.objects.get(id=student_id)

        is_admin = email in get_admin_emails()
        show_full_profile = is_admin

        if not is_admin:
            try:
                employer = EmployerProfile.objects.get(email=email)
                apps = Application.objects.filter(student=profile, gig__employer=employer)
                if apps.filter(status=Application.Status.ACCEPTED).exists():
                    show_full_profile = True
                elif apps.filter(status=Application.Status.PENDING).exists():
                    show_full_profile = False
                else:
                    show_full_profile = False
            except EmployerProfile.DoesNotExist:
                show_full_profile = profile.email == email

        data = {
            "id": profile.id,
            "full_name": profile.full_name,
            "email": profile.email,
            "mobile": profile.mobile if show_full_profile else "Masked (Accept to View)",
            "gender": profile.gender,
            "dob": str(profile.dob),
            "college": profile.college,
            "about": profile.about,
            "skills": profile.skills,
            "intro_video_url": profile.intro_video_url or "",
            "profile_picture_url": profile.profile_picture_url or "",
            "is_banned": profile.is_banned,
            "registered_at": profile.registered_at.strftime("%d %b %Y, %I:%M %p"),
        }
        return JsonResponse({"success": True, "data": data})
    except UserProfile.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found."})


@admin_only
def admin_add_staff(request):
    """Add a new Admin or Employer."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        new_email = data.get("email", "").strip().lower()
        role = data.get("role", "").strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

    if not new_email or "@" not in new_email:
        return JsonResponse({"success": False, "message": "Invalid email address."})

    if role not in [UserRole.Roles.ADMIN, UserRole.Roles.EMPLOYER]:
        return JsonResponse({"success": False, "message": "Invalid role specified."})

    if new_email in get_admin_emails() and role != UserRole.Roles.ADMIN:
        return JsonResponse({"success": False, "message": "Cannot change role of a Master Admin."})

    role_obj, _ = UserRole.objects.get_or_create(email=new_email)
    role_obj.role = role
    role_obj.save()

    log_admin_action(request, "ADD_STAFF", new_email, f"Added as {role}.")
    return JsonResponse({"success": True, "message": f"Successfully added {new_email} as an {role}."})


@admin_only
def admin_delete_staff(request):
    """Permanently delete a staff account and linked profile data."""
    email = get_session_email(request)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        target_email = data.get("email", "").strip().lower()
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid request."}, status=400)

    if target_email in get_admin_emails():
        return JsonResponse({"success": False, "message": "Master Admins cannot be removed."})

    if target_email == email:
        return JsonResponse({"success": False, "message": "You cannot remove your own access."})

    try:
        role_obj = UserRole.objects.get(email=target_email)
        old_role = role_obj.role

        with transaction.atomic():
            deleted_user_profiles, _ = UserProfile.objects.filter(email=target_email).delete()
            deleted_employer_profiles, _ = EmployerProfile.objects.filter(email=target_email).delete()
            role_obj.delete()

        log_admin_action(
            request,
            "DELETE_STAFF",
            target_email,
            (
                f"Deleted role={old_role}; "
                f"user_profiles_deleted={deleted_user_profiles}; "
                f"employer_profiles_deleted={deleted_employer_profiles}."
            ),
        )
        return JsonResponse({"success": True, "message": f"{target_email} and linked details deleted."})
    except UserRole.DoesNotExist:
        return JsonResponse({"success": False, "message": "Staff member not found."})


@admin_only
def admin_toggle_freeze(request):
    """Freeze or unfreeze an account by email."""
    current_email = get_session_email(request)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        target_email = data.get("email", "").strip().lower()
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

    if not target_email:
        return JsonResponse({"success": False, "message": "Email required."}, status=400)

    if target_email in get_admin_emails():
        return JsonResponse({"success": False, "message": "Master Admins cannot be frozen."})

    if target_email == current_email:
        return JsonResponse({"success": False, "message": "You cannot freeze your own account."})

    role_obj, _ = UserRole.objects.get_or_create(email=target_email)
    role_obj.is_frozen = not role_obj.is_frozen
    role_obj.save()

    status = "frozen" if role_obj.is_frozen else "unfrozen"
    log_admin_action(request, "TOGGLE_FREEZE", target_email, f"Account {status}.")

    return JsonResponse(
        {"success": True, "message": f"{target_email} has been {status}.", "is_frozen": role_obj.is_frozen}
    )


@admin_only
def admin_delete_gig(request):
    """Delete a gig."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    try:
        data = json.loads(request.body)
        gig_id = data.get("gig_id")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

    if not gig_id:
        return JsonResponse({"success": False, "message": "Gig id required."}, status=400)

    try:
        gig = Gig.objects.get(id=gig_id)
        title = gig.title
        employer_email = gig.employer.email
        gig.delete()
        log_admin_action(request, "DELETE_GIG", employer_email, f"Gig deleted: {title}")
        return JsonResponse({"success": True, "message": f'Gig "{title}" deleted.'})
    except Gig.DoesNotExist:
        return JsonResponse({"success": False, "message": "Gig not found."})
