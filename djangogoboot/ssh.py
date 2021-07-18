import paramiko

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

KEYTYPES = {
    'ed25519': paramiko.ed25519key.Ed25519Key,
    'rsa': paramiko.rsakey.RSAKey,
    'ecdsa': paramiko.ecdsakey.ECDSAKey,
    'dsa': paramiko.dsskey.DSSKey,
}


def verify_ssh_inputs(
    host, user, key_filename,
    jump_host=None, jump_user=None, known_hosts_filename=None,
    port=22, jump_port=22
):

    # check private key
    try:
        with open(key_filename) as key_file:
            pkey, keytype = get_pkey_from_file(key_file)
        if keytype is None:
            return False, ["Invalid SSH Key format"]
    except FileNotFoundError:
        return False, ["Could not find SSH Key file"]

    # check known_hosts
    if known_hosts_filename is not None:
        try:
            open(known_hosts_filename)
        except FileNotFoundError:
            return False, ["Specified known hosts file not found"]

    client = paramiko.client.SSHClient()
    if known_hosts_filename is not None:
        host_policy = paramiko.client.RejectPolicy
        client.load_host_keys(known_hosts_filename)
    elif jump_host is None:
        host_policy = paramiko.client.AutoAddPolicy
    else:
        return False, ["Known hosts file required for jump host configuration"]
    client.set_missing_host_key_policy(host_policy)

    if jump_host is None:
        try:
            client.connect(
                hostname=host,
                username=user,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
            )
        except paramiko.ssh_exception.AuthenticationException:
            return False, ["SSH connection failed"]
        finally:
            client.close()
    else:
        jump_client = paramiko.client.SSHClient()
        jump_client.load_host_keys(known_hosts_filename)
        jump_client.set_missing_host_key_policy(host_policy)
        try:
            jump_client.connect(
                hostname=jump_host,
                username=jump_user or user,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
            )
        except paramiko.ssh_exception.AuthenticationException:
            return False, ["SSH connection to jump host failed"]

        jump_transport = jump_client.get_transport()
        jump_channel = jump_transport.open_channel(
            'direct-tcpip',
            (host, port),
            ('', 0)
        )
        try:
            client.connect(
                hostname=host,
                username=user,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
                sock=jump_channel,
            )
        except paramiko.ssh_exception.AuthenticationException:
            return False, ["SSH connection to jump success, but to host failed"]
        finally:
            client.close()
            jump_client.close()
    return True, []


def get_host_key(hostname):
    transport = paramiko.transport.Transport(hostname)
    transport.start_client()
    key = transport.get_remote_server_key()
    keyname = key.get_name()
    keyval = key.get_base64()
    return f"{hostname} {keyname} {keyval}"


def get_pkey_from_file(key_file):
    for keytype, keyclass in KEYTYPES.items():
        try:
            pkey = keyclass.from_private_key(key_file)
        except paramiko.ssh_exception.SSHException:
            continue
        return pkey, keytype
    return None, None


def generate_rsa_keypair():
    # SSH key generation code taken from Stack Overflow
    # https://stackoverflow.com/a/39126754/65326

    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=4096
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption()
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    return private_key.decode('utf-8'), public_key.decode('utf-8')
