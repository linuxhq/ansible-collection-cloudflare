# devices\_policy\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare devices policy

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zero Trust`

## Role Variables

    devices_policy_info_account_id: null
    devices_policy_info_api_token: null

## Return Values

    _devices_policy_info_dict

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.devices_policy_info
