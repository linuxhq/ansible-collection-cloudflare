# devices\_settings\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare devices settings

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zero Trust`
* Cloudflare api `Token` with `Read` permissions to `Account Settings`

## Role Variables

    devices_settings_info_account_id: null
    devices_settings_info_api_token: null

## Return Values

    _devices_settings_info_dict

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_settings_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          devices_settings_info_account_id: '{{ _accounts_info_id }}'
          devices_settings_info_api_token: '{{ accounts_info_api_token }}'
