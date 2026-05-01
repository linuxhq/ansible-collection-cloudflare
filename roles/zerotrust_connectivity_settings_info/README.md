# zerotrust\_connectivity\_settings\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zerotrust connectivity settings

Application programming interface -> [zero\_trust](https://developers.cloudflare.com/api/resources/zero_trust/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zero Trust`

## Role Variables

    zerotrust_connectivity_settings_info_account_id: null
    zerotrust_connectivity_settings_info_api_token: null

## Return Values

    _zerotrust_connectivity_settings_info_dict

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zerotrust_connectivity_settings_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          zerotrust_connectivity_settings_info_account_id: "{{ _accounts_info_id }}"
          zerotrust_connectivity_settings_info_api_token: "{{ accounts_info_api_token }}"
