# linuxhq.cloudflare

![License](https://img.shields.io/badge/license-GPLv3-lightgreen)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.cloudflare-blue)](https://galaxy.ansible.com/linuxhq/cloudflare)
[![Lint](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/pre-commit.yml)
[![Release](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml)

A collection of cloudflare roles

# Collection

## Build

    ansible-galaxy collection build

## Install

    ansible-galaxy collection install linuxhq.cloudflare

## Requirements

* Python `>= 3.11`
* `ansible-core >= 2.18.0`
* `community.general >= 12.0.0, < 14.0.0`
* `cloudflare >= 4.3.1, < 5`

# Examples

Example playbooks and inventory can be found [here](examples/)

# Tokens

The use of these roles will require an api token which can be generated using the link below

* https://dash.cloudflare.com/profile/api-tokens

## Permissions

If you plan to utilize all the roles in this collection you'll need the following permissions

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
