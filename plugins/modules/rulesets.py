#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rulesets
short_description: Manage Cloudflare rulesets
description:
  - Create, update, and delete a Cloudflare zone ruleset entrypoint for a phase.
  - Results include sensitive values returned by Cloudflare, such as header values set by rules; protect registered
    results and task output, for example with C(no_log).
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
  name:
    type: str
    description:
      - Ruleset name.
      - Required when creating the ruleset; an existing ruleset cannot be renamed.
      - An existing ruleset's description is preserved.
  rules:
    type: list
    elements: dict
    description:
      - Ordered rules evaluated by the ruleset.
      - When omitted, the existing rules are preserved.
      - An explicit empty list clears the ruleset.
      - A rule without C(enabled) is enabled, as in Cloudflare; set C(enabled=false)
        to keep a rule disabled.
      - Each rule is compared on all of its top-level fields, so omitting a field,
        such as C(description), removes it. Fields Cloudflare assigns, C(id), C(ref),
        C(version), and C(last_updated), are ignored unless set. A C(skip) rule
        without C(logging) uses Cloudflare's default, C(logging.enabled=true).
      - A rule's C(action_parameters.headers) and C(action_parameters.rules) mappings
        are compared on their complete key sets, so omitting an entry removes it.
      - Use the Cloudflare API names for C(set_cache_control) directives, such as
        C(max-age) and C(no-cache); their snake_case spellings fail before any change.
      - When rules hold credentials, pass them from a vaulted variable and set
        C(no_log) on the task.
  phase:
    type: str
    default: http_request_firewall_custom
    description:
      - Cloudflare request phase controlled by the entrypoint ruleset.
  kind:
    type: str
    default: zone
    choices:
      - zone
    description:
      - Scope of the ruleset. This module manages only zone phase entrypoints.
      - Custom, managed, and account-level rulesets are not supported.
  state:
    type: str
    choices:
      - present
      - absent
    default: present
    description:
      - Desired state of the resource.
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
    cloudflare_error_context,
    ensure_resource_absent,
    ensure_resource_present,
    get_or_none,
    normalize_current_by_desired_fields,
    require_mapping,
    resource_field,
    serialize_resource,
    values_differ,
)

# The SDK renames these snake_case action parameters to their API spellings on
# write, so Cloudflare would store and return keys that never match the request.
ACTION_PARAMETER_API_KEYS = {
    "max_age": "max-age",
    "must_revalidate": "must-revalidate",
    "must_understand": "must-understand",
    "no_cache": "no-cache",
    "no_store": "no-store",
    "no_transform": "no-transform",
    "proxy_revalidate": "proxy-revalidate",
    "s_maxage": "s-maxage",
    "stale_if_error": "stale-if-error",
    "stale_while_revalidate": "stale-while-revalidate",
}


def validate_action_parameters(module):
    """Fail when an action parameter uses an SDK spelling instead of its API key."""
    for rule in module.params.get("rules") or ():
        action_parameters = rule.get("action_parameters")
        if not isinstance(action_parameters, dict):
            continue

        for key, api_key in ACTION_PARAMETER_API_KEYS.items():
            if key in action_parameters:
                module.fail_json(msg=f"action_parameters key {key!r} must use the Cloudflare API key {api_key!r}")


def rules_from_resource(module, ruleset):
    rules = ruleset.get("rules")
    if rules is None:
        return []

    if not isinstance(rules, list):
        module.fail_json(msg="Cloudflare API returned malformed ruleset data")

    for rule in rules:
        require_mapping(module, rule, "ruleset rule")

    return rules


# Cloudflare assigns these rule fields; every other rule field is managed.
ASSIGNED_RULE_FIELDS = ("id", "last_updated", "ref", "version")

# Rule fields Cloudflare fills in when a rule with this action omits them.
RULE_DEFAULTS = {"skip": {"logging": {"enabled": True}}}

# Header and skip-rule maps are compared whole, so removed entries count.
EXACT_RULE_FIELDS = ("headers", "rules")


def compared_rule_field(rule, key, desired):
    """Return whether a current rule field takes part in the comparison.

    The update replaces every rule, so a field the request omits is a
    difference, unless Cloudflare assigned it or it holds Cloudflare's default
    for the rule's action.
    """
    if key in desired:
        return True

    if key in ASSIGNED_RULE_FIELDS:
        return False

    defaults = RULE_DEFAULTS.get(rule.get("action"), {})
    return key not in defaults or values_differ(rule[key], defaults[key])


def comparable_rules(rules, desired_rules):
    """Project current rules for comparison with the desired rules.

    Each rule keeps every compared field; nested mappings are projected onto
    the requested fields.
    """
    comparable = []
    for index, rule in enumerate(rules):
        desired = desired_rules[index] if index < len(desired_rules) else {}
        comparable.append(
            {
                key: (
                    normalize_current_by_desired_fields(value, desired[key], EXACT_RULE_FIELDS)
                    if key in desired
                    else value
                )
                for key, value in rule.items()
                if compared_rule_field(rule, key, desired)
            }
        )

    return comparable


def checked_ruleset(module, ruleset, phase):
    """Serialize a ruleset response and validate its phase and rules."""
    ruleset = serialize_resource(ruleset)
    require_mapping(module, ruleset, "ruleset")
    resource_field(module, ruleset, "phase", "ruleset", expected=phase)
    rules_from_resource(module, ruleset)
    return ruleset


def run(module, client):
    params = module.params
    zone_id = params["zone_id"]
    phase = params["phase"]
    rulesets = client.rulesets
    if params["state"] == "present":
        validate_action_parameters(module)

    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the ruleset entrypoint",
        zone_id=zone_id,
        phase=phase,
    ):
        current = get_or_none(rulesets.phases.get, phase, zone_id=zone_id)
        if current is not None:
            current = checked_ruleset(module, current, phase)

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "ruleset",
            "ruleset",
            current,
            delete=lambda ruleset_id: rulesets.delete(ruleset_id, zone_id=zone_id),
            context={"zone_id": zone_id},
        )

    # The update replaces every rule, so give each rule Cloudflare's enabled
    # default; an existing disabled rule is then a visible change, not re-enabled
    # silently.
    rules = None if params.get("rules") is None else [{"enabled": True, **rule} for rule in params["rules"]]

    if current is None:
        if params.get("name") is None:
            module.fail_json(msg="name is required when creating a ruleset")

        name = params["name"]
        payload = {"kind": params["kind"], "name": name, "phase": phase, "rules": rules or []}
    else:
        name = resource_field(module, current, "name", "ruleset")
        if params.get("name") is not None and params["name"] != name:
            module.fail_json(msg="An existing ruleset cannot be renamed", ruleset=current)

        # Omitted rules preserve the current rules, so there is nothing to compare.
        payload = {} if rules is None else {"rules": rules}
        # The update replaces the entrypoint and clears a description it omits,
        # so carry the current description, which this module does not manage.
        if payload and current.get("description"):
            payload["description"] = current["description"]

    ensure_resource_present(
        module,
        "ruleset",
        "ruleset",
        current,
        payload,
        create=lambda payload: checked_ruleset(module, rulesets.create(zone_id=zone_id, **payload), phase),
        update=lambda ruleset_id, payload: checked_ruleset(
            module,
            rulesets.phases.update(phase, zone_id=zone_id, **payload),
            phase,
        ),
        expected_name=name,
        defaults={"rules": []},
        exact_values=("rules",),
        context={"zone_id": zone_id},
        comparable=lambda ruleset: {
            **ruleset,
            "rules": comparable_rules(rules_from_resource(module, ruleset), payload.get("rules", [])),
        },
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "name": {"type": "str"},
            "rules": {"type": "list", "elements": "dict"},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
            "kind": {"type": "str", "default": "zone", "choices": ["zone"]},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
