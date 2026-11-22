# access\_policies

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access policies

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/policies/).

## Requirements

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Apps and Policies                             | Write |
| Account | Access: Organizations, Identity Providers, and Groups | Read  |
| Account | Account Settings                                      | Read  |

## Role Variables

| Variable                     | Default | Description                                        |
| ---------------------------- | ------- | -------------------------------------------------- |
| `access_policies_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `access_policies_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `access_policies_async`      | `300`   | Seconds each async job may run                     |
| `access_policies_batch`      | `10`    | Items submitted per batch                          |
| `access_policies_delay`      | `3`     | Seconds between job status checks                  |
| `access_policies_list`       | `[]`    | Access policies to manage                          |
| `access_policies_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `access_policies_retries`    | `100`   | Job status checks before failing                   |

## Dependencies

* [access\_groups\_info](../access_groups_info)
* [access\_identity\_providers\_info](../access_identity_providers_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_policies
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_groups_info_account_id: '{{ _accounts_info_id }}'
          access_groups_info_api_token: '{{ accounts_info_api_token }}'
          access_identity_providers_info_account_id: '{{ _accounts_info_id }}'
          access_identity_providers_info_api_token: '{{ accounts_info_api_token }}'
          access_policies_account_id: '{{ _accounts_info_id }}'
          access_policies_api_token: '{{ accounts_info_api_token }}'
          access_policies_list:
            - name: molecule-00-email
              decision: allow
              include:
                - email:
                    email: email@molecule.org
              require:
                - login_method:
                    id: "{{ _access_identity_providers_info_dict['onetimepin'].id }}"
            - name: molecule-00-group
              decision: non_identity
              include:
                - group:
                    id: "{{ _access_groups_info_dict['molecule-00'].id }}"
