import os

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

try:
    from allauth.socialaccount.models import SocialApp
except ImportError:
    try:
        from allauth.socialaccount.models import SocialApplication as SocialApp
    except ImportError:
        raise ImportError(
            "django-allauth is not installed or version incompatible. " "Run: poetry add django-allauth>=65.0.0"
        )


class Command(BaseCommand):
    help = "Setup Google OAuth for django-allauth"

    def handle(self, *args, **options):
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        secret = os.environ.get("GOOGLE_OAUTH_SECRET")

        if not client_id or not secret:
            self.stdout.write(
                self.style.WARNING("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_SECRET must be set in environment")
            )
            return

        # Get or create the default site
        site = Site.objects.get_current()

        # Create or update Google OAuth app
        google_app, created = SocialApp.objects.get_or_create(
            provider="google",
            defaults={
                "name": "Google OAuth",
                "client_id": client_id,
                "secret": secret,
            },
        )

        if not created:
            google_app.client_id = client_id
            google_app.secret = secret
            google_app.save()
            self.stdout.write(self.style.SUCCESS("Updated existing Google OAuth app"))
        else:
            self.stdout.write(self.style.SUCCESS("Created new Google OAuth app"))

        # Associate with site
        google_app.sites.add(site)

        self.stdout.write(self.style.SUCCESS(f"Google OAuth configured for site: {site.domain}"))
