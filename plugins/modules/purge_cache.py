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
      - Supported keys are C(purge_everything), C(files), C(tags), C(hosts),
        and C(prefixes); any other key fails before a request is sent.
    required: true
    type: dict
"""

EXAMPLES = r"""
- name: Purge everything
  linuxhq.cloudflare.purge_cache:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    cache:
      purge_everything: true
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
    resource_id,
    serialize_resource,
    validate_cloudflare_params,
)

CACHE_KEYS = ("files", "hosts", "prefixes", "purge_everything", "tags")


def run(module, client):
    zone_id = module.params["zone_id"]
    with cloudflare_error_context("Cloudflare API request failed while purging the cache", zone_id=zone_id):
        result = serialize_resource(client.cache.purge(zone_id=zone_id, **module.params["cache"]))

    resource_id(module, result, "cache purge", expected=zone_id)
    module.exit_json(changed=True, message="Cache purged", purge_cache=result)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "cache": {"required": True, "type": "dict"},
        },
        supports_check_mode=True,
    )

    cache = module.params["cache"]
    if not cache:
        module.fail_json(msg="cache must not be empty")

    unsupported = sorted(set(cache) - set(CACHE_KEYS))
    if unsupported:
        module.fail_json(
            msg=f"Unsupported cache keys: {', '.join(unsupported)}; supported keys are {', '.join(CACHE_KEYS)}"
        )

    if module.check_mode:
        validate_cloudflare_params(module)
        module.exit_json(changed=True, message="Cache would be purged")

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
