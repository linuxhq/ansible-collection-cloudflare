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
notes:
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.create
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
      - Required when creating the ruleset.
      - An existing ruleset cannot be renamed, because Cloudflare keeps the stored name of a phase entrypoint;
        when O(name) differs from it, the module fails before any change, including with O(state=absent).
  rules:
    type: list
    elements: dict
    description:
      - Ordered rules evaluated by the ruleset.
      - When omitted, the existing rules are preserved.
      - An update of the rules preserves the existing ruleset's description.
      - An explicit empty list clears the ruleset.
      - A rule without C(enabled) is enabled, as in Cloudflare; set C(enabled=false)
        to keep a rule disabled.
      - Each rule is compared on all of its top-level fields, so omitting a field,
        such as C(description), removes it. Fields Cloudflare assigns, C(id), C(ref),
        C(version), and C(last_updated), are ignored unless set. A C(skip) rule
        without C(logging) uses Cloudflare's default, C(logging.enabled=true).
        Cloudflare drops an empty C(description) or C(action_parameters), so either
        matches a rule without that field.
      - An empty C(action_parameters.phases), C(action_parameters.products),
        C(action_parameters.rules), or C(action_parameters.rulesets) fails
        before any change, including one that is empty once its null keys are
        dropped, because Cloudflare does not store it; omit the parameter
        instead.
      - An empty C(id) or C(ref) fails before any change, because Cloudflare
        assigns the rule its own value instead; omit the field instead.
      - A rule's C(action_parameters) are compared on their complete key sets
        at every level, as Cloudflare stores them exactly as sent and an update
        replaces them, so omitting a parameter or a nested key, such as a
        C(headers) entry, removes it. The C(version) Cloudflare sets to
        V(latest) for an C(execute) rule that omits it is ignored.
      - Other nested rule mappings, such as C(ratelimit) and
        C(exposed_credential_check), are also compared on their complete key
        sets, as an update replaces them, so omitting a nested key removes it.
        Cloudflare drops C(ratelimit.requests_to_origin=false), so it matches a
        stored rule without the key.
      - Use the Cloudflare API names for C(set_cache_control) directives, such as
        C(max-age) and C(no-cache); their snake_case spellings fail before any change.
      - A rule field set to null, at any level, such as a key of
        C(action_parameters), is not sent and counts as omitted.
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
    require_mapping,
    require_mapping_list,
    resource_field,
    serialize_resource,
    unique_match,
    values_differ,
    without_nested_nulls,
    without_retries,
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

# Skip rule action parameters Cloudflare drops when they hold these empty values.
EMPTY_SKIP_PARAMETERS = {"phases": [], "products": [], "rules": {}, "rulesets": []}


def validate_action_parameters(module):
    """Fail when an action parameter uses an SDK spelling or a skip parameter is empty.

    Cloudflare drops an empty phases, products, rules, or rulesets value, so
    the rule would never match the request.
    """
    empty = []
    for index, rule in enumerate(module.params.get("rules") or ()):
        action_parameters = rule.get("action_parameters")
        if not isinstance(action_parameters, dict):
            continue

        # A key set to null is not sent, so it counts as omitted.
        for key, api_key in ACTION_PARAMETER_API_KEYS.items():
            if action_parameters.get(key) is not None:
                module.fail_json(
                    msg=f"rules[{index}].action_parameters.{key} must use the Cloudflare API key {api_key!r}"
                )

        # Nested null keys are not sent either, so check the value that is sent.
        sent = without_nested_nulls(action_parameters)
        empty.extend(
            f"rules[{index}].action_parameters.{key}"
            for key, value in EMPTY_SKIP_PARAMETERS.items()
            if key in sent and sent[key] == value
        )

    if empty:
        module.fail_json(
            msg=f"Cloudflare does not store these empty action parameters: {', '.join(empty)}; omit them instead",
            empty_fields=empty,
        )


def validate_assigned_fields(module):
    """Fail when a rule requests an empty id or ref.

    Cloudflare assigns the rule its own value instead, so the rule would never
    match the request.
    """
    empty = [
        f"rules[{index}].{field}"
        for index, rule in enumerate(module.params.get("rules") or ())
        for field in ("id", "ref")
        if rule.get(field) == ""
    ]
    if empty:
        module.fail_json(
            msg=f"Cloudflare assigns its own value for these empty rule fields: {', '.join(empty)}; omit them instead",
            empty_fields=empty,
        )


def rules_from_resource(module, ruleset, failure=None):
    """Return the rules of ruleset; failure adds result fields to a malformed-data failure."""
    rules = ruleset.get("rules")
    if rules is None:
        return []

    return require_mapping_list(module, rules, "ruleset", "ruleset rule", failure)


# Cloudflare assigns these rule fields; every other rule field is managed.
ASSIGNED_RULE_FIELDS = ("id", "last_updated", "ref", "version")

# Rule fields Cloudflare fills in when a rule with this action omits them.
RULE_DEFAULTS = {"skip": {"logging": {"enabled": True}}}

# Action parameters Cloudflare fills in when a rule with this action omits them.
ACTION_PARAMETER_DEFAULTS = {"execute": {"version": "latest"}}

# Cloudflare drops these rule fields when they are empty.
EMPTY_RULE_FIELDS = {"action_parameters": {}, "description": ""}

# Keys of nested rule mappings Cloudflare drops when they hold these values, so
# a stored mapping without the key matches a request that sets it to the value.
DROPPED_NESTED_DEFAULTS = {"ratelimit": {"requests_to_origin": False}}


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


def comparable_action_parameters(rule, desired):
    """Return the rule's action_parameters without the defaults Cloudflare filled in that desired omits.

    Cloudflare stores the other action parameters exactly as sent, so they are
    kept whole.
    """
    value = rule.get("action_parameters")
    requested = desired.get("action_parameters")
    requested = requested if isinstance(requested, dict) else {}
    defaults = ACTION_PARAMETER_DEFAULTS.get(rule.get("action"), {})
    if not isinstance(value, dict):
        return value

    return {
        key: item
        for key, item in value.items()
        if key in requested or key not in defaults or values_differ(item, defaults[key])
    }


def comparable_nested_mapping(rule, key, desired):
    """Return a rule's nested mapping with the dropped defaults that desired sets.

    The update replaces the mapping, so it is compared on its complete key
    set; a key Cloudflare drops when it holds its default is filled in with
    that default when desired sets it.
    """
    value = rule[key]
    requested = desired.get(key)
    if not isinstance(value, dict) or not isinstance(requested, dict):
        return value

    defaults = DROPPED_NESTED_DEFAULTS.get(key, {})
    return {**{name: item for name, item in defaults.items() if name in requested}, **value}


def comparable_rules(rules, desired_rules):
    """Project current rules for comparison with the desired rules.

    Each rule keeps every compared field, and nested mappings are compared on
    their complete key sets. Its action_parameters omit defaults Cloudflare
    filled in, and other nested mappings gain the defaults Cloudflare drops
    that the request sets.
    """
    comparable = []
    for index, rule in enumerate(rules):
        desired = desired_rules[index] if index < len(desired_rules) else {}
        rule = {**{key: value for key, value in EMPTY_RULE_FIELDS.items() if key in desired}, **rule}
        comparable.append(
            {
                key: (
                    comparable_action_parameters(rule, desired)
                    if key == "action_parameters"
                    else comparable_nested_mapping(rule, key, desired)
                )
                for key in rule
                if compared_rule_field(rule, key, desired)
            }
        )

    return comparable


def checked_ruleset(module, ruleset, phase, failure=None):
    """Serialize a ruleset response and validate its phase.

    failure adds result fields to a failure, such as changed=True after a write.
    """
    ruleset = serialize_resource(ruleset)
    require_mapping(module, ruleset, "ruleset", failure)
    resource_field(module, ruleset, "phase", "ruleset", expected=phase, context=failure)
    return ruleset


def run(module, client):
    params = module.params
    zone_id = params["zone_id"]
    phase = params["phase"]
    rulesets = client.rulesets
    lookup = {"zone_id": zone_id, "phase": phase}
    if params["state"] == "present":
        validate_action_parameters(module)
        validate_assigned_fields(module)

    with cloudflare_error_context("Cloudflare API request failed while gathering the ruleset entrypoint", **lookup):
        current = get_or_none(rulesets.phases.get, phase, zone_id=zone_id)
        if current is not None:
            current = checked_ruleset(module, current, phase, lookup)

    if current is not None:
        name = resource_field(module, current, "name", "ruleset", context=lookup)
        if params.get("name") is not None and params["name"] != name:
            failure = {**lookup, "ruleset": current}
            if params["state"] == "absent":
                module.fail_json(msg="An existing ruleset with a different name cannot be deleted", **failure)

            module.fail_json(msg="An existing ruleset cannot be renamed", **failure)

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "ruleset",
            "ruleset",
            current,
            delete=lambda ruleset_id: rulesets.delete(ruleset_id, zone_id=zone_id),
            context=lookup,
        )

    # The update replaces every rule, so give each rule Cloudflare's enabled
    # default; an existing disabled rule is then a visible change, not re-enabled
    # silently. A null rule field, at any level, counts as omitted.
    rules = (
        None
        if params.get("rules") is None
        else [{"enabled": True, **without_nested_nulls(rule)} for rule in params["rules"]]
    )

    if current is None:
        # Cloudflare rejects a new ruleset without a name.
        name = params.get("name")
        payload = {"kind": params["kind"], "name": name, "phase": phase, "rules": rules or []}
    else:
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
        create=lambda payload: without_retries(client).rulesets.create(zone_id=zone_id, **payload),
        update=lambda ruleset_id, payload: rulesets.phases.update(phase, zone_id=zone_id, **payload),
        # A zone has at most one entrypoint ruleset per phase.
        find_created=lambda: unique_match(get_or_none(rulesets.phases.get, phase, zone_id=zone_id)),
        expected_name=name,
        defaults={"rules": []},
        exact_values=("rules",),
        context=lookup,
        comparable=lambda ruleset, failure: {
            **ruleset,
            "rules": comparable_rules(
                rules_from_resource(module, checked_ruleset(module, ruleset, phase, failure), failure),
                payload.get("rules", []),
            ),
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
