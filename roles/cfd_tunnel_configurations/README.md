# cfd\_tunnel\_configurations

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnel configurations

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_configurations_account_id: null
    cfd_tunnel_configurations_api_token: null
    cfd_tunnel_configurations_async: 300
    cfd_tunnel_configurations_batch: 10
    cfd_tunnel_configurations_delay: 3
    cfd_tunnel_configurations_list: []
    cfd_tunnel_configurations_poll: 0
    cfd_tunnel_configurations_retries: 100

## Dependencies

* [accounts\_info](../accounts_info)
* [cfd\_tunnel\_info](../cfd_tunnel_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel_configurations
          cfd_tunnel_configurations_account_id: '{{ _accounts_info_id }}'
          cfd_tunnel_configurations_api_token: '{{ accounts_info_api_token }}'
          cfd_tunnel_configurations_list:
            - tunnel_id: "{{ _cfd_tunnel_info_dict['molecule'].id }}"
              config:
                ingress:
                  - hostname: organic.molecule.org
                    originRequest:
                      http2Origin: true
                      originServerName: organic.molecule.org
                    service: https://nginx:8443
                  - hostname: inorganic.molecule.org
                    originRequest:
                      http2Origin: true
                      originServerName: inorganic.molecule.org
                    service: https://nginx:8443
                  - service: http_status:404
