# warp\_connector\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare warp connectors

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare One Connector: WARP`

## Role Variables

    warp_connector_info_account_id: null
    warp_connector_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _warp_connector_info_dict
    _warp_connector_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.warp_connector_info
