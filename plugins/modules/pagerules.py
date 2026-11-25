#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pagerules
short_description: Manage Cloudflare Page Rules
description:
  - Create, update, and delete Cloudflare page rules identified by their targets.
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
  actions:
    type: list
    elements: dict
    description:
      - Actions applied when the page rule matches.
      - Each action accepts only C(id) and C(value), and the
        C(always_use_https), C(disable_apps), C(disable_performance),
        C(disable_security), and C(disable_zaraz) actions accept only C(id).
        The C(value) of a C(forwarding_url) action accepts only C(url) and
        C(status_code). Cloudflare accepts any other key but does not store
        it, so the module fails before making changes.
      - An action C(id) that is a mapping or a list fails before any request.
      - Actions are compared by C(id), regardless of their order.
      - The C(value) of a C(cache_ttl_by_status) action is compared on every
        key, so a status code removed from it is removed from the rule. Other
        action values are compared only on the keys given.
      - A field set to null, at any level, is not sent and counts as omitted.
      - Required when O(state=present).
  targets:
    required: true
    type: list
    elements: dict
    description:
      - URL matching conditions that identify the page rule.
      - With O(state=present), each target accepts only C(target) and
        C(constraint), whose C(operator) and C(value) are its only keys.
        Cloudflare accepts any other key but does not store it, so the module
        fails before making changes.
      - A page rule matches only when its stored targets equal the requested
        targets.
      - A field set to null, at any level, is not sent and counts as omitted.
      - URL values are matched as Cloudflare stores them, with the host in
        lowercase and a slash after a bare host, before any trailing wildcard.
        A bare host followed by a query gets no slash.
  priority:
    type: int
    description:
      - Priority of the page rule, from 1 to the number of page rules in the
        zone, including a rule being created.
      - A higher number is a higher priority. When several page rules match a
        request, only the matching rule with the highest priority applies, and
        the Cloudflare dashboard lists it first.
      - A priority of 0 or above that number fails before any change, because
        Cloudflare would store the rule with the lowest or highest priority
        instead. Cloudflare rejects a negative priority.
      - In check mode, the upper bound is not checked, because page rules that
        earlier tasks in the same run would create are not counted.
      - An existing rule's priority is preserved when omitted.
  status:
    type: str
    choices:
      - active
      - disabled
    description:
      - Whether the page rule is active or disabled.
      - Defaults to C(active) when creating a page rule; an existing rule's
        status is preserved when omitted.
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
- name: Ensure page rule exists
  linuxhq.cloudflare.pagerules:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    actions:
      - id: forwarding_url
        value:
          status_code: 301
          url: https://www.example.com
    targets:
      - target: url
        constraint:
          operator: matches
          value: example.com/*

- name: Ensure page rule has the lowest priority but is paused
  linuxhq.cloudflare.pagerules:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    priority: 1
    status: disabled
    actions:
      - id: cache_level
        value: bypass
    targets:
      - target: url
        constraint:
          operator: matches
          value: example.com/admin/*

- name: Ensure page rule is absent
  linuxhq.cloudflare.pagerules:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    state: absent
    targets:
      - target: url
        constraint:
          operator: matches
          value: example.com/*
"""

RETURN = r"""
---
pagerule:
  description: Cloudflare page rule.
  returned: when available
  type: dict
  contains:
    id:
      description: Page rule identifier.
      returned: always
      type: str
    actions:
      description: Actions applied by the page rule.
      returned: always
      type: list
      elements: dict
    priority:
      description: Priority of the page rule; a higher number is a higher priority.
      returned: when available
      type: int
    status:
      description: Current page rule status.
      returned: when available
      type: str
    targets:
      description: Target constraints identifying the page rule.
      returned: always
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
    payload_from_params,
    require_mapping_list,
    require_present_options,
    resource_id,
    serialize_resource,
    unsupported_fields,
    values_differ,
    without_nested_nulls,
    without_retries,
)

# Fields sent from the module parameters, and carried from the current rule on update.
FIELDS = ("priority", "status")

# Cloudflare answers a request for a deleted page rule with this error code
# and a 400 status.
INVALID_PAGERULE_CODE = 1002

# Actions whose value mapping is compared on every key, not only those requested.
EXACT_VALUE_ACTIONS = ("cache_ttl_by_status",)

# Fields Cloudflare stores, from the cloudflare SDK page rule create types; it
# accepts any other field but drops it. Action values typed as mappings are
# keyed by action id; other values are not checked.
TARGET_FIELDS = {"constraint": ("operator", "value"), "target": None}
ACTION_FIELDS = ("id", "value")
# Actions whose SDK type has only an id; Cloudflare drops their value.
ID_ONLY_ACTIONS = ("always_use_https", "disable_apps", "disable_performance", "disable_security", "disable_zaraz")
ACTION_VALUE_FIELDS = {"forwarding_url": ("status_code", "url")}


def validate_field_names(module):
    """Fail when a target or action field Cloudflare accepts but never stores is requested.

    Targets and actions are not sent when removing a page rule. Null fields
    are ignored, as Cloudflare drops them and the comparison ignores them.
    Null actions fail as missing ones do.
    """
    params = module.params
    if params["state"] != "present":
        return

    require_present_options(module, ("actions",))
    # Actions are keyed by id, so an id must be hashable.
    invalid = [
        f"actions[{index}].id"
        for index, action in enumerate(params["actions"])
        if isinstance(action.get("id"), (dict, list))
    ]
    if invalid:
        module.fail_json(msg=f"{', '.join(invalid)} must not be a mapping or a list", invalid_fields=invalid)

    unknown = []
    for index, target in enumerate(params["targets"]):
        unknown.extend(unsupported_fields(target, TARGET_FIELDS, f"targets[{index}]"))

    for index, action in enumerate(params["actions"]):
        path = f"actions[{index}]"
        action_id = action.get("id")
        fields = ("id",) if action_id in ID_ONLY_ACTIONS else ACTION_FIELDS
        unknown.extend(unsupported_fields(action, fields, path))
        if action_id in ACTION_VALUE_FIELDS:
            unknown.extend(unsupported_fields(action.get("value"), ACTION_VALUE_FIELDS[action_id], f"{path}.value"))

    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these page rule fields: {', '.join(unknown)}",
            unsupported_fields=unknown,
        )


def canonical_url(value):
    """Return a URL pattern as Cloudflare stores it.

    Cloudflare lowercases the host and adds a slash after a bare host, before
    a trailing wildcard, so example.com* becomes example.com/*; the scheme and
    path keep their case. A bare host followed by a query or fragment is only
    lowercased, so Example.com?a=B becomes example.com?a=B.
    """
    scheme, separator, rest = value.partition("://")
    if not separator or any(character in scheme for character in "/?#"):
        # A "://" after the first slash, "?" or "#" belongs to the path, query
        # or fragment, not a scheme.
        scheme, separator, rest = "", "", value

    host, slash, path = rest.partition("/")
    if "?" in host or "#" in host:
        # Lowercase only the host before the query or fragment; add no slash.
        end = min(index for index in (rest.find("?"), rest.find("#")) if index >= 0)
        return f"{scheme}{separator}{rest[:end].lower()}{rest[end:]}"

    if not slash and host.endswith("*"):
        host, path = host[:-1], "*"

    return f"{scheme}{separator}{host.lower()}/{path}"


def canonical_targets(targets):
    canonical = []
    for target in targets:
        constraint = target.get("constraint")
        if target.get("target") == "url" and isinstance(constraint, dict) and isinstance(constraint.get("value"), str):
            target = {**target, "constraint": {**constraint, "value": canonical_url(constraint["value"])}}

        canonical.append(target)

    return canonical


def pagerule_list(module, pagerule, field, item_name, context):
    """Return the targets or actions of the page rule, failing when they are not a list of mappings.

    context adds result fields to the failure, which also names the page
    rule's id.
    """
    if "id" in pagerule:
        context = {"resource_id": pagerule["id"], **context}

    return require_mapping_list(module, pagerule.get(field), "page rule", item_name, context)


def ordered_actions(actions, current_actions):
    """Return actions in the order of the current action ids, then sorted by id.

    Cloudflare lists a rule's actions sorted by id but echoes a write in request
    order, so action order is not significant.
    """
    order = [action.get("id") for action in current_actions]
    return sorted(
        actions,
        key=lambda action: (
            order.index(action.get("id")) if action.get("id") in order else len(order),
            str(action.get("id")),
        ),
    )


def comparable_pagerule(module, pagerule, actions, failure):
    """Return pagerule with EXACT_VALUE_ACTIONS values compared on every key.

    The comparison projects a stored mapping onto the requested keys, which
    would hide a key removed from the request. A stored value with a key the
    request lacks is replaced by its sorted keys, which never match a mapping.
    failure adds result fields to a malformed-data failure.
    """
    requested = {action.get("id"): action.get("value") for action in actions}
    comparable_actions = []
    for action in pagerule_list(module, pagerule, "actions", "page rule action", failure):
        if action.get("id") in EXACT_VALUE_ACTIONS:
            value = action.get("value")
            wanted = requested.get(action["id"])
            if isinstance(value, dict) and isinstance(wanted, dict) and not value.keys() <= wanted.keys():
                action = {**action, "value": sorted(value)}

        comparable_actions.append(action)

    return {**pagerule, "actions": comparable_actions}


def target_identity(targets):
    """Return targets with only the target and constraint operator and value, which identify a page rule.

    Other keys are compared as part of the rule, so a rule whose targets differ
    only in them is updated rather than created again.
    """
    identity = []
    for target in targets:
        target = {key: value for key, value in target.items() if key in ("constraint", "target")}
        constraint = target.get("constraint")
        if isinstance(constraint, dict):
            target["constraint"] = {key: value for key, value in constraint.items() if key in ("operator", "value")}

        identity.append(target)

    return identity


def matching_pagerules(module, client, targets):
    """Return the page rules matching targets and the zone's rule count."""
    zone_id = module.params["zone_id"]
    context = {"zone_id": zone_id}
    with cloudflare_error_context(
        "Cloudflare API request failed while finding the page rule",
        **context,
    ):
        pagerules = serialize_resource(client.page_rules.list(zone_id=zone_id))

    # The SDK types this response as optional; treat null as no rules.
    if pagerules is None:
        pagerules = []

    identity = target_identity(targets)
    matches = []
    for pagerule in require_mapping_list(module, pagerules, "page rule", "page rule", context):
        stored = target_identity(pagerule_list(module, pagerule, "targets", "page rule target", context))
        if not values_differ(stored, identity):
            matches.append(pagerule)

    return matches, len(pagerules)


def created_pagerules(client, zone_id, targets):
    """Return the page rules matching targets, for create_once to find a created rule.

    Unlike matching_pagerules, it never fails the module: a malformed list,
    rule or targets is no match, so create_once raises the create error.
    """
    identity = target_identity(targets)
    pagerules = serialize_resource(client.page_rules.list(zone_id=zone_id))
    return [
        pagerule
        for pagerule in (pagerules if isinstance(pagerules, list) else [])
        if isinstance(pagerule, dict)
        and isinstance(pagerule.get("targets"), list)
        and all(isinstance(target, dict) for target in pagerule["targets"])
        and not values_differ(target_identity(pagerule["targets"]), identity)
    ]


def find_pagerule(module, client, targets):
    """Return the page rule matching targets, or None, and the zone's rule count."""
    zone_id = module.params["zone_id"]
    matches, rule_count = matching_pagerules(module, client, targets)
    if len(matches) > 1:
        module.fail_json(
            msg="Multiple page rules match the requested target constraints",
            zone_id=zone_id,
            matching_ids=[
                resource_id(module, pagerule, "page rule", context={"zone_id": zone_id}) for pagerule in matches
            ],
        )

    return matches[0] if matches else None, rule_count


def validate_priority(module, current, rule_count):
    """Fail when priority is 0 or exceeds the zone's rule count after this change.

    Cloudflare stores 0 as 1 and rejects a negative priority.

    Check mode skips the upper bound: rules that earlier tasks would create are
    not in the current count, so a valid batch would fail.
    """
    priority = module.params.get("priority")
    if priority == 0:
        module.fail_json(msg="priority 0 must be at least 1", zone_id=module.params["zone_id"])

    if module.check_mode:
        return

    maximum = rule_count + (1 if current is None else 0)
    if priority is not None and priority > maximum:
        module.fail_json(
            msg=f"priority {priority} exceeds the number of page rules in the zone; the maximum is {maximum}",
            zone_id=module.params["zone_id"],
        )


def run(module, client):
    zone_id = module.params["zone_id"]
    page_rules = client.page_rules
    validate_field_names(module)
    targets = canonical_targets(module.params["targets"])
    current, rule_count = find_pagerule(module, client, targets)

    if module.params["state"] == "absent":
        ensure_resource_absent(
            module,
            "pagerule",
            "page rule",
            current,
            delete=lambda pagerule_id: page_rules.delete(pagerule_id=pagerule_id, zone_id=zone_id),
            context={"zone_id": zone_id},
            deleted_codes=(INVALID_PAGERULE_CODE,),
        )

    validate_priority(module, current, rule_count)
    payload = payload_from_params(module.params, FIELDS)
    # A null target or action field, at any level, counts as omitted, so it is not sent.
    payload["targets"] = without_nested_nulls(targets)
    current_actions = (
        [] if current is None else pagerule_list(module, current, "actions", "page rule action", {"zone_id": zone_id})
    )
    payload["actions"] = without_nested_nulls(ordered_actions(module.params["actions"], current_actions))
    if current is None:
        payload.setdefault("status", "active")

    ensure_resource_present(
        module,
        "pagerule",
        "page rule",
        current,
        payload,
        create=lambda payload: without_retries(client).page_rules.create(zone_id=zone_id, **payload),
        update=lambda pagerule_id, payload: page_rules.update(pagerule_id=pagerule_id, zone_id=zone_id, **payload),
        find_created=lambda: created_pagerules(client, zone_id, targets),
        preserved_fields=FIELDS,
        context={"zone_id": zone_id},
        comparable=lambda pagerule, failure: comparable_pagerule(module, pagerule, payload["actions"], failure),
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "actions": {"type": "list", "elements": "dict"},
            "targets": {"required": True, "type": "list", "elements": "dict"},
            "priority": {"type": "int"},
            "status": {
                "type": "str",
                "choices": ["active", "disabled"],
            },
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        required_if=[("state", "present", ["actions"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
