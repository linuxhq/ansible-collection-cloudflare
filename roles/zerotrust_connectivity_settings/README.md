# zerotrust\_connectivity\_settings

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare zerotrust connectivity settings

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zero Trust`
* Cloudflare api `Token` with `Read` permissions to `Account Settings`

## Role Variables

    zerotrust_connectivity_settings_account_id: null
    zerotrust_connectivity_settings_api_token: null
    zerotrust_connectivity_settings_icmp_proxy_enabled: false
    zerotrust_connectivity_settings_offramp_warp_enabled: false

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zerotrust_connectivity_settings
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          zerotrust_connectivity_settings_account_id: '{{ _accounts_info_id }}'
          zerotrust_connectivity_settings_api_token: '{{ accounts_info_api_token }}'
          zerotrust_connectivity_settings_icmp_proxy_enabled: true
          zerotrust_connectivity_settings_offramp_warp_enabled: true
