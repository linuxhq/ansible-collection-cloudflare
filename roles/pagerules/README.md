# pagerules

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare page rules

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Page Rules`

## Role Variables

    pagerules_api_token: null
    pagerules_list: []

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pagerules
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          pagerules_api_token: "{{ zones_info_api_token }}"
          pagerules_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              pagerules:
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://github.com/linuxhq
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: "linuxhq.dev/*"
                      target: url
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://github.com/linuxhq
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: "www.linuxhq.dev/*"
                      target: url
