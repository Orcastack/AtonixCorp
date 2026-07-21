from django.core.management.base import BaseCommand

from finances.enterprise_reporting import cleanup_automation_artifacts


class Command(BaseCommand):
    help = 'Delete expired automation artifacts according to each workflow retention policy.'

    def handle(self, *args, **options):
        results = cleanup_automation_artifacts()
        self.stdout.write(
            self.style.SUCCESS(
                'Completed automation artifact cleanup. '
                f"deleted={results['deleted']} bytes_reclaimed={results['bytes_reclaimed']}"
            )
        )