from django.core.management.base import BaseCommand

from finances.banking_services import sync_banking_integration
from finances.models import BankingIntegration


class Command(BaseCommand):
    help = 'Run scheduled banking syncs for active integrations.'

    def handle(self, *args, **options):
        synced = 0
        skipped = 0

        for integration in BankingIntegration.objects.filter(is_active=True).order_by('organization_id', 'id'):
            try:
                sync_banking_integration(integration, payload={}, initiated_by=None, trigger_type='scheduled')
                synced += 1
            except Exception as exc:
                skipped += 1
                self.stderr.write(self.style.WARNING(f'Skipped integration {integration.id}: {exc}'))

        self.stdout.write(self.style.SUCCESS(f'Completed scheduled banking syncs. synced={synced} skipped={skipped}'))