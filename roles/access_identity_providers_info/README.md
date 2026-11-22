# access\_identity\_providers\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access identity providers

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/identity_providers/).

## Requirements

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Organizations, Identity Providers, and Groups | Read  |
| Account | Account Settings                                      | Read  |

## Role Variables

| Variable                                    | Default | Description                                |
| ------------------------------------------- | ------- | ------------------------------------------ |
| `access_identity_providers_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `access_identity_providers_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |
| `access_identity_providers_info_no_log`     | `false` | Hide task output from logs                 |

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_identity_providers_info_dict
    _access_identity_providers_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_identity_providers_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_identity_providers_info_account_id: '{{ _accounts_info_id }}'
          access_identity_providers_info_api_token: '{{ accounts_info_api_token }}'
