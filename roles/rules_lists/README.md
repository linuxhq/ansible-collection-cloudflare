# rules\_lists

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare rules lists

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/rules/subresources/lists/).

## Requirements

| Type    | Permission           | Value |
| ------- | -------------------- | ----- |
| Account | Account Filter Lists | Edit  |
| Account | Account Settings     | Read  |

## Role Variables

| Variable                 | Default | Description                                        |
| ------------------------ | ------- | -------------------------------------------------- |
| `rules_lists_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `rules_lists_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `rules_lists_async`      | `300`   | Seconds each async job may run                     |
| `rules_lists_batch`      | `10`    | Items submitted per batch                          |
| `rules_lists_delay`      | `3`     | Seconds between job status checks                  |
| `rules_lists_list`       | `[]`    | Rules lists to manage                              |
| `rules_lists_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `rules_lists_retries`    | `100`   | Job status checks before failing                   |

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rules_lists
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          rules_lists_account_id: '{{ _accounts_info_id }}'
          rules_lists_api_token: '{{ accounts_info_api_token }}'
          rules_lists_list:
            - kind: ip
              name: uptime_robot
              elements:
                "{{ lookup('ansible.builtin.url',
                           'https://uptimerobot.com/inc/files/ips/IPv4.txt',
                           wantlist=true) |
                    map('community.general.dict_kv',
                        'ip') |
                    sort(attribute='ip') }}"
