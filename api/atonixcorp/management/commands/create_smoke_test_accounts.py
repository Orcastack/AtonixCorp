from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from finances.models import Organization, Role, TeamMember


class Command(BaseCommand):
    help = 'Create or update owner, admin, member, and viewer test identities for authenticated smoke testing.'

    def add_arguments(self, parser):
        parser.add_argument('--organization-id', type=int, required=True)
        parser.add_argument('--password', help='Shared temporary password. Prefer the secure prompt when running interactively.')
        parser.add_argument('--email-prefix', default='smoke-test')

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(pk=options['organization_id'])
        except Organization.DoesNotExist as error:
            raise CommandError('Organization was not found.') from error

        Role.get_or_create_default_roles()
        user_model = get_user_model()
        password = options['password']
        if not password:
            from getpass import getpass

            password = getpass('Temporary smoke-test password: ')
        if not password:
            raise CommandError('A non-empty temporary password is required.')
        prefix = options['email_prefix'].strip().lower()
        roles = {
            'admin': 'CFO',
            'member': 'FINANCE_ANALYST',
            'viewer': 'VIEWER',
        }
        created = []

        for label, role_code in roles.items():
            email = f'{prefix}-{label}@example.test'
            user, user_created = user_model.objects.get_or_create(
                username=f'{prefix}-{label}',
                defaults={'email': email},
            )
            user.email = email
            user.set_password(password)
            user.save(update_fields=['email', 'password'])
            TeamMember.objects.update_or_create(
                organization=organization,
                user=user,
                defaults={'role': Role.objects.get(code=role_code), 'is_active': True},
            )
            created.append(f'{label}: {email}' + (' (created)' if user_created else ' (updated)'))

        owner = organization.owner
        owner.set_password(password)
        owner.save(update_fields=['password'])
        created.insert(0, f'owner: {owner.email or owner.username} (updated)')
        self.stdout.write(self.style.SUCCESS('\n'.join(created)))
