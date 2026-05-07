import json
import os
import platform
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

try:
    import keyring
except ImportError:  # pragma: no cover
    keyring = None

from .errors import CLIError


SERVICE_NAME = 'Ledgora CLI'
CONFIG_FILENAME = 'config.json'


def config_dir():
    override = os.getenv('LEDGORA_CLI_CONFIG_DIR')
    if override:
        return Path(override).expanduser()

    system_name = platform.system()
    if system_name == 'Darwin':
        return Path.home() / 'Library' / 'Application Support' / 'ledgora'
    if system_name == 'Windows':
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / 'ledgora'
        return Path.home() / 'AppData' / 'Roaming' / 'ledgora'
    return Path.home() / '.config' / 'ledgora'


def config_path():
    return config_dir() / CONFIG_FILENAME


def _default_config():
    return {
        'version': 1,
        'current_profile': None,
        'profiles': {},
    }


def _ensure_private_directory(path):
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _write_private_file(path, content):
    _ensure_private_directory(path.parent)
    path.write_text(content)
    os.chmod(path, 0o600)


def load_config():
    path = config_path()
    if not path.exists():
        return _default_config()
    data = json.loads(path.read_text())
    return {
        'version': data.get('version', 1),
        'current_profile': data.get('current_profile'),
        'profiles': data.get('profiles', {}),
    }


def save_config(config):
    _write_private_file(config_path(), json.dumps(config, indent=2, sort_keys=True))


def _keyring_disabled():
    return os.getenv('LEDGORA_CLI_DISABLE_KEYRING') == '1'


def _keyring_entry_name(profile_name):
    return f'profile:{profile_name}:fernet-key'


def _local_key_path(profile_name):
    return config_dir() / f'.{profile_name}.key'


def _read_key_from_keyring(profile_name):
    if _keyring_disabled() or keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, _keyring_entry_name(profile_name))
    except Exception:  # pragma: no cover
        return None


def _write_key_to_keyring(profile_name, raw_key):
    if _keyring_disabled() or keyring is None:
        return False
    try:
        keyring.set_password(SERVICE_NAME, _keyring_entry_name(profile_name), raw_key)
        return True
    except Exception:  # pragma: no cover
        return False


def _delete_key_from_keyring(profile_name):
    if _keyring_disabled() or keyring is None:
        return
    try:
        keyring.delete_password(SERVICE_NAME, _keyring_entry_name(profile_name))
    except Exception:  # pragma: no cover
        return


def _load_or_create_fernet(profile_name):
    existing_key = _read_key_from_keyring(profile_name)
    if existing_key:
        return Fernet(existing_key.encode()), 'keyring'

    local_key_path = _local_key_path(profile_name)
    if local_key_path.exists():
        return Fernet(local_key_path.read_text().strip().encode()), 'local_keyfile'

    generated_key = Fernet.generate_key().decode()
    if _write_key_to_keyring(profile_name, generated_key):
        return Fernet(generated_key.encode()), 'keyring'

    _write_private_file(local_key_path, generated_key)
    return Fernet(generated_key.encode()), 'local_keyfile'


def encrypt_secret(profile_name, plaintext):
    fernet, backend = _load_or_create_fernet(profile_name)
    ciphertext = fernet.encrypt((plaintext or '').encode()).decode()
    return ciphertext, backend


def decrypt_secret(profile_name, ciphertext):
    fernet, _ = _load_or_create_fernet(profile_name)
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CLIError('Stored credentials could not be decrypted.', 'STORAGE_ERROR') from exc


def resolve_profile_name(config, explicit_profile=None):
    return explicit_profile or config.get('current_profile') or 'default'


def get_profile(profile_name=None):
    config = load_config()
    resolved_name = resolve_profile_name(config, profile_name)
    stored = config['profiles'].get(resolved_name)
    if stored is None:
        raise CLIError(f'Profile {resolved_name} was not found.', 'PROFILE_NOT_FOUND')

    return {
        'profile': resolved_name,
        'host': stored['host'],
        'organization_id': stored['organization_id'],
        'organization_name': stored.get('organization_name'),
        'expires_at': stored.get('expires_at'),
        'user': stored.get('user') or {},
        'key_backend': stored.get('key_backend'),
        'access_token': decrypt_secret(resolved_name, stored['access_token_ciphertext']),
        'api_key': decrypt_secret(resolved_name, stored['api_key_ciphertext']),
    }


def upsert_profile(profile_name, session, *, make_current=True):
    config = load_config()
    access_token_ciphertext, key_backend = encrypt_secret(profile_name, session['access_token'])
    api_key_ciphertext, _ = encrypt_secret(profile_name, session['api_key'])
    config['profiles'][profile_name] = {
        'host': session['host'],
        'organization_id': session['organization_id'],
        'organization_name': session.get('organization_name'),
        'expires_at': session.get('expires_at'),
        'user': session.get('user') or {},
        'key_backend': key_backend,
        'access_token_ciphertext': access_token_ciphertext,
        'api_key_ciphertext': api_key_ciphertext,
    }
    if make_current:
        config['current_profile'] = profile_name
    save_config(config)


def set_current_profile(profile_name):
    config = load_config()
    if profile_name not in config['profiles']:
        raise CLIError(f'Profile {profile_name} was not found.', 'PROFILE_NOT_FOUND')
    config['current_profile'] = profile_name
    save_config(config)


def list_profiles():
    config = load_config()
    current = config.get('current_profile')
    return [
        {
            'name': name,
            'is_current': name == current,
            'organization_id': profile.get('organization_id'),
            'host': profile.get('host'),
        }
        for name, profile in sorted(config['profiles'].items())
    ]


def remove_profile(profile_name=None):
    config = load_config()
    resolved_name = resolve_profile_name(config, profile_name)
    if resolved_name not in config['profiles']:
        raise CLIError(f'Profile {resolved_name} was not found.', 'PROFILE_NOT_FOUND')

    del config['profiles'][resolved_name]
    _delete_key_from_keyring(resolved_name)
    local_key_path = _local_key_path(resolved_name)
    if local_key_path.exists():
        local_key_path.unlink()

    if config.get('current_profile') == resolved_name:
        remaining = sorted(config['profiles'])
        config['current_profile'] = remaining[0] if remaining else None

    if config['profiles']:
        save_config(config)
    else:
        path = config_path()
        if path.exists():
            path.unlink()