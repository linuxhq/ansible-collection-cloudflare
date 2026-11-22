# zones\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zones

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zones/).

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | Zone       | Read  |

## Role Variables

| Variable               | Default | Description                               |
| ---------------------- | ------- | ----------------------------------------- |
| `zones_info_api_token` | `null`  | Cloudflare API token; null skips the role |

## Dependencies

None

## Return Values

    _zones_info_dict
    _zones_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones_info
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
