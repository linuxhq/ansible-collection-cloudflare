# purge\_cache

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare purging of cache

Application programming interface -> [cache](https://developers.cloudflare.com/api/resources/cache/)

## Requirements

* Cloudflare api `Token` with `Purge` permissions to `Cache Purge`

## Role Variables

    purge_cache_api_token: null
    purge_cache_list: []

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.purge_cache
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          purge_cache_api_token: "{{ zones_info_api_token }}"
          purge_cache_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              cache:
                purge_everything: true
