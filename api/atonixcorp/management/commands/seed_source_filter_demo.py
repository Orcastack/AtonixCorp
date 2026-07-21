from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finances.banking_services import complete_oauth_consent, prepare_oauth_consent, sync_banking_integration
from finances.models import BankingIntegration, Budget, Entity, Expense, Income, Organization


class Command(BaseCommand):
    help = 'Seed a repeatable mixed manual/imported finance dataset for source-filter verification.'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, default=2, help='User ID for personal income, expenses, and budgets.')
        parser.add_argument('--organization-id', type=int, default=2, help='Organization ID for the bank integration.')
        parser.add_argument('--entity-id', type=int, default=2, help='Entity ID for imported banking transactions.')
        parser.add_argument('--reset', action='store_true', help='Delete the previously seeded verification records before reseeding.')

    @transaction.atomic
    def handle(self, *args, **options):
        user = self._get_user(options['user_id'])
        organization = self._get_organization(options['organization_id'])
        entity = self._get_entity(options['entity_id'], organization)

        if options['reset']:
            self._reset_seeded_records(user, organization, entity)

        summary = self._seed_records(user, organization, entity)
        self.stdout.write(self.style.SUCCESS(f'Source filter verification data ready: {summary}'))

    def _get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(id=user_id)
        except user_model.DoesNotExist as exc:
            raise CommandError(f'User {user_id} does not exist.') from exc

    def _get_organization(self, organization_id):
        try:
            return Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist as exc:
            raise CommandError(f'Organization {organization_id} does not exist.') from exc

    def _get_entity(self, entity_id, organization):
        try:
            return Entity.objects.get(id=entity_id, organization=organization)
        except Entity.DoesNotExist as exc:
            raise CommandError(
                f'Entity {entity_id} does not exist for organization {organization.id}.'
            ) from exc

    def _reset_seeded_records(self, user, organization, entity):
        Expense.objects.filter(user=user, entity__isnull=True, description__in=self._seeded_expense_descriptions()).delete()
        Income.objects.filter(user=user, entity__isnull=True, source='Consulting Retainer').delete()
        Budget.objects.filter(user=user, entity__isnull=True, category__in=self._seeded_budget_categories()).delete()

        integration = BankingIntegration.objects.filter(
            organization=organization,
            entity=entity,
            provider_name='Plaid Verification Feed',
        ).first()
        if integration is not None:
            integration.transactions.filter(transaction_id__in=self._seeded_transaction_ids()).delete()
            integration.sync_runs.all().delete()
            integration.consent_logs.all().delete()
            integration.delete()

    def _seed_records(self, user, organization, entity):
        current_month = timezone.now().date().replace(day=5)
        previous_month = (current_month.replace(day=1) - timezone.timedelta(days=10)).replace(day=10)

        for source, amount, date in [
            ('Consulting Retainer', Decimal('12500.00'), current_month),
            ('Consulting Retainer', Decimal('11800.00'), previous_month),
        ]:
            Income.objects.update_or_create(
                user=user,
                entity=None,
                source=source,
                date=date,
                defaults={
                    'amount': amount,
                    'income_type': 'business',
                    'currency': 'USD',
                },
            )

        for category, limit, color in [
            ('Meals', Decimal('350.00'), '#ef4444'),
            ('Software', Decimal('500.00'), '#0ea5e9'),
            ('Transportation', Decimal('250.00'), '#f59e0b'),
        ]:
            Budget.objects.update_or_create(
                user=user,
                entity=None,
                category=category,
                defaults={
                    'limit': limit,
                    'spent': Decimal('0.00'),
                    'color': color,
                    'currency': 'USD',
                },
            )

        seeded_expenses = [
            ('Client lunch', Decimal('145.20'), 'Meals', current_month),
            ('Design software seat', Decimal('219.00'), 'Software', current_month),
            ('Taxi to airport', Decimal('84.50'), 'Transportation', current_month),
            ('Team lunch prior month', Decimal('96.00'), 'Meals', previous_month),
            ('Mapping software prior month', Decimal('180.00'), 'Software', previous_month),
        ]
        for description, amount, category, date in seeded_expenses:
            Expense.objects.update_or_create(
                user=user,
                entity=None,
                description=description,
                date=date,
                defaults={
                    'amount': amount,
                    'category': category,
                    'currency': 'USD',
                },
            )

        integration, _ = BankingIntegration.objects.get_or_create(
            organization=organization,
            entity=entity,
            provider_code='plaid',
            defaults={
                'integration_type': 'open_banking',
                'provider_name': 'Plaid Verification Feed',
                'status': 'pending',
                'is_active': True,
                'webhook_url': '',
            },
        )
        integration.provider_name = 'Plaid Verification Feed'
        integration.integration_type = 'open_banking'
        integration.is_active = True
        integration.entity = entity
        integration.set_api_key('demo-client-id')
        integration.set_api_secret('demo-client-secret')
        integration.save()

        if not integration.consent_granted_at:
            state = prepare_oauth_consent(
                integration,
                redirect_uri='http://localhost:3000/firm/integrations',
                requested_by=user,
                scopes=['accounts:read', 'transactions:read'],
            )['state']
            complete_oauth_consent(
                integration,
                authorization_code='verify-code',
                state=state,
                requested_by=user,
            )

        sync_run = sync_banking_integration(
            integration,
            payload={
                'accounts': [
                    {
                        'account_id': 'ux_verify_checking',
                        'name': 'UX Verify Operating',
                        'bank_name': 'Plaid Sandbox Bank',
                        'account_type': 'business',
                        'currency': 'USD',
                        'balance': '8450.00',
                        'available_balance': '8120.00',
                    }
                ],
                'transactions': [
                    {
                        'external_id': 'uxv_txn_001',
                        'account_id': 'ux_verify_checking',
                        'date': str(current_month),
                        'amount': '-182.40',
                        'currency': 'USD',
                        'merchant': 'Starbucks',
                        'description': 'STARBUCKS UX REVIEW',
                        'raw_category': 'food_and_drink',
                    },
                    {
                        'external_id': 'uxv_txn_002',
                        'account_id': 'ux_verify_checking',
                        'date': str(current_month),
                        'amount': '-355.00',
                        'currency': 'USD',
                        'merchant': 'Adobe',
                        'description': 'ADOBE CREATIVE CLOUD',
                        'raw_category': 'software',
                    },
                    {
                        'external_id': 'uxv_txn_003',
                        'account_id': 'ux_verify_checking',
                        'date': str(current_month),
                        'amount': '-148.75',
                        'currency': 'USD',
                        'merchant': 'Uber',
                        'description': 'UBER TRIP AIRPORT',
                        'raw_category': 'transportation',
                    },
                    {
                        'external_id': 'uxv_txn_004',
                        'account_id': 'ux_verify_checking',
                        'date': str(previous_month),
                        'amount': '-72.10',
                        'currency': 'USD',
                        'merchant': 'Starbucks',
                        'description': 'STARBUCKS PRIOR MONTH',
                        'raw_category': 'food_and_drink',
                    },
                    {
                        'external_id': 'uxv_txn_005',
                        'account_id': 'ux_verify_checking',
                        'date': str(previous_month),
                        'amount': '-120.00',
                        'currency': 'USD',
                        'merchant': 'Uber',
                        'description': 'UBER PRIOR MONTH',
                        'raw_category': 'transportation',
                    },
                ],
            },
            initiated_by=user,
            trigger_type='manual',
        )

        return {
            'personal_expenses': Expense.objects.filter(user=user, entity__isnull=True).count(),
            'personal_income': Income.objects.filter(user=user, entity__isnull=True).count(),
            'personal_budgets': Budget.objects.filter(user=user, entity__isnull=True).count(),
            'integration_id': integration.id,
            'bank_transactions': integration.transactions.count(),
            'sync_run_id': sync_run.id,
        }

    def _seeded_expense_descriptions(self):
        return [
            'Client lunch',
            'Design software seat',
            'Taxi to airport',
            'Team lunch prior month',
            'Mapping software prior month',
        ]

    def _seeded_budget_categories(self):
        return ['Meals', 'Software', 'Transportation']

    def _seeded_transaction_ids(self):
        return ['uxv_txn_001', 'uxv_txn_002', 'uxv_txn_003', 'uxv_txn_004', 'uxv_txn_005']