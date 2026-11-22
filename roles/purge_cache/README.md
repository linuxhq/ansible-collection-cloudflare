# purge\_cache

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare purging of cache

## Requirements

| Type | Permission  | Value |
| ---- | ----------- | ----- |
| Zone | Cache Purge | Purge |
| Zone | Zone        | Read  |

## Role Variables

    purge_cache_api_token: null
    purge_cache_async: 300
    purge_cache_batch: 10
    purge_cache_delay: 3
    purge_cache_list: []
    purge_cache_poll: 0
    purge_cache_retries: 100

Each `purge_cache_list` item requires `zone_id` and `cache`, the
`linuxhq.cloudflare.purge_cache` module options. An item without either fails,
naming the missing option. The role does nothing while `purge_cache_api_token`
is `null`.

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.purge_cache
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          purge_cache_api_token: '{{ zones_info_api_token }}'
          purge_cache_list:
            - zone_id: "{{ _zones_info_dict['molecule.com'].id }}"
              cache:
                purge_everything: true
