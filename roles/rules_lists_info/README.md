# rules\_lists\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare rules lists

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Account Filter Lists`

## Role Variables

    rules_lists_info_account_id: null
    rules_lists_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _rules_lists_info_dict
    _rules_lists_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.rules_lists_info
