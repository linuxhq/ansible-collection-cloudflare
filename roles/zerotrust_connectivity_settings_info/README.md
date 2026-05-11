# zerotrust\_connectivity\_settings\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zerotrust connectivity settings

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zero Trust`

## Role Variables

    zerotrust_connectivity_settings_info_account_id: null
    zerotrust_connectivity_settings_info_api_token: null

## Return Values

    _zerotrust_connectivity_settings_info_dict

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.zerotrust_connectivity_settings_info
