# warp\_connector

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare warp connectors

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/warp_connector/).

## Requirements

| Type    | Permission                     | Value |
| ------- | ------------------------------ | ----- |
| Account | Account Settings               | Read  |
| Account | Cloudflare One Connector: WARP | Write |

## Role Variables

| Variable                    | Default | Description                                        |
| --------------------------- | ------- | -------------------------------------------------- |
| `warp_connector_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `warp_connector_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `warp_connector_async`      | `300`   | Seconds each async job may run                     |
| `warp_connector_batch`      | `10`    | Items submitted per batch                          |
| `warp_connector_delay`      | `3`     | Seconds between job status checks                  |
| `warp_connector_list`       | `[]`    | WARP connectors to manage                          |
| `warp_connector_no_log`     | `false` | Hide task output from logs                         |
| `warp_connector_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `warp_connector_retries`    | `100`   | Job status checks before failing                   |

Set `warp_connector_no_log: true` to keep the connector tokens and tunnel credentials that results include out of task output.

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.warp_connector
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          warp_connector_account_id: '{{ _accounts_info_id }}'
          warp_connector_api_token: '{{ accounts_info_api_token }}'
          warp_connector_list:
            - name: molecule-00
            - name: molecule-01
            - name: molecule-02
            - name: molecule-03
            - name: molecule-04
