# cfd\_tunnel\_configurations\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare cfd tunnel configurations

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/configurations/).

## Requirements

| Type    | Permission        | Value |
| ------- | ----------------- | ----- |
| Account | Account Settings  | Read  |
| Account | Cloudflare Tunnel | Read  |

## Role Variables

| Variable                                    | Default | Description                                |
| ------------------------------------------- | ------- | ------------------------------------------ |
| `cfd_tunnel_configurations_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `cfd_tunnel_configurations_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _cfd_tunnel_configurations_info_dict
    _cfd_tunnel_configurations_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel_configurations_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          cfd_tunnel_configurations_info_account_id: '{{ _accounts_info_id }}'
          cfd_tunnel_configurations_info_api_token: '{{ accounts_info_api_token }}'
