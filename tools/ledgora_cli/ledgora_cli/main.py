import argparse
import json
import sys
from urllib.parse import urlencode

from .api import DEFAULT_HOST, LedgoraClient, expires_at_from_now
from .errors import CLIError, format_cli_error
from .storage import get_profile, list_profiles, remove_profile, set_current_profile, upsert_profile


def _read_api_key(args):
    if args.api_key and args.api_key_stdin:
        raise CLIError('Use either --api-key or --api-key-stdin, not both.', 'INVALID_INPUT')
    if args.api_key_stdin:
        return sys.stdin.read().strip()
    return (args.api_key or '').strip()


def _print_identity(me_response, profile_name):
    organization = me_response.get('organization') or {}
    user = me_response.get('user') or {}
    print('Successfully logged in to Ledgora')
    print(f"Organization: {organization.get('name', 'Unknown')} ({organization.get('id', 'unknown')})")
    print(f"User: {user.get('email', 'unknown')}")
    print(f"Profile: {profile_name}")


def _print_json(data):
    print(json.dumps(data, indent=2, sort_keys=True))


def _authenticated_client_session(profile_name=None):
    session = get_profile(profile_name)
    client = LedgoraClient(session['host'])
    return client, session


def _persist_session(session):
    upsert_profile(session['profile'], session, make_current=True)


def _request_with_saved_session(profile_name, method, path, *, payload=None):
    client, session = _authenticated_client_session(profile_name)
    response = client.request_with_session(method, path, session, payload=payload)
    _persist_session(session)
    return response


def command_login(args):
    api_key = _read_api_key(args)
    organization_id = (args.org or '').strip()
    if not api_key or not organization_id:
        raise CLIError('Missing required flags. Use --api-key and --org.', 'INVALID_INPUT')

    profile_name = (args.profile or 'default').strip() or 'default'
    client = LedgoraClient(args.host or DEFAULT_HOST)
    login_response = client.cli_login(api_key, organization_id)

    session = {
        'host': client.host,
        'organization_id': login_response['organization_id'],
        'organization_name': None,
        'access_token': login_response['access_token'],
        'api_key': api_key,
        'expires_at': expires_at_from_now(login_response['expires_in']),
        'user': login_response.get('user') or {},
    }
    upsert_profile(profile_name, session, make_current=True)

    try:
        me_response = client.me(session['access_token'], session['organization_id'])
    except CLIError:
        remove_profile(profile_name)
        raise

    session['organization_name'] = (me_response.get('organization') or {}).get('name')
    session['user'] = me_response.get('user') or session['user']
    session['expires_at'] = (me_response.get('session') or {}).get('expires_at') or session['expires_at']
    upsert_profile(profile_name, session, make_current=True)
    _print_identity(me_response, profile_name)
    return 0


def command_logout(args):
    remove_profile(args.profile or None)
    print('Local Ledgora CLI session removed.')
    return 0


def command_use(args):
    set_current_profile(args.profile)
    print(f'Active profile: {args.profile}')
    return 0


def command_whoami(args):
    session = get_profile(args.profile)
    client = LedgoraClient(session['host'])
    me_response = client.request_with_session('GET', '/auth/me', session)
    session['organization_name'] = (me_response.get('organization') or {}).get('name')
    session['user'] = me_response.get('user') or session.get('user') or {}
    session['expires_at'] = (me_response.get('session') or {}).get('expires_at') or session.get('expires_at')
    upsert_profile(session['profile'], session, make_current=True)
    _print_identity(me_response, session['profile'])
    return 0


def command_profiles(_args):
    profiles = list_profiles()
    if not profiles:
        print('No saved Ledgora CLI profiles.')
        return 0
    for profile in profiles:
        marker = '*' if profile['is_current'] else '-'
        print(f"{marker} {profile['name']} {profile['organization_id']} {profile['host']}")
    return 0


def command_organizations_list(args):
    response = _request_with_saved_session(args.profile, 'GET', '/v1/organizations')
    _print_json(response)
    return 0


def command_accounts_list(args):
    response = _request_with_saved_session(args.profile, 'GET', '/v1/accounts')
    _print_json(response)
    return 0


def command_customers_list(args):
    response = _request_with_saved_session(args.profile, 'GET', '/v1/customers')
    _print_json(response)
    return 0


def command_vendors_list(args):
    response = _request_with_saved_session(args.profile, 'GET', '/v1/vendors')
    _print_json(response)
    return 0


def _report_path(report_name, args):
    query = {}
    if getattr(args, 'as_of_date', None):
        query['as_of_date'] = args.as_of_date
    if getattr(args, 'from_date', None):
        query['from_date'] = args.from_date
    if getattr(args, 'to_date', None):
        query['to_date'] = args.to_date
    if getattr(args, 'currency', None):
        query['currency'] = args.currency
    suffix = f"?{urlencode(query)}" if query else ''
    return f'/v1/reports/{report_name}{suffix}'


def command_report_trial_balance(args):
    response = _request_with_saved_session(args.profile, 'GET', _report_path('trial-balance', args))
    _print_json(response)
    return 0


def command_report_profit_and_loss(args):
    response = _request_with_saved_session(args.profile, 'GET', _report_path('profit-and-loss', args))
    _print_json(response)
    return 0


def command_report_balance_sheet(args):
    response = _request_with_saved_session(args.profile, 'GET', _report_path('balance-sheet', args))
    _print_json(response)
    return 0


def command_report_cash_flow(args):
    response = _request_with_saved_session(args.profile, 'GET', _report_path('cash-flow', args))
    _print_json(response)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog='ledgora', description='Ledgora CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    login_parser = subparsers.add_parser('login', help='Authenticate with an API key')
    login_parser.add_argument('--api-key', dest='api_key')
    login_parser.add_argument('--api-key-stdin', action='store_true', help='Read the API key from stdin')
    login_parser.add_argument('--org')
    login_parser.add_argument('--host', default=DEFAULT_HOST)
    login_parser.add_argument('--profile', default='default')
    login_parser.set_defaults(handler=command_login)

    logout_parser = subparsers.add_parser('logout', help='Remove the local session for a profile')
    logout_parser.add_argument('--profile')
    logout_parser.set_defaults(handler=command_logout)

    use_parser = subparsers.add_parser('use', help='Switch the active profile')
    use_parser.add_argument('profile')
    use_parser.set_defaults(handler=command_use)

    whoami_parser = subparsers.add_parser('whoami', help='Validate the current session and print the user identity')
    whoami_parser.add_argument('--profile')
    whoami_parser.set_defaults(handler=command_whoami)

    profiles_parser = subparsers.add_parser('profiles', help='List saved profiles')
    profiles_parser.set_defaults(handler=command_profiles)

    organizations_parser = subparsers.add_parser('organizations', help='Work with organization-scoped resources')
    organizations_subparsers = organizations_parser.add_subparsers(dest='organizations_command', required=True)
    organizations_list_parser = organizations_subparsers.add_parser('list', help='List accessible organizations')
    organizations_list_parser.add_argument('--profile')
    organizations_list_parser.set_defaults(handler=command_organizations_list)

    accounts_parser = subparsers.add_parser('accounts', help='Work with the chart of accounts')
    accounts_subparsers = accounts_parser.add_subparsers(dest='accounts_command', required=True)
    accounts_list_parser = accounts_subparsers.add_parser('list', help='List ledger accounts')
    accounts_list_parser.add_argument('--profile')
    accounts_list_parser.set_defaults(handler=command_accounts_list)

    customers_parser = subparsers.add_parser('customers', help='Work with customers')
    customers_subparsers = customers_parser.add_subparsers(dest='customers_command', required=True)
    customers_list_parser = customers_subparsers.add_parser('list', help='List customers')
    customers_list_parser.add_argument('--profile')
    customers_list_parser.set_defaults(handler=command_customers_list)

    vendors_parser = subparsers.add_parser('vendors', help='Work with vendors')
    vendors_subparsers = vendors_parser.add_subparsers(dest='vendors_command', required=True)
    vendors_list_parser = vendors_subparsers.add_parser('list', help='List vendors')
    vendors_list_parser.add_argument('--profile')
    vendors_list_parser.set_defaults(handler=command_vendors_list)

    reports_parser = subparsers.add_parser('reports', help='Run financial reports')
    reports_subparsers = reports_parser.add_subparsers(dest='reports_command', required=True)

    trial_balance_parser = reports_subparsers.add_parser('trial-balance', help='Fetch the trial balance report')
    trial_balance_parser.add_argument('--profile')
    trial_balance_parser.add_argument('--as-of-date')
    trial_balance_parser.add_argument('--currency')
    trial_balance_parser.set_defaults(handler=command_report_trial_balance)

    profit_and_loss_parser = reports_subparsers.add_parser('profit-and-loss', help='Fetch the profit and loss report')
    profit_and_loss_parser.add_argument('--profile')
    profit_and_loss_parser.add_argument('--from-date')
    profit_and_loss_parser.add_argument('--to-date')
    profit_and_loss_parser.add_argument('--currency')
    profit_and_loss_parser.set_defaults(handler=command_report_profit_and_loss)

    balance_sheet_parser = reports_subparsers.add_parser('balance-sheet', help='Fetch the balance sheet report')
    balance_sheet_parser.add_argument('--profile')
    balance_sheet_parser.add_argument('--as-of-date')
    balance_sheet_parser.add_argument('--currency')
    balance_sheet_parser.set_defaults(handler=command_report_balance_sheet)

    cash_flow_parser = reports_subparsers.add_parser('cash-flow', help='Fetch the cash flow report')
    cash_flow_parser.add_argument('--profile')
    cash_flow_parser.add_argument('--from-date')
    cash_flow_parser.add_argument('--to-date')
    cash_flow_parser.add_argument('--currency')
    cash_flow_parser.set_defaults(handler=command_report_cash_flow)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CLIError as exc:
        print(format_cli_error(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())