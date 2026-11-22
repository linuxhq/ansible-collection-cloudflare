# cfd\_tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnels

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/).

## Requirements

| Type    | Permission        | Value |
| ------- | ----------------- | ----- |
| Account | Account Settings  | Read  |
| Account | Cloudflare Tunnel | Write |

## Role Variables

| Variable                | Default | Description                                        |
| ----------------------- | ------- | -------------------------------------------------- |
| `cfd_tunnel_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `cfd_tunnel_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `cfd_tunnel_async`      | `300`   | Seconds each async job may run                     |
| `cfd_tunnel_batch`      | `10`    | Items submitted per batch                          |
| `cfd_tunnel_delay`      | `3`     | Seconds between job status checks                  |
| `cfd_tunnel_list`       | `[]`    | Cloudflared tunnels to manage                      |
| `cfd_tunnel_no_log`     | `false` | Hide task output from logs                         |
| `cfd_tunnel_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `cfd_tunnel_retries`    | `100`   | Job status checks before failing                   |

Set `cfd_tunnel_no_log: true` to keep the connector tokens and tunnel credentials that results include out of task output.

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          cfd_tunnel_account_id: '{{ _accounts_info_id }}'
          cfd_tunnel_api_token: '{{ accounts_info_api_token }}'
          cfd_tunnel_list:
            - name: molecule-local
              config_src: local
              tunnel_secret: "{{ lookup('env', 'CLOUDFLARE_TUNNEL_SECRET') }}"
            - name: molecule-remote
              config_src: cloudflare
