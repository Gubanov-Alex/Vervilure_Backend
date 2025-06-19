from allauth.socialaccount.models import SocialApp
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Clean up duplicate Google OAuth SocialApp entries."""

    help = "Remove duplicate Google OAuth SocialApp configurations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be deleted without actually deleting"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find Google OAuth apps
        google_apps = SocialApp.objects.filter(provider="google")

        if google_apps.count() <= 1:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Found {google_apps.count()} Google OAuth app(s). No duplicates to clean.")
            )
            return

        self.stdout.write(self.style.WARNING(f"⚠️  Found {google_apps.count()} Google OAuth apps:"))

        for i, app in enumerate(google_apps):
            self.stdout.write(f"  {i + 1}. ID: {app.id}, Name: '{app.name}', Client ID: {app.client_id[:10]}...")

        # Keep the first one, delete the rest
        apps_to_keep = google_apps[:1]
        apps_to_delete = google_apps[1:]

        if dry_run:
            self.stdout.write("\n🔍 DRY RUN - Would delete:")
            for app in apps_to_delete:
                self.stdout.write(f"  - ID: {app.id}, Name: '{app.name}'")
            self.stdout.write(f"\n✅ Would keep: ID: {apps_to_keep[0].id}, Name: '{apps_to_keep[0].name}'")
        else:
            self.stdout.write(f"\n🗑️  Deleting {len(apps_to_delete)} duplicate(s):")

            for app in apps_to_delete:
                self.stdout.write(f"  - Deleting ID: {app.id}, Name: '{app.name}'")
                app.delete()

            self.stdout.write(self.style.SUCCESS(f"✅ Cleanup complete. Kept: ID: {apps_to_keep[0].id}"))
