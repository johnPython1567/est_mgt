from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from pages.models import SavedSearch


class Command(BaseCommand):
    help = (
        "Check every saved search for new matching properties and "
        "email users about them. Intended to run once a day via an "
        "external scheduler hitting the trigger-saved-search-check "
        "endpoint (Render's free tier has no built-in cron jobs)."
    )

    def handle(self, *args, **options):
        checked_at = timezone.now()
        total_searches = 0
        emails_sent = 0

        for search in SavedSearch.objects.select_related(
            "user", "property_type"
        ):
            total_searches += 1
            new_matches = list(search.new_matches())

            if new_matches:
                subject = (
                    f"{len(new_matches)} new propert"
                    f"{'y' if len(new_matches) == 1 else 'ies'} "
                    "matching your saved search"
                )

                message = render_to_string(
                    "emails/saved_search_alert.txt",
                    {
                        "user": search.user,
                        "search": search,
                        "properties": new_matches,
                        "site_url": getattr(
                            settings,
                            "SITE_URL",
                            "https://est-mgt.onrender.com",
                        ),
                    },
                )

                # fail_silently=True: one user's bad/invalid email
                # address shouldn't crash the whole run and prevent
                # every other user's alert from being checked.
                sent = send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [search.user.email],
                    fail_silently=True,
                )

                if sent:
                    emails_sent += 1

            # Always advance the checkpoint, whether or not there
            # were new matches this run -- otherwise the same
            # already-seen properties would keep re-triggering an
            # alert on every future run.
            search.last_checked_at = checked_at
            search.save(update_fields=["last_checked_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {total_searches} saved search(es), "
                f"sent {emails_sent} email(s)."
            )
        )