# pagerules

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare pagerules

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Page Rules`

## Role Variables

    pagerules_api_token: null
    pagerules_async: 300
    pagerules_batch: 10
    pagerules_delay: 3
    pagerules_list: []
    pagerules_poll: 0
    pagerules_retries: 100

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pagerules
          pagerules_api_token: '{{ accounts_info_api_token }}'
          pagerules_list:
            - zone_id: '{{ _zones_info_dict[zones_list.0.name].id }}'
              pagerules:
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://docs.ansible.com/projects/molecule
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: molecule.org/*
                      target: url
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://docs.ansible.com/projects/molecule
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: www.molecule.org/*
                      target: url
