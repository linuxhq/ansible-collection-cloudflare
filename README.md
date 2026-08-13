# linuxhq.cloudflare

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.cloudflare-blue)](https://galaxy.ansible.com/linuxhq/cloudflare)
[![Lint](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/pre-commit.yml)
[![Release](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml)

An Ansible collection of Cloudflare modules, plugins, and roles.

## Requirements

- Python `>= 3.11`
- `ansible-core >= 2.18.0`
- `community.general >= 12.0.0, < 14.0.0`
- `cloudflare >= 5.6.0, < 6`

## Installation

    ansible-galaxy collection install linuxhq.cloudflare

## Development

With Tox installed, install the pre-commit hook:

```sh
tox run -e pre-commit
```

Tox manages isolated environments under `.tox/`; no environment activation is required.

### Checks

Run the default checks:

```sh
tox
```

Run grouped checks:

```sh
tox run -m format
tox run -m lint
tox run -m unit
```

Run Ansible sanity tests for a module:

```sh
tox run -e ansible-test -- sanity --python "$(cat .python-version)" plugins/modules/access_apps.py
```

### Molecule

Each role has a Molecule scenario that also serves as an example playbook. Set `MOLECULE_ROLE`
to select a role:

```sh
MOLECULE_ROLE=accounts_info tox run -e molecule -- test -s default
```

Molecule scenarios may create real Cloudflare resources.

### Changelog and build

```sh
tox run -e changelog -- generate
tox run -e build
```

### Plugin audit

Use `$plugins-audit` for an exhaustive review of the `plugins/` tree.

## Examples

Example playbooks and inventory are available in [`examples/`](examples/).

## Tokens

These roles require an API token created from the
[Cloudflare dashboard](https://dash.cloudflare.com/profile/api-tokens).

### Permissions

Using every role in the collection requires the following permissions:

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Apps and Policies                             | Write |
| Account | Access: Organizations, Identity Providers, and Groups | Write |
| Account | Access: Service Tokens                                | Write |
| Account | Account Filter Lists                                  | Edit  |
| Account | Account Settings                                      | Read  |
| Account | Account WAF                                           | Write |
| Account | Cloudflare Pages                                      | Write |
| Account | Cloudflare Tunnel                                     | Write |
| Account | Cloudflare One Connector: WARP                        | Write |
| Account | Zero Trust                                            | Write |
| Zone    | Cache Purge                                           | Purge |
| Zone    | DNS                                                   | Write |
| Zone    | Page Rules                                            | Write |
| Zone    | Zone                                                  | Write |
