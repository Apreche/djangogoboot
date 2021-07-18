import secrets
import string
import subprocess


def generate_secure_password(length=24):
    # https://docs.python.org/3/library/secrets.html#recipes-and-best-practices
    alphabet = string.ascii_letters + string.digits
    return ''.join(
        secrets.choice(alphabet) for i in range(length)
    )


def vault_encrypt_string(password_filename, key, value):
    result = subprocess.run(
        [
            'ansible-vault',
            'encrypt_string',
            value,
            '--name',
            key,
            '--vault-password-file',
            password_filename
        ],
        capture_output=True
    )
    return result.stdout.decode('utf-8')
