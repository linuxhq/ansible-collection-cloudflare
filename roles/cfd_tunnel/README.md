# cfd\_tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnels

## Requirements

| Type    | Permission        | Value |
| ------- | ----------------- | ----- |
| Account | Account Settings  | Read  |
| Account | Cloudflare Tunnel | Write |

## Role Variables

    cfd_tunnel_account_id: null
    cfd_tunnel_api_token: null
    cfd_tunnel_async: 300
    cfd_tunnel_batch: 10
    cfd_tunnel_delay: 3
    cfd_tunnel_list: []
    cfd_tunnel_poll: 0
    cfd_tunnel_retries: 100

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
