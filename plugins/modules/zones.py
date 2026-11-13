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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
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
      - Required when creating a zone.
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
      - Every setting is read before any change. A differing setting that
        Cloudflare reports as not editable, such as one the zone's plan does
        not include, fails before the zone or any setting is changed.
    suboptions:
      id:
        description:
          - Cloudflare zone setting identifier.
        required: true
        type: str
      value:
        description:
          - Desired zone setting value.
          - For object values, only the provided nested fields are compared.
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
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    find_resource,
    normalize_current_by_desired_fields,
    require_applied,
    resource_field,
    resource_id,
    select_fields,
    serialize_resource,
    values_differ,
)


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


def validate_settings(module):
    setting_ids = set()
    for setting in module.params.get("settings") or []:
        if not setting["id"].strip() or setting["id"] != setting["id"].strip() or setting["id"] in setting_ids:
            module.fail_json(msg="Each zone setting requires a unique valid id")

        setting_ids.add(setting["id"])


def find_zone(module, client):
    name = module.params["name"]
    account_id = module.params.get("account_id")
    query = {"name": name}
    context = {"name": name}
    if account_id is not None:
        query["account"] = {"id": account_id}
        context["account_id"] = account_id

    with cloudflare_error_context("Cloudflare API request failed while finding the zone", **context):
        return find_resource(module, client.zones.list(**query), "zone", "name", name)


def checked_zone(module, zone, payload, expected_id=None):
    zone = serialize_resource(zone)
    resource_id(module, zone, "zone", expected=expected_id)
    resource_field(module, zone, "name", "zone", expected=module.params["name"])
    require_applied(module, zone, payload, "zone")
    return zone


def edit_zone(module, client, zone_id, payload):
    with cloudflare_error_context(
        "Cloudflare API request failed while updating the zone",
        zone_id=zone_id,
    ):
        return checked_zone(module, client.zones.edit(zone_id=zone_id, **payload), payload, expected_id=zone_id)


def create_zone(module, client):
    params = module.params
    if params.get("account_id") is None:
        module.fail_json(msg="account_id is required when creating a zone")

    if module.check_mode:
        module.exit_json(changed=True, message="Zone would be created")

    payload = {
        "account": {"id": params["account_id"]},
        "name": params["name"],
        "type": params.get("type") or "full",
    }
    with cloudflare_error_context(
        "Cloudflare API request failed while creating the zone",
        account_id=params["account_id"],
        name=params["name"],
    ):
        return checked_zone(module, client.zones.create(**payload), payload)


def update_zone(module, client, zone):
    changed = False
    # Cloudflare edits only one zone property per request.
    for field in ("type", "vanity_name_servers"):
        if module.params.get(field) is None:
            continue

        payload = {field: module.params[field]}
        if not values_differ(select_fields(zone, payload), payload):
            continue

        if module.check_mode:
            module.exit_json(changed=True, message="Zone would be updated", zone=zone)

        zone = edit_zone(module, client, zone["id"], payload)
        changed = True

    return zone, changed


def setting_field(setting):
    if isinstance(setting, dict):
        for field in ("value", "enabled"):
            if field in setting:
                return field

    return None


def pending_settings(module, client, zone_id):
    """Return the requested settings that differ, with their current field.

    Every setting is read before any write, so a setting the zone's plan
    cannot edit fails before the zone or another setting changes.
    """
    pending = []
    for setting in module.params.get("settings") or []:
        setting_id = setting["id"]
        with cloudflare_error_context(
            "Cloudflare API request failed while gathering the zone setting",
            zone_id=zone_id,
            setting_id=setting_id,
        ):
            existing = serialize_resource(client.zones.settings.get(setting_id=setting_id, zone_id=zone_id))

        # Most settings hold a value; a few, such as ssl_recommender, an enabled flag.
        field = setting_field(existing)
        if field is None:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data")

        if setting_matches(existing[field], setting["value"]):
            continue

        if existing.get("editable") is False:
            module.fail_json(
                msg=f"Zone setting {setting_id} is not editable on this zone",
                zone_id=zone_id,
                setting_id=setting_id,
            )

        pending.append((setting, field))

    return pending


def update_settings(module, client, zone, pending):
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
        ):
            updated = serialize_resource(
                client.zones.settings.edit(setting_id=setting_id, zone_id=zone_id, **{field: setting["value"]})
            )

        resource_id(module, updated, "zone setting", expected=setting_id)
        if field not in updated:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data")

        if not setting_matches(updated[field], setting["value"]):
            module.fail_json(msg="Cloudflare did not apply the requested zone setting")

        updated_settings.append(updated)

    return updated_settings


def run(module, client):
    # DNS names are case-insensitive, and Cloudflare stores zone names in
    # lowercase without the root label's trailing dot.
    name = module.params["name"].lower()
    module.params["name"] = name.removesuffix(".")
    if not module.params["name"]:
        module.fail_json(msg="name must not be empty")

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
        )

    if current is None:
        zone = create_zone(module, client)
    else:
        zone = current
        resource_id(module, zone, "zone")

    pending = pending_settings(module, client, zone["id"])
    zone, changed = update_zone(module, client, zone)
    updated_settings = update_settings(module, client, zone, pending)
    if current is not None and not changed and not updated_settings:
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
