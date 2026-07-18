#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: purge_cache
short_description: Manage cloudflare purging of cache
description:
  - Execute a Cloudflare cache purge request for a zone.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  zone_id:
    required: true
    type: str
    description:
      - Cloudflare zone identifier.
  cache:
    description:
      - Cache purge payload such as C(purge_everything), C(files), C(tags), C(hosts), or C(prefixes).
    required: true
    type: dict
requirements:
  - python >= 3.9
  - cloudflare >= 5.5.0, < 6

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
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    post_result,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "cache": {"required": True, "type": "dict"},
        },
        supports_check_mode=True,
    )

    if not module.params["cache"]:
        module.fail_json(msg="cache must not be empty")

    if module.check_mode:
        module.exit_json(changed=True, message="Cache would be purged")

    with cloudflare_client(module) as client:
        result = post_result(
            client,
            "/zones/%s/purge_cache" % module.params["zone_id"],
            module.params["cache"],
        )

    module.exit_json(changed=True, message="Cache purged", purge_cache=result)


if __name__ == "__main__":
    main()
