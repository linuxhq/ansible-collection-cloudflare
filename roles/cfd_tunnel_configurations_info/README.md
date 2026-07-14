# cfd\_tunnel\_configurations\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare cfd tunnel configurations

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_configurations_info_account_id: null
    cfd_tunnel_configurations_info_api_token: null

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
          cfd_tunnel_configurations_info_account_id: '{{ _accounts_info_id }}'
          cfd_tunnel_configurations_info_api_token: '{{ accounts_info_api_token }}'
