# devices\_settings\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare devices settings

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zero Trust`

## Role Variables

    devices_settings_info_account_id: null
    devices_settings_info_api_token: null

## Return Values

    _devices_settings_info_dict

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_settings_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          devices_settings_info_account_id: "{{ _accounts_info_id }}"
          devices_settings_info_api_token: "{{ accounts_info_api_token }}"
