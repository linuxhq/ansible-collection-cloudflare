#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: purge_cache
short_description: Purge cached Cloudflare content
description:
  - Execute a Cloudflare cache purge request for a zone.
  - The module reports C(changed) whenever it submits a purge request.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
  zone_id:
    required: true
    type: str
    description:
      - Cloudflare zone identifier.
  cache:
    description:
      - Cache purge payload.
      - Set at least one suboption.
    required: true
    type: dict
    suboptions:
      purge_everything:
        description:
          - Whether to purge every cached file in the zone.
        type: bool
      files:
        description:
          - URLs to purge.
          - Each item is a URL string, or a mapping with C(url) and the
            C(headers) the content was cached with.
        type: list
        elements: raw
      tags:
        description:
          - Cache tags to purge.
        type: list
        elements: str
      hosts:
        description:
          - Hostnames to purge.
        type: list
        elements: str
      prefixes:
        description:
          - URL prefixes to purge.
        type: list
        elements: str
"""

EXAMPLES = r"""
- name: Purge everything
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      purge_everything: true

- name: Purge files
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      files:
        - https://www.example.com/css/styles.css
        - url: https://www.example.com/index.html
          headers:
            Accept-Language: en-US

- name: Purge cache tags
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      tags:
        - product-page

- name: Purge hostnames
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      hosts:
        - www.example.com

- name: Purge URL prefixes
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      prefixes:
        - www.example.com/images
"""

RETURN = r"""
---
purge_cache:
  description: Cloudflare cache purge response.
  returned: when not in check mode
  type: dict
  contains:
    id:
      description: Identifier of the purged zone.
      returned: always
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    payload_from_params,
    require_cloudflare_sdk,
    resource_id,
    serialize_resource,
    validate_cloudflare_params,
)

CACHE_KEYS = ("files", "hosts", "prefixes", "purge_everything", "tags")


def cache_payload(module):
    return payload_from_params(module.params["cache"], CACHE_KEYS)


def run(module, client):
    zone_id = module.params["zone_id"]
    with cloudflare_error_context("Cloudflare API request failed while purging the cache", zone_id=zone_id):
        result = serialize_resource(client.cache.purge(zone_id=zone_id, **cache_payload(module)))

    resource_id(module, result, "cache purge", expected=zone_id)
    module.exit_json(changed=True, message="Cache purged", purge_cache=result)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "cache": {
                "required": True,
                "type": "dict",
                "options": {
                    "purge_everything": {"type": "bool"},
                    "files": {"type": "list", "elements": "raw"},
                    "tags": {"type": "list", "elements": "str"},
                    "hosts": {"type": "list", "elements": "str"},
                    "prefixes": {"type": "list", "elements": "str"},
                },
            },
        },
        supports_check_mode=True,
    )

    if not cache_payload(module):
        module.fail_json(msg="cache must not be empty")

    if module.check_mode:
        require_cloudflare_sdk(module)
        validate_cloudflare_params(module)
        module.exit_json(changed=True, message="Cache would be purged")

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
