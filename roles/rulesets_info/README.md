# rulesets\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare rulesets

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/rulesets/).

## Requirements

| Type    | Permission  | Value |
| ------- | ----------- | ----- |
| Account | Account WAF | Read  |
| Zone    | Zone        | Read  |

## Role Variables

| Variable                  | Default                        | Description                                                          |
| ------------------------- | ------------------------------ | -------------------------------------------------------------------- |
| `rulesets_info_api_token` | `null`                         | Cloudflare API token; null skips the query and publishes empty facts |
| `rulesets_info_phase`     | `http_request_firewall_custom` | Ruleset phase to read                                                |

## Dependencies

None

## Return Values

    _rulesets_info_dict
    _rulesets_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets_info
          rulesets_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
