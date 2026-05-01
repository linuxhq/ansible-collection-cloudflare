# cfd\_tunnel\_configurations

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnel configurations

Application programming interface -> [tunnels](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_configurations_account_id: null
    cfd_tunnel_configurations_api_token: null
    cfd_tunnel_configurations_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)
* [linuxhq.cloudflare.cfd\_tunnel\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/cfd_tunnel_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel_configurations
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq

          cfd_tunnel_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_api_token: "{{ accounts_info_api_token }}"
          cfd_tunnel_list:
            - name: linuxhq.dev-remote
              config_src: cloudflare

          cfd_tunnel_info_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_info_api_token: "{{ accounts_info_api_token }}"

          cfd_tunnel_configurations_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_configurations_api_token: "{{ accounts_info_api_token }}"
          cfd_tunnel_configurations_list:
            - tunnel_id: "{{ _cfd_tunnel_info_dict['linuxhq.dev-remote'].id }}"
              config:
                ingress:
                  - hostname: molecule-a.linuxhq.dev
                    originRequest:
                      http2Origin: true
                      originServerName: molecule-a.linuxhq.dev
                    service: https://nginx:8443
                  - hostname: molecule-b.linuxhq.dev
                    originRequest:
                      http2Origin: true
                      originServerName: molecule-b.linuxhq.dev
                    service: https://nginx:8443
                  - service: http_status:404
