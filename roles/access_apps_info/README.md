# access\_apps\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access apps

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Access: Apps and Policies`

## Role Variables

    access_apps_info_account_id: null
    access_apps_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_apps_info_dict
    _access_apps_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.access_apps_info
