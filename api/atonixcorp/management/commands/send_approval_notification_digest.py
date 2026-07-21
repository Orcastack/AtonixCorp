from django.core.management.base import BaseCommand

from finances.accounting_notification_delivery import send_approval_digest


class Command(BaseCommand):
    help = 'Send digest emails for unread finance approval notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='Look back window for unread approval notifications.')

    def handle(self, *args, **options):
        deliveries = send_approval_digest(hours=options['hours'])
        total_notifications = sum(item['notification_count'] for item in deliveries)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {len(deliveries)} approval digest emails covering {total_notifications} unread approval notifications."
            )
        )
