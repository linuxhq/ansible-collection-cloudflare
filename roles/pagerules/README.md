# pagerules

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare pagerules

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/page_rules/).

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | Page Rules | Write |
| Zone | Zone       | Read  |

## Role Variables

| Variable              | Default | Description                               |
| --------------------- | ------- | ----------------------------------------- |
| `pagerules_api_token` | `null`  | Cloudflare API token; null skips the role |
| `pagerules_list`      | `[]`    | Zones and their page rules to manage      |

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pagerules
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          pagerules_api_token: '{{ zones_info_api_token }}'
          pagerules_list:
            - zone_id: "{{ _zones_info_dict['molecule.org'].id }}"
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
