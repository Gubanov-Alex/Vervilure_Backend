# Management command for automated account cleanup

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from src.apps.accounts.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to cleanup expired deactivated accounts.

    This command should be run regularly (daily) via cron or Celery beat.
    """

    help = 'Cleanup expired deactivated accounts by anonymizing them'

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days after deactivation to consider expired (default: 30)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Force anonymization without confirmation',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        dry_run = options['dry_run']
        days = options['days']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'Starting account cleanup process...')
        )

        # Find expired deactivated accounts
        cutoff_date = timezone.now() - timedelta(days=days)
        expired_users = User.objects.filter(
            deactivated_at__lt=cutoff_date,
            is_anonymized=False,
            is_active=False
        ).select_related()

        count = expired_users.count()

        if count == 0:
            self.stdout.write(
                self.style.WARNING('No expired deactivated accounts found.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {count} expired deactivated accounts.')
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN - No changes will be made:')
            )
            for user in expired_users:
                self.stdout.write(
                    f'  - {user.email} (deactivated: {user.deactivated_at})'
                )
            return

        # Confirmation prompt
        if not force:
            confirm = input(
                f'This will anonymize {count} accounts. '
                'Are you sure you want to continue? [y/N]: '
            )
            if confirm.lower() != 'y':
                self.stdout.write(
                    self.style.ERROR('Operation cancelled.')
                )
                return

        # Process anonymization
        anonymized_count = 0
        errors = []

        for user in expired_users:
            try:
                original_email = user.email
                anonymous_id = user.anonymize_user_data()

                # Also anonymize related data if needed
                user.addresses.all().delete()

                anonymized_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Anonymized: {original_email} -> {anonymous_id}'
                    )
                )

                logger.info(
                    f"Account automatically anonymized via cleanup: {original_email}",
                    extra={
                        "user_id": user.id,
                        "anonymous_id": anonymous_id,
                        "deactivated_at": user.deactivated_at.isoformat(),
                        "action": "auto_account_anonymize"
                    }
                )

            except Exception as e:
                error_msg = f'Failed to anonymize {user.email}: {str(e)}'
                errors.append(error_msg)
                self.stdout.write(
                    self.style.ERROR(error_msg)
                )
                logger.error(
                    f"Failed to anonymize account: {user.email}",
                    extra={
                        "user_id": user.id,
                        "error": str(e),
                        "action": "auto_account_anonymize_error"
                    },
                    exc_info=True
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCleanup completed: {anonymized_count}/{count} accounts anonymized.'
            )
        )

        if errors:
            self.stdout.write(
                self.style.ERROR(f'{len(errors)} errors occurred:')
            )
            for error in errors:
                self.stdout.write(f'  - {error}')
            raise CommandError(f'{len(errors)} errors occurred during cleanup')

        # Cleanup related data
        self._cleanup_related_data()

    def _cleanup_related_data(self):
        """Cleanup related data like expired tokens."""
        from src.apps.accounts.models import BlacklistedToken

        # Remove expired blacklisted tokens
        expired_tokens = BlacklistedToken.objects.filter(
            expires_at__lt=timezone.now()
        )
        deleted_tokens = expired_tokens.count()
        expired_tokens.delete()

        if deleted_tokens > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleaned up {deleted_tokens} expired blacklisted tokens.'
                )
            )
