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
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  name:
    required: true
    type: str
    description:
      - Fully qualified domain name of the zone.
  account_id:
    description:
      - Account identifier used when creating a zone.
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
    suboptions:
      id:
        description:
          - Cloudflare zone setting identifier.
        required: true
        type: str
      value:
        description:
          - Desired zone setting value.
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
  returned: when the zone or its settings changed
  type: list
  elements: dict
  contains:
    id:
      description: Zone setting identifier.
      returned: always
      type: str
    value:
      description: Updated zone setting value.
      returned: always
      type: raw
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
    find_by_name,
    get_result,
    patch_result,
    post_result,
    resource_field,
    resource_id,
    select_fields,
    validate_requested_values,
    values_differ,
)


def settings_endpoint(zone_id, setting_id):
    return cloudflare_path("zones", zone_id, "settings", setting_id)


def normalize_setting_value(value):
    if isinstance(value, dict):
        return {key: normalize_setting_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [normalize_setting_value(item) for item in value]

    if isinstance(value, bool):
        return str(value).lower()

    if isinstance(value, (int, float)):
        return str(value)

    return value


def zone_endpoint(zone_id=None):
    if zone_id is None:
        return cloudflare_path("zones")
    return cloudflare_path("zones", zone_id)


def ensure_present(module, client):
    params = module.params

    setting_ids = set()
    for setting in params.get("settings") or []:
        if (
            not isinstance(setting.get("id"), str)
            or not setting["id"].strip()
            or setting["id"] != setting["id"].strip()
            or "value" not in setting
            or setting["id"] in setting_ids
        ):
            module.fail_json(msg="Each zone setting requires a unique valid id and value")
        setting_ids.add(setting["id"])

    current = find_by_name(
        client,
        zone_endpoint(),
        params["name"],
        paginate=False,
    )

    if current is None:
        if params.get("account_id") is None:
            module.fail_json(msg="account_id is required when creating a zone")

        if module.check_mode:
            module.exit_json(changed=True, message="Zone would be created")

        payload = {
            "account": {"id": params["account_id"]},
            "name": params["name"],
            "type": params.get("type") or "full",
        }
        current = post_result(client, zone_endpoint(), payload)
        current_id = resource_id(module, current, "zone")
        resource_field(module, current, "name", "zone", expected=params["name"])
        validate_requested_values(module, current, payload, "zone")

        if params.get("vanity_name_servers") is not None:
            current = patch_result(
                client,
                zone_endpoint(current_id),
                {"vanity_name_servers": params["vanity_name_servers"]},
            )
            current_id = resource_id(module, current, "zone", expected=current_id)
            resource_field(module, current, "name", "zone", expected=params["name"])
            validate_requested_values(
                module,
                current,
                {"vanity_name_servers": params["vanity_name_servers"]},
                "zone",
            )

        changed = True
        created = True
    else:
        current_id = resource_id(module, current, "zone")
        payload = {field: params[field] for field in ("type", "vanity_name_servers") if params.get(field) is not None}
        changed = False
        if payload and values_differ(select_fields(current, payload.keys()), payload):
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Zone would be updated",
                    zone=current,
                )

            current = patch_result(client, zone_endpoint(current_id), payload)
            current_id = resource_id(module, current, "zone", expected=current_id)
            resource_field(module, current, "name", "zone", expected=params["name"])
            validate_requested_values(module, current, payload, "zone")
            changed = True
        created = False

    updated_settings = []
    for setting in params.get("settings") or []:
        existing = get_result(
            client,
            settings_endpoint(current_id, setting["id"]),
            default={},
        )
        if not isinstance(existing, dict) or "value" not in existing:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data")

        if normalize_setting_value(existing.get("value")) == normalize_setting_value(setting["value"]):
            continue

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Zone settings would be updated",
                zone=current,
            )

        updated_setting = patch_result(
            client,
            settings_endpoint(current_id, setting["id"]),
            {"value": setting["value"]},
        )
        resource_id(module, updated_setting, "zone setting", expected=setting["id"])
        if "value" not in updated_setting:
            module.fail_json(msg="Cloudflare API returned malformed zone setting data")
        if normalize_setting_value(updated_setting["value"]) != normalize_setting_value(setting["value"]):
            module.fail_json(msg="Cloudflare did not apply the requested zone setting")
        updated_settings.append(updated_setting)

    if not changed and not updated_settings:
        module.exit_json(changed=False, message="Zone already present", zone=current)

    module.exit_json(
        changed=True,
        message="Zone created" if created else "Zone updated",
        zone=current,
        settings=updated_settings,
    )


def ensure_absent(module, client):
    params = module.params

    current = find_by_name(
        client,
        zone_endpoint(),
        params["name"],
        paginate=False,
    )

    if current is None:
        module.exit_json(changed=False, message="Zone already absent")

    current_id = resource_id(module, current, "zone")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Zone would be deleted",
            zone=current,
        )

    delete_result(client, zone_endpoint(current_id), expected_id=current_id)
    module.exit_json(changed=True, message="Zone deleted", zone=current)


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
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
