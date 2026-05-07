# access\_identity\_providers\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access identity providers

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Access: Organizations, Identity Providers, and Groups`

## Role Variables

    access_identity_providers_info_account_id: null
    access_identity_providers_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_identity_providers_info_dict
    _access_identity_providers_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_identity_providers_info
          access_identity_providers_info_account_id: "{{ _accounts_info_id }}"
          access_identity_providers_info_api_token: "{{ accounts_info_api_token }}"
