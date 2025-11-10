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

# Examples

Example playbooks and inventory can be found [here](examples/)

# Tokens

The use of these roles will require an api token which can be generated using the link below

* https://dash.cloudflare.com/profile/api-tokens

## Permissions

If you plan to utilize all the roles in this collection you'll need the following permissions

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Apps and Policies                             | Edit  |
| Account | Access: Organizations, Identity Providers, and Groups | Edit  |
| Account | Access: Service Tokens                                | Edit  |
| Account | Account Filter Lists                                  | Edit  |
| Account | Account Settings                                      | Read  |
| Account | Cloudflare Tunnel                                     | Edit  |
| Account | Cloudflare One Connector: WARP                        | Edit  |
| Account | Zero Trust                                            | Edit  |
| Zone    | Cache Purge                                           | Purge |
| Zone    | DNS                                                   | Edit  |
| Zone    | Page Rules                                            | Edit  |
| Zone    | Zone                                                  | Edit  |
| Zone    | Zone Settings                                         | Edit  |
| Zone    | Zone WAF                                              | Edit  |
