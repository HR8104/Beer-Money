from django.core.management.base import BaseCommand

from core.utils import auto_close_expired_gigs


class Command(BaseCommand):
    help = "Auto-close gigs whose date/time has expired."

    def handle(self, *args, **options):
        closed_count = auto_close_expired_gigs()
        self.stdout.write(self.style.SUCCESS(f"Closed {closed_count} expired gig(s)."))
