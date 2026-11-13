# zones\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zones

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zone`

## Role Variables

    zones_info_api_token: null
    zones_info_match: all

## Dependencies

None

## Return Values

    _zones_info_dict
    _zones_info_list

`_zones_info_list` lists every zone, including internal zones.
`_zones_info_dict` maps each non-internal zone name to its zone, so an
internal zone never shadows a public zone with the same name.

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones_info
          zones_info_api_token: '{{ accounts_info_api_token }}'
