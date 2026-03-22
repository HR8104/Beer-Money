import json
import logging

from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render

from ..decorators import student_only
from ..models import Application, Gig, UserProfile
from ..utils import auto_close_expired_gigs, get_session_email, is_gig_expired

logger = logging.getLogger(__name__)


@student_only
def home_view(request):
    """Main feed for students; shows available gigs."""
    email = get_session_email(request)
    auto_close_expired_gigs()

    try:
        profile = UserProfile.objects.get(email=email)
        is_registered = True
    except UserProfile.DoesNotExist:
        profile = None
        is_registered = False

    gigs = Gig.objects.filter(status=Gig.Status.ACTIVE).order_by("-created_at")

    applied_gig_ids = []
    applications = []
    hired_applications = []
    stats = {"pending": 0, "accepted": 0, "rejected": 0}

    if is_registered:
        applications = (
            Application.objects.filter(student=profile)
            .select_related("gig", "gig__employer")
            .order_by("-applied_at")
        )
        applied_gig_ids = applications.values_list("gig_id", flat=True)
        hired_applications = applications.filter(status__in=[Application.Status.ACCEPTED, Application.Status.COMPLETED])

        stats["pending"] = applications.filter(status=Application.Status.PENDING).count()
        stats["accepted"] = hired_applications.count()
        stats["rejected"] = applications.filter(status=Application.Status.REJECTED).count()

    return render(
        request,
        "core/home.html",
        {
            "email": email,
            "profile": profile,
            "is_registered": is_registered,
            "gigs": gigs,
            "applied_gig_ids": list(applied_gig_ids),
            "applications": applications,
            "hired_applications": hired_applications,
            "stats": stats,
        },
    )


@student_only
def apply_to_gig(request):
    """Student applies for a gig."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method."}, status=405)

    email = get_session_email(request)
    try:
        student = UserProfile.objects.get(email=email)
        data = json.loads(request.body)
        gig_id = data.get("gig_id")
        suitability_note = (data.get("suitability_note") or "").strip()

        if len(suitability_note) < 10:
            return JsonResponse(
                {"success": False, "message": "Please write at least 10 characters about why you are suitable."}
            )

        gig = Gig.objects.get(id=gig_id)
        if gig.status == Gig.Status.ACTIVE and is_gig_expired(gig):
            gig.status = Gig.Status.CLOSED
            gig.save(update_fields=["status", "updated_at"])
        if gig.status != Gig.Status.ACTIVE:
            return JsonResponse(
                {"success": False, "message": "This gig is no longer accepting applications."}
            )

        Application.objects.create(student=student, gig=gig, suitability_note=suitability_note)
        return JsonResponse({"success": True, "message": "Application submitted successfully!"})
    except UserProfile.DoesNotExist:
        return JsonResponse({"success": False, "message": "Please complete your profile first."})
    except Gig.DoesNotExist:
        return JsonResponse({"success": False, "message": "Gig not found."})
    except IntegrityError:
        return JsonResponse({"success": False, "message": "You have already applied for this gig."})
    except Exception as exc:
        logger.exception("apply_to_gig failed for %s", email)
        return JsonResponse({"success": False, "message": "Application failed. Please try again."}, status=500)
