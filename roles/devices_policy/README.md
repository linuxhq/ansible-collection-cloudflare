# devices\_policy

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare devices policy

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zero Trust`

## Role Variables

    devices_policy_account_id: null
    devices_policy_allow_mode_switch: null
    devices_policy_allow_updates: null
    devices_policy_allowed_to_leave: null
    devices_policy_api_token: null
    devices_policy_auto_connect: null
    devices_policy_captive_portal: null
    devices_policy_disable_auto_fallback: null
    devices_policy_exclude: null
    devices_policy_exclude_office_ips: null
    devices_policy_include: null
    devices_policy_lan_allow_minutes: null
    devices_policy_lan_allow_subnet_size: null
    devices_policy_register_interface_ip_with_dns: null
    devices_policy_sccm_vpn_boundary_support: null
    devices_policy_service_mode_v2: null
    devices_policy_support_url: null
    devices_policy_switch_locked: null
    devices_policy_tunnel_protocol: null

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_policy
          devices_policy_account_id: '{{ _accounts_info_id }}'
          devices_policy_api_token: '{{ accounts_info_api_token }}'
          devices_policy_auto_connect: 60
          devices_policy_include:
            - address: 100.64.0.0/10
          devices_policy_service_mode_v2:
            mode: warp_tunnel_only
