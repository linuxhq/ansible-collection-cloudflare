#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rulesets
short_description: Manage Cloudflare rulesets
description:
  - Create, update, and delete a Cloudflare zone ruleset entrypoint for a phase.
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
  name:
    type: str
    description:
      - Ruleset name.
      - Required when creating the ruleset; an existing ruleset cannot be renamed.
  rules:
    type: list
    elements: dict
    description:
      - Ordered rules evaluated by the ruleset.
      - When omitted, the existing rules are preserved.
      - An explicit empty list clears the ruleset.
  phase:
    type: str
    default: http_request_firewall_custom
    description:
      - Cloudflare request phase controlled by the entrypoint ruleset.
  kind:
    type: str
    default: zone
    description:
      - Scope of the ruleset.
      - Used only when creating a ruleset.
  state:
    type: str
    choices:
      - present
      - absent
    default: present
    description:
      - Desired state of the resource.
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
- name: Ensure custom firewall ruleset exists
  linuxhq.cloudflare.rulesets:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    name: default
    rules:
      - action: block
        expression: (ip.geoip.country ne "US")
"""

RETURN = r"""
---
ruleset:
  description: Cloudflare ruleset.
  returned: when available
  type: dict
  contains:
    id:
      description: Ruleset identifier.
      returned: always
      type: str
    name:
      description: Ruleset name.
      returned: always
      type: str
    kind:
      description: Scope of the ruleset.
      returned: when available
      type: str
    phase:
      description: Cloudflare request phase controlled by the ruleset.
      returned: when available
      type: str
    rules:
      description: Ordered rules in the ruleset.
      returned: when available
      type: list
      elements: dict
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
    delete_result,
    get_result,
    normalize_current_by_desired_fields,
    post_result,
    put_result,
    require_mapping,
    resource_field,
    resource_id,
    validate_requested_values,
    values_differ,
)


def entrypoint_endpoint(zone_id, phase):
    return cloudflare_path("zones", zone_id, "rulesets", "phases", phase, "entrypoint")


def rulesets_endpoint(zone_id):
    return cloudflare_path("zones", zone_id, "rulesets")


def rules_from_resource(module, ruleset):
    rules = ruleset.get("rules")
    if rules is None:
        return []

    if not isinstance(rules, list):
        module.fail_json(msg="Cloudflare API returned malformed ruleset data")

    for rule in rules:
        require_mapping(module, rule, "ruleset rule")

    return rules


def ensure_present(module, client):
    params = module.params

    current = get_result(
        client,
        entrypoint_endpoint(params["zone_id"], params["phase"]),
        default=None,
        ok_statuses=[404],
    )

    if current is None:
        if params.get("name") is None:
            module.fail_json(msg="name is required when creating a ruleset")

        if module.check_mode:
            module.exit_json(changed=True, message="Ruleset would be created")

        payload = {
            "kind": params["kind"],
            "name": params["name"],
            "phase": params["phase"],
            "rules": params.get("rules") or [],
        }
        ruleset = post_result(
            client,
            rulesets_endpoint(params["zone_id"]),
            payload,
        )
        resource_id(module, ruleset, "ruleset")
        resource_field(module, ruleset, "name", "ruleset", expected=params["name"])
        resource_field(module, ruleset, "phase", "ruleset", expected=params["phase"])
        resource_field(module, ruleset, "kind", "ruleset", expected=params["kind"])
        rules_from_resource(module, ruleset)
        validate_requested_values(module, ruleset, payload, "ruleset")
        module.exit_json(changed=True, message="Ruleset created", ruleset=ruleset)

    current_id = resource_id(module, current, "ruleset")
    current_name = resource_field(module, current, "name", "ruleset")
    resource_field(module, current, "phase", "ruleset", expected=params["phase"])
    current_rules = rules_from_resource(module, current)

    if params.get("name") is not None and params["name"] != current_name:
        module.fail_json(
            msg="An existing ruleset cannot be renamed",
            ruleset=current,
        )

    payload = {
        "rules": (current_rules or [] if params.get("rules") is None else params["rules"]),
    }

    if not values_differ(
        normalize_current_by_desired_fields(
            {"rules": current_rules or []},
            payload,
        ),
        payload,
    ):
        module.exit_json(
            changed=False,
            message="Ruleset already present",
            ruleset=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Ruleset would be updated",
            ruleset=current,
        )

    ruleset = put_result(
        client,
        entrypoint_endpoint(params["zone_id"], params["phase"]),
        payload,
    )
    resource_id(module, ruleset, "ruleset", expected=current_id)
    resource_field(module, ruleset, "name", "ruleset", expected=current_name)
    resource_field(module, ruleset, "phase", "ruleset", expected=params["phase"])
    rules_from_resource(module, ruleset)
    validate_requested_values(module, ruleset, payload, "ruleset")
    module.exit_json(changed=True, message="Ruleset updated", ruleset=ruleset)


def ensure_absent(module, client):
    params = module.params

    current = get_result(
        client,
        entrypoint_endpoint(params["zone_id"], params["phase"]),
        default=None,
        ok_statuses=[404],
    )

    if current is None:
        module.exit_json(changed=False, message="Ruleset already absent")

    current_id = resource_id(module, current, "ruleset")
    resource_field(module, current, "phase", "ruleset", expected=params["phase"])

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Ruleset would be deleted",
            ruleset=current,
        )

    delete_result(
        client,
        cloudflare_path("zones", params["zone_id"], "rulesets", current_id),
    )
    module.exit_json(
        changed=True,
        message="Ruleset deleted",
        ruleset=current,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "name": {"type": "str"},
            "rules": {"type": "list", "elements": "dict"},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
            "kind": {"type": "str", "default": "zone"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
