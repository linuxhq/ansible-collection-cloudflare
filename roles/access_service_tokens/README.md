# access\_service\_tokens

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access service tokens

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/service_tokens/).

## Requirements

| Type    | Permission             | Value |
| ------- | ---------------------- | ----- |
| Account | Access: Service Tokens | Write |
| Account | Account Settings       | Read  |

## Role Variables

| Variable                           | Default | Description                                        |
| ---------------------------------- | ------- | -------------------------------------------------- |
| `access_service_tokens_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `access_service_tokens_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `access_service_tokens_async`      | `300`   | Seconds each async job may run                     |
| `access_service_tokens_batch`      | `10`    | Items submitted per batch                          |
| `access_service_tokens_delay`      | `3`     | Seconds between job status checks                  |
| `access_service_tokens_display`    | `true`  | Print the service token from every result          |
| `access_service_tokens_list`       | `[]`    | Access service tokens to manage                    |
| `access_service_tokens_no_log`     | `false` | Hide task output from logs                         |
| `access_service_tokens_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `access_service_tokens_retries`    | `100`   | Job status checks before failing                   |

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_service_tokens
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_service_tokens_account_id: '{{ _accounts_info_id }}'
          access_service_tokens_api_token: '{{ accounts_info_api_token }}'
          access_service_tokens_list:
            - name: molecule-00
              duration: forever
            - name: molecule-01
              duration: forever
            - name: molecule-02
              duration: forever
            - name: molecule-03
              duration: forever
            - name: molecule-04
              duration: forever
            - name: molecule-05
              duration: forever
            - name: molecule-06
              duration: forever
            - name: molecule-07
              duration: forever
            - name: molecule-08
              duration: forever
            - name: molecule-09
              duration: forever
            - name: molecule-10
              duration: forever
            - name: molecule-11
              duration: forever
