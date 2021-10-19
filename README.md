# Djangogoboot

Djangogoboot is a CLI utility written in Python used to *fully* bootstrap brand new Django projects. It assumes an architecture where the entire stack is hosted on a single instance. Starting from a clean template it will setup a GitHub repository with GitHub actions to handle linting, testing, and production deployment. Any releases are created in that GitHub repository will set off automated deployments to the production instance.

# Installation

Djangogoboot is a standard python app ditributed on pypy. I recommend installing it via pip.

`$ pip install djangogoboot`

# Basic Usage

Once installed, djangogoboot can be invoked with the simple command.

`$ djangogoboot`

The program will prompt for all the information it requires. To avoid prompts, it is possible to pass it all the required information as parameters on the command line. For more information check, the help.

`$ djangogoboot --help`

If Djangogoboot succeeds, a GitHub repository will be created with the project inside. Developers should be able to clone that repository and develop locally. Any pull request made to the repository will be checked by two GitHub actions. One will lint the codebase and the other will run the Django test suite. If any releases are created on that repository, that will result in an automated deployment to the production instance.

## Prerequisites

Before using djangogoboot, the following things must already be setup in advance. Djangogoboot does as much as it can, but there is only so much that is possible. Before actually doing anything, Djangogoboot does its best to verify that it has all necessary information and that all the values are correct. This is to avoid failures that leave artifacts behind for the user to cleanup by hand.

* Before using Djangogoboot, create a [GitHub personal access token](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token) that has full control of private repositories.
	* Djangogoboot will check the environment variable named `GH_TOKEN`. If the variable is not present, it will prompt the user for the token. It may not be passed as a CLI parameter.
	* The user that this token belongs to will be the account under which the new project will be created.

* Before using Djangogoboot, the production instance on which the Django project will be hosted must already exist.
	* The instance should be running Ubuntu 20.04 LTS. Other Ubuntu versions or Debian-based Linux distros may work, but are not (yet) officially supported.
	* There must be a user on the instance that has sudo privileges. This user will be the one that executes the automated deployments.
	* SSH server must be running on the instance.
	* There must be an SSH keypair that is *not* encrypted with a passphrase that can be used to connect to the instance as the user with sudo privileges. 
	* If using a jump host...
		* It must be possible to connect to the production instance from the jump host via SSH.
		* If the same keypair can not be used to login to both the jump host and the target host, a username and keypair for each must be provided for both.
		* A pre-existing known_hosts file must be provided to verify both the jump host and production instance.
	* The GitHub action runners must be able to reach the instance over the network via SSH, either directly or via a [ProxyJump](https://man.openbsd.org/ssh_config.5#ProxyJump). This usually means it has a public IP address.
	* There must be a public DNS record pointing at the instance. This is likely to be the domain of your new django project web site.

# Philosophy

Django provides an excellent tutorial for learning Django. When you look at the Django community online, there are actually not many people struggling with Django directly. Most often people are having a hard time because they learned web development, but not Linux systems administration. Django, rightfully, does nothing to help people learn things like setting up gunicorn/nginx, as that is outside their domain. However, that doesn't change the fact that people are left struggling to deploy their projects.

At the same time, even very experienced developers who are highly skilled and knowledgeable at all parts of the stack, often find it a hassle to repeat the same configuration tasks every time they want to start a new project. How nice would it be to type literally one command, and have a live production server with automatic testing and deployments already setup. 

There are many popular SaaS products or container-based solutions out there trying to solve this problem in their own way. They have their place in the world. But in the opinion of this project, those are overengineered and/or overpriced for the vast majority of projects will will start and remain very small for their entire existence.

For the vast majority of projects, the entire stack can be hosted on a single server instance. Premature optimization and scaling are to be avoided. If a project does indeed find itself needing to scale beyond a single instance, the team behind it should have no problem finding the resources to evolve its architecture. Even so, the single instance full stack is a fine place for almost all projects to start.

# Design

## GitHub Actions

The Djangogoboot application and its template simply create a GitHub repository with GitHub actions configured. After that, their job is done and the GitHub actions take care of everything else.

* The testing action, simply executes the default Django test framework.
* The linting action is powered by [GitHub super-linter](https://github.com/github/super-linter). The 
* The deployment action uses [Ansible](https://www.ansible.com/) to execute the deployment. It simply executes the `deploy.yml` playbook in the `.ansible` directory of the resulting project. Any secret information requires is stored in the respotory's [GitHub secrets](https://docs.github.com/en/actions/reference/encrypted-secrets).

## The Instance

The production instance that is deployed by Djangogoboot includes the following (mostly) complete web stack. Services that are not automatically managed by the OS are managed via [systemd](https://www.freedesktop.org/wiki/Software/systemd/).

* [Ubuntu 20.04](https://ubuntu.com)
* [PostgreSQL](https://www.postgresql.org)
* [Gunicorn](https://gunicorn.org)
* [RabbitMQ](https://www.rabbitmq.com)
* [Celery](https://docs.celeryproject.org)
* [NGINX](https://www.nginx.com)
* [Let's Encrypt](https://letsencrypt.org)/[certbot](https://certbot.eff.org)
* [memcached](https://memcached.org)
* [Postfix](http://www.postfix.org) (local e-mail only)

# Known Limitations

There are many obvious improvements and additions that can be made to Djangogoboot and its template. It is somewhat likely that they already exist in the GitHub issue tracker, soplease check there. New suggestions always welcome.

# Pull Requests

There are two repositories for Djangogoboot. This one is merely a CLI application that is used to launch new projects from the template. The template itself is in a separate repository. The template repository actually contains the GitHub actions and ansible playbooks that constitute most of the functionality. Make sure to submit PRs to the appropriate repository.
