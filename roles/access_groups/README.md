# access\_groups

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access groups

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/groups/).

## Requirements

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Organizations, Identity Providers, and Groups | Write |
| Account | Access: Service Tokens                                | Read  |
| Account | Account Settings                                      | Read  |

## Role Variables

| Variable                   | Default | Description                                        |
| -------------------------- | ------- | -------------------------------------------------- |
| `access_groups_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `access_groups_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `access_groups_async`      | `300`   | Seconds each async job may run                     |
| `access_groups_batch`      | `10`    | Items submitted per batch                          |
| `access_groups_delay`      | `3`     | Seconds between job status checks                  |
| `access_groups_list`       | `[]`    | Access groups to manage                            |
| `access_groups_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `access_groups_retries`    | `100`   | Job status checks before failing                   |

## Dependencies

* [access\_service\_tokens\_info](../access_service_tokens_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_groups
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_service_tokens_info_account_id: '{{ _accounts_info_id }}'
          access_service_tokens_info_api_token: '{{ accounts_info_api_token }}'
          access_groups_account_id: '{{ _accounts_info_id }}'
          access_groups_api_token: '{{ accounts_info_api_token }}'
          access_groups_list:
            - name: molecule-00
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-00'].id }}"
              is_default: false
            - name: molecule-01
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-01'].id }}"
              is_default: false
            - name: molecule-02
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-02'].id }}"
              is_default: false
