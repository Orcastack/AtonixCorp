from django.core.management.base import BaseCommand

from finances.enterprise_reporting import run_due_automation_workflows


class Command(BaseCommand):
    help = 'Run due scheduled automation workflows, including enterprise reporting deliveries.'

    def handle(self, *args, **options):
        results = run_due_automation_workflows()
        self.stdout.write(
            self.style.SUCCESS(
                'Completed scheduled automation workflows. '
                f"completed={results['completed']} failed={results['failed']} skipped={results['skipped']} "
                f"artifacts_deleted={results['artifacts_deleted']} bytes_reclaimed={results['bytes_reclaimed']}"
            )
        )