#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: zones
short_description: Manage Cloudflare zones
description:
  - Create, update, delete Cloudflare zones, and manage zone settings.
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
  name:
    required: true
    type: str
    description:
      - Fully qualified domain name of the zone.
      - Matched case-insensitively.
      - A trailing dot is ignored, as Cloudflare stores the name without it.
  account_id:
    description:
      - Account identifier used when creating a zone.
      - When omitted on create, Cloudflare creates the zone in the account of
        the API token.
      - When provided, also limits the zone lookup to this account.
    type: str
  type:
    type: str
    choices:
      - full
      - partial
      - secondary
    description:
      - DNS setup type used by the zone.
      - Defaults to C(full) when creating a zone.
      - An existing zone's type is only changed when explicitly provided.
  vanity_name_servers:
    type: list
    elements: str
    description:
      - Custom authoritative name servers assigned to the zone.
  settings:
    type: list
    elements: dict
    description:
      - Zone settings to manage.
      - Every setting is read before the zone or any setting is changed. A
        differing setting that Cloudflare reports as not editable, such as one
        the zone's plan does not include, fails at that point.
      - Settings cannot be read before a zone exists, so a new zone is created
        first. Such a failure then leaves the new zone in place without its
        O(vanity_name_servers) or settings applied, and check mode cannot
        predict it.
    suboptions:
      id:
        description:
          - Cloudflare zone setting identifier.
          - V(.) and V(..) fail before any request.
          - When the zone is created, an id with leading or trailing
            whitespace fails before any change, because Cloudflare rejects it
            only when the setting is read after the zone is created.
        required: true
        type: str
      value:
        description:
          - Desired zone setting value.
          - For object values, only the provided nested fields are compared.
          - The object values of C(aegis), C(nel), and C(security_header)
            accept only the fields Cloudflare
            stores for them, such as C(enabled) of C(nel). Cloudflare accepts
            any other field but does not store it, so the module fails before
            making changes; a null other field is ignored, as Cloudflare drops
            it. Other values are not checked.
          - These values, and the C(strict_transport_security) value of
            C(security_header), must be mappings; any other value, such as
            V(on) for C(nel), fails before making changes.
          - An empty mapping at any level of these object values, such as
            V({}) for C(nel), fails before making changes, because Cloudflare
            accepts it but leaves the stored value unchanged.
          - A null value, or a null at any level of the object values above,
            such as a null C(enabled) of C(nel), fails before making changes,
            because Cloudflare either rejects it or stores a different value.
            A null C(pool_id) of C(aegis) is accepted; Cloudflare does not store
            it.
          - For settings Cloudflare exposes as an C(enabled) flag, such as
            C(ssl_recommender), the value sets that flag.
        required: true
        type: raw
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
- name: Ensure zone exists
  linuxhq.cloudflare.zones:
    api_token: "{{ cloudflare_api_token }}"
    account_id: "{{ account_id }}"
    name: example.com
    type: full

- name: Ensure zone settings are applied
  linuxhq.cloudflare.zones:
    api_token: "{{ cloudflare_api_token }}"
    account_id: "{{ account_id }}"
    name: example.com
    settings:
      - id: always_use_https
        value: "on"
      - id: min_tls_version
        value: "1.2"

- name: Ensure zone is absent
  linuxhq.cloudflare.zones:
    api_token: "{{ cloudflare_api_token }}"
    account_id: "{{ account_id }}"
    name: example.com
    state: absent
"""

RETURN = r"""
---
zone:
  description: Cloudflare zone.
  returned: when available
  type: dict
  contains:
    id:
      description: Cloudflare zone identifier.
      returned: always
      type: str
    name:
      description: Fully qualified domain name of the zone.
      returned: always
      type: str
    status:
      description: Current zone activation status.
      returned: when available
      type: str
    type:
      description: DNS setup type used by the zone.
      returned: when available
      type: str
settings:
  description: Updated zone settings.
  returned: when O(state=present) changed the zone or its settings, outside check mode
  type: list
  elements: dict
  contains:
    id:
      description: Zone setting identifier.
      returned: always
      type: str
    value:
      description: Updated zone setting value.
      returned: when the setting holds a value
      type: raw
    enabled:
      description: Updated flag of a setting Cloudflare exposes as enabled, such as C(ssl_recommender).
      returned: when the setting holds an enabled flag
      type: bool
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    DOT_SEGMENTS,
    INVALID_ZONE_CODE,
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    create_once,
    ensure_resource_absent,
    fail_not_applied,
    find_resource,
    matching_resources,
    normalize_current_by_desired_fields,
    require_applied,
    resource_field,
    resource_id,
    select_fields,
    serialize_resource,
    unsupported_fields,
    values_differ,
    without_retries,
)

# Fields of the setting values the cloudflare SDK types as objects, by setting
# id. Cloudflare accepts any other field but drops it.
SETTING_VALUE_FIELDS = {
    "aegis": ("enabled", "pool_id"),
    "nel": ("enabled",),
    "security_header": {
        "strict_transport_security": ("enabled", "include_subdomains", "max_age", "nosniff", "preload"),
    },
}
# Fields of the setting values above that Cloudflare accepts as null and does
# not store, so they match a stored value without them.
NULLABLE_SETTING_FIELDS = {"aegis": ("pool_id",)}


def setting_value_forms(value):
    """Return the string forms a scalar setting value matches."""
    if isinstance(value, bool):
        return {str(value).lower()}

    if isinstance(value, (int, float)):
        # The SDK decodes some integer settings, such as browser_cache_ttl, as
        # floats, while string settings, such as min_tls_version, keep "1.0".
        forms = {str(value), str(float(value))}
        if float(value).is_integer():
            forms.add(str(int(value)))

        return forms

    return {value}


def setting_values_equal(current, desired):
    if isinstance(current, dict) and isinstance(desired, dict):
        return current.keys() == desired.keys() and all(
            setting_values_equal(current[key], desired[key]) for key in current
        )

    if isinstance(current, (list, tuple)) and isinstance(desired, (list, tuple)):
        return len(current) == len(desired) and all(setting_values_equal(*pair) for pair in zip(current, desired))

    if isinstance(current, (dict, list, tuple)) or isinstance(desired, (dict, list, tuple)):
        return False

    return bool(setting_value_forms(current) & setting_value_forms(desired))


def setting_matches(current_value, desired_value):
    return setting_values_equal(normalize_current_by_desired_fields(current_value, desired_value), desired_value)


def empty_mappings(value, path):
    """Return the path of value and of each mapping nested in it that is empty."""
    if not isinstance(value, dict):
        return []

    if not value:
        return [path]

    return [found for key, item in value.items() for found in empty_mappings(item, f"{path}.{key}")]


def non_mappings(value, fields, path):
    """Return the path of value and of each value typed as an object in fields that is not a mapping.

    fields maps a key to the fields of its object value, as in
    SETTING_VALUE_FIELDS; null values are reported separately.
    """
    if value is None:
        return []

    if not isinstance(value, dict):
        return [path]

    if not isinstance(fields, dict):
        return []

    return [
        found
        for key, item in value.items()
        if key in fields
        for found in non_mappings(item, fields[key], f"{path}.{key}")
    ]


def null_values(value, path, fields=None):
    """Return the path of value and of each value nested in it that is null.

    fields lists the known keys of a mapping, as in SETTING_VALUE_FIELDS; a
    null value under another key is ignored, as Cloudflare drops it.
    """
    if value is None:
        return [path]

    if isinstance(value, dict):
        return [
            found
            for key, item in value.items()
            if fields is None or key in fields
            for found in null_values(item, f"{path}.{key}", fields.get(key) if isinstance(fields, dict) else None)
        ]

    if isinstance(value, list):
        return [found for index, item in enumerate(value) for found in null_values(item, f"{path}[{index}]")]

    return []


def validate_settings(module):
    setting_ids = set()
    unknown = []
    empty = []
    null = []
    not_mapping = []
    for index, setting in enumerate(module.params.get("settings") or []):
        if not setting["id"] or setting["id"] in setting_ids:
            module.fail_json(msg="Each zone setting requires a unique valid id")

        if setting["id"] in DOT_SEGMENTS:
            module.fail_json(msg="Each zone setting id must not be '.' or '..'", setting=setting["id"])

        setting_ids.add(setting["id"])
        path = f"settings[{index}].value"
        if setting["value"] is None:
            null.append(path)
        elif setting["id"] in SETTING_VALUE_FIELDS:
            nullable = {f"{path}.{field}" for field in NULLABLE_SETTING_FIELDS.get(setting["id"], ())}
            fields = SETTING_VALUE_FIELDS[setting["id"]]
            null.extend(found for found in null_values(setting["value"], path, fields) if found not in nullable)
            not_mapping.extend(non_mappings(setting["value"], fields, path))
            unknown.extend(unsupported_fields(setting["value"], fields, path))
            empty.extend(empty_mappings(setting["value"], path))

    # Cloudflare rejects a null value or stores a different one, such as false.
    if null:
        module.fail_json(
            msg=f"Cloudflare does not apply these null zone setting values: {', '.join(null)}",
            null_fields=null,
        )

    # Cloudflare rejects these, possibly after an earlier write in the same run.
    if not_mapping:
        module.fail_json(
            msg=f"These zone setting values must be mappings: {', '.join(not_mapping)}",
            invalid_fields=not_mapping,
        )

    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these zone setting fields: {', '.join(unknown)}",
            unsupported_fields=unknown,
        )

    # Cloudflare accepts an empty mapping but leaves the stored value unchanged.
    if empty:
        module.fail_json(
            msg=f"Cloudflare does not apply these empty zone setting values: {', '.join(empty)}",
            empty_fields=empty,
        )


def list_zones(module, client):
    """Return the zones named name, in account_id when it is set."""
    query = {"name": module.params["name"]}
    if module.params.get("account_id") is not None:
        query["account"] = {"id": module.params["account_id"]}

    return client.zones.list(**query)


def zone_context(module):
    """Return the zone's name, and its account_id when it is set, for failures."""
    context = {"name": module.params["name"]}
    if module.params.get("account_id") is not None:
        context["account_id"] = module.params["account_id"]

    return context


def find_zone(module, client):
    with cloudflare_error_context("Cloudflare API request failed while finding the zone", **zone_context(module)):
        return find_resource(
            module, list_zones(module, client), "zone", "name", module.params["name"], context=zone_context(module)
        )


def written_context(zone, changed, updated_settings=()):
    """Return the result fields a failure reports once this run has written to the zone, or {}.

    changed reports that the zone was created or updated; updated_settings
    lists the settings updated so far.
    """
    if not changed and not updated_settings:
        return {}

    return {"changed": True, "zone": zone, "settings": list(updated_settings)}


def checked_zone(module, zone, payload, expected_id=None, written=None):
    """Serialize and validate the zone a create or update returned.

    A failure reports changed=True, the zone, its id, and written, the
    result fields of earlier writes in this run.
    """
    zone = serialize_resource(zone)
    failure = {**(written or {}), **zone_context(module), "changed": True, "zone": zone}

    if expected_id is not None:
        failure["zone_id"] = expected_id

    failure = {"zone_id": resource_id(module, zone, "zone", expected=expected_id, context=failure), **failure}
    resource_field(module, zone, "name", "zone", expected=module.params["name"], context=failure)
    require_applied(module, zone, payload, "zone", context=failure)
    return zone


def edit_zone(module, client, zone, payload, written):
    """Edit one zone property; written holds the result fields of earlier writes, as in written_context."""
    with cloudflare_error_context(
        "Cloudflare API request failed while updating the zone",
        zone_id=zone["id"],
        **written,
    ):
        edited = client.zones.edit(zone_id=zone["id"], **payload)

    return checked_zone(module, edited, payload, expected_id=zone["id"], written=written)


def create_zone(module, client):
    params = module.params
    if module.check_mode:
        module.exit_json(changed=True, message="Zone would be created")

    payload = {"name": params["name"], "type": params.get("type") or "full"}
    if params.get("account_id") is not None:
        payload["account"] = {"id": params["account_id"]}

    with cloudflare_error_context("Cloudflare API request failed while creating the zone", **zone_context(module)):
        # The SDK requires an account; when it is omitted, Cloudflare uses the
        # account of the API token.
        zone = create_once(
            lambda: without_retries(client).zones.create(
                account=payload.get("account", cloudflare.omit), name=payload["name"], type=payload["type"]
            ),
            lambda: matching_resources(list_zones(module, client), "name", params["name"]),
        )

    return checked_zone(module, zone, payload)


def update_zone(module, client, zone, changed):
    """Update the zone's properties; changed reports that the zone was already created."""
    # Cloudflare edits only one zone property per request.
    for field in ("type", "vanity_name_servers"):
        if module.params.get(field) is None:
            continue

        payload = {field: module.params[field]}
        if not values_differ(select_fields(zone, payload), payload):
            continue

        if module.check_mode:
            module.exit_json(changed=True, message="Zone would be updated", zone=zone)

        zone = edit_zone(module, client, zone, payload, written_context(zone, changed))
        changed = True

    return zone, changed


def setting_field(setting):
    if isinstance(setting, dict):
        for field in ("value", "enabled"):
            if field in setting:
                return field

    return None


def pending_settings(module, client, zone, changed):
    """Return the requested settings that differ, with their current field.

    Every setting is read before the zone or any setting is updated, so a
    setting the zone's plan cannot edit fails first. A new zone has to be
    created before its settings can be read; changed reports that it was, so
    a failure reports the created zone.
    """
    zone_id = zone["id"]
    written = written_context(zone, changed)
    pending = []
    for setting in module.params.get("settings") or []:
        setting_id = setting["id"]
        context = {"zone_id": zone_id, "setting_id": setting_id, **written}
        with cloudflare_error_context("Cloudflare API request failed while gathering the zone setting", **context):
            existing = serialize_resource(client.zones.settings.get(setting_id=setting_id, zone_id=zone_id))

        # Most settings hold a value; a few, such as ssl_recommender, an enabled flag.
        field = setting_field(existing)
        if field is None:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data", **context)

        if setting_matches(existing[field], setting["value"]):
            continue

        if existing.get("editable") is False:
            module.fail_json(msg=f"Zone setting {setting_id} is not editable on this zone", **context)

        pending.append((setting, field))

    return pending


def update_settings(module, client, zone, pending, changed):
    """Update the pending settings; changed reports that the zone was already created or updated.

    A failure after a write in this run reports changed=True, the zone, and
    the settings updated so far, including one Cloudflare returned malformed
    or did not apply.
    """
    zone_id = zone["id"]
    updated_settings = []
    for setting, field in pending:
        setting_id = setting["id"]
        if module.check_mode:
            module.exit_json(changed=True, message="Zone settings would be updated", zone=zone)

        with cloudflare_error_context(
            "Cloudflare API request failed while updating the zone setting",
            zone_id=zone_id,
            setting_id=setting_id,
            **written_context(zone, changed, updated_settings),
        ):
            updated = serialize_resource(
                client.zones.settings.edit(setting_id=setting_id, zone_id=zone_id, **{field: setting["value"]})
            )

        context = {
            "zone_id": zone_id,
            "setting_id": setting_id,
            **written_context(zone, True, [*updated_settings, updated]),
        }
        resource_id(module, updated, "zone setting", expected=setting_id, context=context)
        if field not in updated:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data", **context)

        if not setting_matches(updated[field], setting["value"]):
            fail_not_applied(
                module,
                "zone setting",
                [
                    {
                        "field": setting_id,
                        "requested": setting["value"],
                        "stored": normalize_current_by_desired_fields(updated[field], setting["value"]),
                    }
                ],
                **context,
            )

        updated_settings.append(updated)

    return updated_settings


def run(module, client):
    # DNS names are case-insensitive, and Cloudflare stores zone names in
    # lowercase without the root label's trailing dot.
    name = module.params["name"].lower()
    module.params["name"] = name.removesuffix(".")
    if module.params["state"] == "present":
        validate_settings(module)

    current = find_zone(module, client)

    if module.params["state"] == "absent":
        ensure_resource_absent(
            module,
            "zone",
            "zone",
            current,
            delete=lambda zone_id: client.zones.delete(zone_id=zone_id),
            context=zone_context(module),
            deleted_codes=(INVALID_ZONE_CODE,),
        )

    if current is None:
        # Settings are read only after the zone is created, so Cloudflare
        # would reject a padded setting id after that write.
        padded = [
            setting["id"] for setting in module.params.get("settings") or [] if setting["id"] != setting["id"].strip()
        ]
        if padded:
            module.fail_json(msg="Zone setting ids must not contain leading or trailing whitespace", settings=padded)

        zone = create_zone(module, client)
    else:
        zone = current
        resource_id(module, zone, "zone", context=zone_context(module))

    pending = pending_settings(module, client, zone, current is None)
    zone, changed = update_zone(module, client, zone, current is None)
    updated_settings = update_settings(module, client, zone, pending, changed)
    if not changed and not updated_settings:
        module.exit_json(changed=False, message="Zone already present", zone=zone)

    module.exit_json(
        changed=True,
        message="Zone created" if current is None else "Zone updated",
        zone=zone,
        settings=updated_settings,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "account_id": {"type": "str"},
            "type": {
                "type": "str",
                "choices": ["full", "partial", "secondary"],
            },
            "vanity_name_servers": {"type": "list", "elements": "str"},
            "settings": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "id": {"required": True, "type": "str"},
                    "value": {"required": True, "type": "raw"},
                },
            },
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
