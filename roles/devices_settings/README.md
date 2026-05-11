# devices\_settings

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare devices settings

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zero Trust`

## Role Variables

    devices_settings_account_id: null
    devices_settings_api_token: null
    devices_settings_disable_for_time: 0
    devices_settings_gateway_proxy_enabled: false
    devices_settings_gateway_udp_proxy_enabled: false
    devices_settings_root_certificate_installation_enabled: false
    devices_settings_use_zt_virtual_ip: false

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_settings
          devices_settings_gateway_proxy_enabled: true
          devices_settings_gateway_udp_proxy_enabled: true
          devices_settings_use_zt_virtual_ip: true
