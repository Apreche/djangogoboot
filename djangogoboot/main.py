#!/usr/bin/env python

import argparse
import os
import sys

from prompt_toolkit import prompt, shortcuts

from . import repo
from . import ssh


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'project_name', nargs='?', type=str, default=None,
        help="The name for this Django project."
    )
    parser.add_argument(
        '-A', '--author', type=str, default=None,
        help="The name of the author of this project"
    )
    parser.add_argument(
        '-E', '--email', type=str, default=None,
        help="The email address of the admin of this project.",
    )
    parser.add_argument(
        '-D', '--domain', type=str, default=None,
        help="The domain name of this site.",
    )
    parser.add_argument(
        '-H', '--host', type=str, default=None,
        help="The SSH hostname of the deployment target."
    )
    parser.add_argument(
        '-U', '--user', type=str, default=None,
        help="The SSH username for connecting to the deployment target."
    )
    parser.add_argument(
        '-P', '--port', type=int, default=None,
        help="SSH port"
    )
    parser.add_argument(
        '-K', '--key-file', type=str, default=None,
        help="Path to SSH private key file for deployment."
    )
    parser.add_argument(
        '-N', '--known-hosts-file', type=str, default=None,
        help="Path to a known_hosts file to use for host verification. "
        "Required for jump host."
    )
    parser.add_argument(
        '-J', '--jump-host', type=str, default=None,
        help="Hostname of the SSH jump/bastion host"
    )
    parser.add_argument(
        '--jump-user', type=str, default=None,
        help="Username for jump host if different from user for primary host."
    )
    parser.add_argument(
        '--jump-port', type=int, default=None,
        help="SSH port for jump host"
    )
    parser.add_argument(
        '-q', '--quiet', action="store_true"
    )
    return parser.parse_args()


def prompt_user():
    args = parse_arguments()
    user_inputs = {}
    user_inputs['quiet'] = args.quiet
    user_inputs['project_name'] = args.project_name or prompt("New project name: ")
    user_inputs['domain_name'] = args.domain or prompt(
        "What is the domain name of this site?: "
    )
    user_inputs['author'] = args.author or prompt(
        "What is the name of the author of this project?: "
    )
    user_inputs['email'] = args.email or prompt(
        "What is the email address of this sites administrator?: "
    )

    github_access_token = os.environ.get(
        'GH_TOKEN',
        os.environ.get('GITHUB_TOKEN', None)
    )
    if github_access_token is None:
        github_access_token = prompt("Github access token: ", is_password=True)
    user_inputs['github_access_token'] = github_access_token

    user_inputs['ssh_host'] = args.host or prompt(
        "What is the SSH hostname of the deployment target?: "
    )
    user_inputs['ssh_user'] = args.user or prompt(
        "What is the SSH username to use when deploying?: "
    )
    user_inputs['ssh_port'] = args.port or prompt(
        "Port for SSH connection: ", default='22'
    )
    user_inputs['ssh_key_file'] = args.key_file or prompt(
        "Path to SSH Private Key for deploying: "
    )

    if not args.jump_host:
        use_jump = shortcuts.confirm("Use SSH jump host?")
        if use_jump:
            user_inputs['jump_host'] = prompt("Jump host: ")
            user_inputs['jump_user'] = prompt(
                "Jump host username: ", default=user_inputs['ssh_user']
            )
            user_inputs['jump_port'] = args.jump_port or prompt(
                "SSH port on jump host: ", default='22'
            )
    else:
        use_jump = True
        user_inputs['jump_host'] = args.jump_host
        jump_user = getattr(args, 'jump_user', None)
        if jump_user:
            user_inputs['jump_user'] = jump_user

    known_hosts = getattr(args, 'known_hosts_file', None)
    if use_jump and (not known_hosts):
        known_hosts = prompt(
            "Path to known_hosts files: "
        )
    user_inputs['known_hosts_file'] = known_hosts

    return user_inputs


def validate_inputs(user_inputs):
    valid = True
    messages = []

    # Check basic field requirements
    required_fields = [
        'project_name',
        'github_access_token',
        'ssh_host',
        'ssh_user',
        'ssh_key_file',
    ]
    for field in required_fields:
        value = user_inputs.get(field, None)
        if not value:
            valid = False
            messages.append("{field} required, but not provided")

    # Verify Github token is working
    if not repo.verify_github_token(user_inputs.get('github_access_token', None)):
        valid = False
        messages.append("Invalid Github access token")

    # Verify SSH connection is working
    ssh_valid, ssh_messages = ssh.verify_ssh_inputs(
        user_inputs.get('ssh_host', None),
        user_inputs.get('ssh_user', None),
        user_inputs.get('ssh_key_file', None),
        jump_host=user_inputs.get('jump_host', None),
        jump_user=user_inputs.get('jump_user', None),
        known_hosts_filename=user_inputs.get('known_hosts_file', None),
    )
    valid = valid and ssh_valid
    messages += ssh_messages

    return (valid, messages)


def main():

    user_inputs = prompt_user()
    inputs_are_valid, messages = validate_inputs(user_inputs)

    if not inputs_are_valid:
        print("\n".join(messages), file=sys.stderr)
        sys.exit("Invalid Inputs")

    repo.launch_project(**user_inputs)


if __name__ == "__main__":
    main()
