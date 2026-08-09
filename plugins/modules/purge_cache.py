#!/usr/bin/python
# Copyright: Contributors to the Ansible project
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
      - Cache purge payload.
      - Supported keys include C(purge_everything), C(files), C(tags), C(hosts),
        and C(prefixes).
    required: true
    type: dict
requirements:
  - python >= 3.9
  - cloudflare >= 5.6.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none

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
    cloudflare_path,
    post_result,
    resource_id,
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
            cloudflare_path("zones", module.params["zone_id"], "purge_cache"),
            module.params["cache"],
        )
        resource_id(module, result, "cache purge")

    module.exit_json(changed=True, message="Cache purged", purge_cache=result)


if __name__ == "__main__":
    main()
