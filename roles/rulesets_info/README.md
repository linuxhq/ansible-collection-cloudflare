# rulesets\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare rulesets

Application programming interface -> [rulesets](https://developers.cloudflare.com/api/resources/rulesets/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Account WAF`

## Role Variables

    rulesets_info_async: 300
    rulesets_info_api_token: null
    rulesets_info_delay: 3
    rulesets_info_phase: http_request_firewall_custom
    rulesets_info_poll: 0
    rulesets_info_retries: 100

## Return Values

    _rulesets_info_dict
    _rulesets_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets_info
          rulesets_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
