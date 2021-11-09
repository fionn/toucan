# Ansible Role to Deploy Canary Tokens

## Introduction

Canary tokens are files that, when used (opened, tested, etc., the exact interaction depends on the type) will trigger an alert.

These can be deployed arbitrarily.

The purpose of this role is to be a prototype for deploying tokens via Ansible. This will allow tight integration between token deployment and infrastructure deployment.

See [`module_utils/`](module_utils) for a description of the core functionality. It also includes a PoC for interacting with the canary token API which can be run as a stand-alone program.

## Installation

Add the below snippet to your Ansible `requirements.yml` file.

```yaml
- name: toucan
  src: "git@github.com:fionn/toucan.git"
  version: "master"
  scm: "git"
```

Then run `ansible-galaxy install -r requirements.yml`.

## Usage

### Creating Tokens

Add the role to your playbook. For example,
```yaml
- name: My playbook
  hosts: all
  roles:
    - role: toucan
      console:
        domain: <console-domain>
        api_token: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          ...
      token:
        memo: "aws-id-{{ inventory_hostname }}"
        kind: aws-id
      dest: "{{ ansible_env.HOME }}/.aws/credentials"
```
could be a playbook that deploys unique AWS tokens to all hosts in the inventory.

See [`example/playbook.yml`](example/playbook.yml) for an example playbook that uses this module.
It can be invoked as standard with e.g. `ansible-playbook playbook.yml --vault-password-file vault_password.txt -i hosts.ini`.

The role requires the following variables:
* `console` dictionary containing:
    * `domain`, the subdomain in `<console_domain>.canary.tools`,
    * `api_token`, token to authenticate to the associated `console.domain`,
* `token` dictionary containing:
    * `memo`, a string to identify the token in the console,
    * `kind`, a string representation of a `CanaryTokenKinds` enumeration (see [the wiki](../../wiki#types-of-tokens) for a list, `WEB_IMAGE` and `S3` tokens are not currently supported),
* `dest`, the destination for the token on the remote host,
* `destroy_only`: see [below](#destroying-tokens).

The role optionally takes the following variables:
* `persistent`, boolean that determines if the token is saved to the backend database or not, defaults to true,
* `fail` will fail the deployment, defaults to false,
* additional `token` dictionary elements:
    * other parameters as required for different token kinds (see [documentation](https://docs.canary.tools/canarytokens/actions.html#create-canarytoken) for "optional parameters"),
    * specifically, `flock_id`, which will be of the form `flock:<base-64-string>` for adding tokens to a specific pre-existing flock,
* `metadata_path`, the location to read and write old `token_id`s to on the remote host, defaults to `$HOME/.toucan_metadata`; Ansible will attempt to remove these tokens from the database.

For detailed documentation on the module, run `ansible-doc -M $HOME/.ansible/roles/toucan/library/ canarytoken.py` (after installation with `ansible-galaxy`).

### Destroying Tokens

The module will always attempt to take `old_token` from the `metadata_path` and destroy it in the console.

The module can be passed `destroy_only: yes` which will:
* not deploy any new tokens;
* fail if there's no `old_token`, so for teardown it is advisable to add `ignore_errors: yes` to this task.

## Caveats and Drawbacks

### Idempotency and Statelessness

By the nature of Ansible and the canarytokens interface, a token will be created regardless of if a token already exists on the remote filesystem.
This may not be an issue, but can result in a proliferation of tokens in the console.
These tokens will not be deleted when the token files themselves are removed, since Ansible doesn't typically handle teardown/destruction.

### Testing

There are currently no tests.
