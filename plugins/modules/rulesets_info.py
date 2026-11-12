#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rulesets_info
short_description: Gather information about Cloudflare rulesets
description:
  - Gather a ruleset entrypoint phase for all accessible zones.
  - Results include sensitive values returned by Cloudflare, such as header values set by rules; protect registered
    results and task output, for example with C(no_log).
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
  phase:
    type: str
    default: http_request_firewall_custom
    description:
      - Cloudflare request phase whose entrypoint ruleset is returned.
"""

EXAMPLES = r"""
- name: Gather rulesets
  linuxhq.cloudflare.rulesets_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
rulesets:
  description: Ruleset entrypoints grouped by zone.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Entrypoint ruleset identifier.
      returned: when a ruleset exists
      type: str
    name:
      description: Cloudflare zone name.
      returned: always
      type: str
    phase:
      description: Cloudflare request phase controlled by the ruleset.
      returned: when a ruleset exists
      type: str
    rules:
      description: Ordered rules in the entrypoint ruleset.
      returned: always
      type: list
      elements: dict
    zone_id:
      description: Cloudflare zone identifier.
      returned: always
      type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    get_or_none,
    require_mapping,
    resource_field,
    resource_id,
    resource_list,
    serialize_resource,
)


def get_entrypoint(client, zone_id, phase):
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the ruleset entrypoint",
        zone_id=zone_id,
        phase=phase,
    ):
        return serialize_resource(get_or_none(client.rulesets.phases.get, phase, zone_id=zone_id))


def run(module, client):
    phase = module.params["phase"]
    with cloudflare_error_context("Cloudflare API request failed while gathering zones"):
        zones = resource_list(module, client.zones.list(), "zone", ("id", "name"))

    rulesets = []
    for zone in zones:
        entry = {"name": zone["name"], "rules": [], "zone_id": zone["id"]}
        ruleset = get_entrypoint(client, zone["id"], phase)
        if ruleset is not None:
            entry["id"] = resource_id(module, ruleset, "ruleset")
            entry["phase"] = resource_field(module, ruleset, "phase", "ruleset", expected=phase)
            rules = ruleset.get("rules")
            if rules is None:
                rules = []
            elif not isinstance(rules, list):
                module.fail_json(msg="Cloudflare API returned malformed ruleset data")

            for rule in rules:
                require_mapping(module, rule, "ruleset rule")

            entry["rules"] = rules

        rulesets.append(entry)

    module.exit_json(changed=False, rulesets=rulesets)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
