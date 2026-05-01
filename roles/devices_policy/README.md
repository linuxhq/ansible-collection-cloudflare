# devices\_policy

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare devices policy

Application programming interface -> [zero\_trust](https://developers.cloudflare.com/api/resources/zero_trust/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zero Trust`

## Role Variables

    devices_policy_account_id: null
    devices_policy_api_token: null
    devices_policy_dict: {}

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_policy
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          devices_policy_account_id: "{{ _accounts_info_id }}"
          devices_policy_api_token: "{{ accounts_info_api_token }}"
          devices_policy_dict:
            auto_connect: 60
            include:
              - address: 100.64.0.0/10
            service_mode_v2:
              mode: warp_tunnel_only
