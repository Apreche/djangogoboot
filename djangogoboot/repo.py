import git
import github
import jinja2
import shutil

from django.core import management
from django.core.management import utils as django_utils

from . import settings
from . import ssh
from . import utils


def jinja_render_replace(filename, data):
    # https://stackoverflow.com/questions/38642557/how-to-load-jinja-template-directly-from-filesystem
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(filename)
    result = template.render(**data)
    with open(filename, "w") as file:
        file.write(result)


def verify_github_token(token):
    github_api = github.Github(token)
    github_user = github_api.get_user()
    try:
        github_user.name
    except (
        github.GithubException,
        github.BadCredentialsException,
    ):
        return False
    return True


def super_lint_readme_tag(project_name, github_repo):
    # Populate super lint tag in README file
    context = {"full_repo_name": github_repo.full_name}
    jinja_render_replace(f"{project_name}/README.md", context)


# Assumes all parameters are pre-validated
def launch_project(
    project_name=None,
    github_access_token=None,
    quiet=False,
    **kwargs,
):
    create_local_project(project_name, **kwargs)
    github_repo = create_github_repo(github_access_token, project_name)
    super_lint_readme_tag(project_name, github_repo)
    local_repo = init_local_repo(project_name)
    connect_remote_repo(local_repo, github_repo)
    setup_github_deployment_key(github_repo)
    set_github_secrets(github_repo, **kwargs)
    if not quiet:
        print(f"{project_name} successfully created at {github_repo.html_url}")


def create_local_project(project_name, author, email, **kwargs):
    management.call_command(
        'startproject',
        project_name,
        f"--template={settings.TEMPLATE_URL}",
        '--name=pyproject.toml,README.md-tpl,test.yml',
    )
    shutil.move(
        f"{project_name}/README.md-tpl",
        f"{project_name}/README.md",
    )
    shutil.move(f"{project_name}/github", f"{project_name}/.github")
    shutil.move(f"{project_name}/gitignore", f"{project_name}/.gitignore")
    shutil.move(f"{project_name}/ansible", f"{project_name}/.ansible")
    shutil.move(
        f"{project_name}/.ansible/gitignore",
        f"{project_name}/.ansible/.gitignore"
    )
    context = {
        "author_name": author,
        "author_email": email,
    }
    jinja_render_replace(f"{project_name}/pyproject.toml", context)
    load_ansible_vault(project_name)


def load_ansible_vault(project_name):
    vault_password = utils.generate_secure_password()
    vault_password_filename = getattr(
        settings,
        'ANSIBLE_VAULT_PASSWORD_FILENAME',
        'dggb_ansible_vault_password_file'
    )

    vault_filename = f"{project_name}/.ansible/group_vars/all/vault.yml"
    django_secret_key = django_utils.get_random_secret_key()

    with open(vault_password_filename, 'w') as vault_password_file:
        print(vault_password, file=vault_password_file)

    vault_contents = utils.vault_encrypt_string(
        vault_password_filename,
        'vault_secret_key',
        django_secret_key,
    )
    with open(vault_filename, 'w') as vault_file:
        print(vault_contents, file=vault_file)


def init_local_repo(project_name):
    local_repo = git.Repo.init(project_name)
    local_repo.git.add(all=True)
    local_repo.index.commit(
        f"Project {project_name} instantiated via djangogoboot\n"
        "https://github.com/Apreche/djangogoboot"
    )
    return local_repo


def create_github_repo(github_access_token, project_name):
    github_api = github.Github(github_access_token)
    github_user = github_api.get_user()
    return github_user.create_repo(
        name=project_name,
        private=True,
        auto_init=False,
    )


def connect_remote_repo(local_repo, github_repo):
    local_repo.create_remote('origin', github_repo.ssh_url)
    local_branch_name = local_repo.active_branch.name
    remote_branch_name = github_repo.default_branch
    local_repo_remote = local_repo.remotes[0]
    local_repo_remote.push(
        refspec=f"{local_branch_name}:{remote_branch_name}"
    )


def setup_github_deployment_key(github_repo):
    private_key, public_key = ssh.generate_rsa_keypair()
    github_repo.create_key(
        title="Djangogoboot Ansible SSH Deploy Key",
        key=public_key, read_only=True
    )
    github_repo.create_secret(
        'DEPLOY_SSH_PRIVATE_KEY', str(private_key)
    )
    with open('deploy_id_rsa', 'w') as private_deploy_key_file:
        print(private_key, file=private_deploy_key_file)
    with open('deploy_id_rsa.pub', 'w') as public_deploy_key_file:
        print(public_key, file=public_deploy_key_file)


def set_github_secrets(
    github_repo,
    email=None,
    domain_name=None,
    ssh_host=None,
    ssh_user=None,
    ssh_port=22,
    ssh_key_file=None,
    jump_host=None,
    jump_user=None,
    jump_port=22,
    known_hosts_file=None,
    **kwargs
):
    github_repo.create_secret('EMAIL_ADDRESS', str(email))
    github_repo.create_secret('WEB_DOMAIN', str(domain_name))
    github_repo.create_secret('ANSIBLE_SSH_HOST', str(ssh_host))
    github_repo.create_secret('ANSIBLE_SSH_USER', str(ssh_user))
    github_repo.create_secret('ANSIBLE_SSH_PORT', str(ssh_port))

    if jump_host is not None:
        github_repo.create_secret('ANSIBLE_SSH_JUMP_HOST', str(jump_host))
        if jump_user:
            github_repo.create_secret('ANSIBLE_SSH_JUMP_USER', str(jump_user))
        github_repo.create_secret('ANSIBLE_SSH_JUMP_PORT', str(jump_port))

    with open(ssh_key_file) as key_file:
        pkey, keytype = ssh.get_pkey_from_file(key_file)
        github_repo.create_secret('ANSIBLE_SSH_PRIVATE_KEY_TYPE', str(keytype))
        key_file.seek(0)
        github_repo.create_secret('ANSIBLE_SSH_PRIVATE_KEY', str(key_file.read()))

    if known_hosts_file:
        with open(known_hosts_file) as hosts_file:
            known_host_value = hosts_file.read()
    else:
        known_host_value = ssh.get_host_key(ssh_host)
    github_repo.create_secret('ANSIBLE_SSH_KNOWN_HOSTS', str(known_host_value))

    vault_password_filename = getattr(
        settings,
        'ANSIBLE_VAULT_PASSWORD_FILENAME',
        'dggb_ansible_vault_password_file'
    )
    with open(vault_password_filename, 'r') as vault_password_file:
        vault_password = vault_password_file.readline()
    github_repo.create_secret(
        'ANSIBLE_VAULT_PASSWORD',
        str(vault_password.rstrip('\n'))
    )
