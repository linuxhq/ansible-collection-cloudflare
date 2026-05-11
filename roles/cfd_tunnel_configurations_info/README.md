# cfd\_tunnel\_configurations\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information cloudflare cfd tunnel configurations

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_configurations_info_account_id: null
    cfd_tunnel_configurations_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.cfd_tunnel_configurations_info
