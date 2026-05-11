#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: zones
short_description: Manage Cloudflare zones
description:
- Create, update, delete Cloudflare zones, and manage zone settings.
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
    - Resource name.
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
    - internal
    default: full
    description:
    - Resource type.
  vanity_name_servers:
    type: list
    elements: str
    description:
    - Vanity name servers.
  settings:
    type: list
    elements: dict
    description:
    - Zone settings to manage.
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
- cloudflare >= 4.3.1, < 5

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
settings:
  description: Updated zone settings.
  returned: when settings changed
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
    delete_result,
    find_zone_by_name,
    get_result,
    patch_result,
    post_result,
    selected_values_differ,
)


def create_payload(params):
    return {
        "account": {"id": params["account_id"]},
        "name": params["name"],
        "type": params["type"],
    }


def settings_endpoint(zone_id, setting_id):
    return "/zones/%s/settings/%s" % (zone_id, setting_id)


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


def setting_values_match(current, desired):
    return normalize_setting_value(current) == normalize_setting_value(desired)


def update_payload(params):
    payload = {"type": params["type"]}
    if params.get("vanity_name_servers") is not None:
        payload["vanity_name_servers"] = params["vanity_name_servers"]
    return payload


def zone_endpoint(zone_id=None):
    if zone_id is None:
        return "/zones"
    return "/zones/%s" % zone_id


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "account_id": {"type": "str"},
            "type": {
                "type": "str",
                "choices": ["full", "partial", "secondary", "internal"],
                "default": "full",
            },
            "vanity_name_servers": {"type": "list", "elements": "str"},
            "settings": {"type": "list", "elements": "dict"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    with cloudflare_client(module) as client:
        current = find_zone_by_name(client, params["name"])

        if params["state"] == "absent":
            if current is None:
                module.exit_json(changed=False, message="Zone already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Zone would be deleted",
                    zone=current,
                )
            delete_result(client, zone_endpoint(current["id"]))
            module.exit_json(changed=True, message="Zone deleted", zone=current)

        if current is None:
            if params.get("account_id") is None:
                module.fail_json(msg="account_id is required when creating a zone")
            if module.check_mode:
                module.exit_json(changed=True, message="Zone would be created")
            current = post_result(client, zone_endpoint(), create_payload(params))
            changed = True
        else:
            payload = update_payload(params)
            changed = selected_values_differ(current, payload, tuple(payload.keys()))
            if changed:
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        message="Zone would be updated",
                        zone=current,
                    )
                current = patch_result(client, zone_endpoint(current["id"]), payload)

        updated_settings = []
        for setting in params.get("settings") or []:
            if setting.get("id") is None or "value" not in setting:
                module.fail_json(msg="Each zone setting requires id and value")
            existing = get_result(
                client,
                settings_endpoint(current["id"], setting["id"]),
                default={},
            )
            if setting_values_match(existing.get("value"), setting["value"]):
                continue
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Zone settings would be updated",
                    zone=current,
                )
            updated_settings.append(
                patch_result(
                    client,
                    settings_endpoint(current["id"], setting["id"]),
                    {"value": setting["value"]},
                )
            )

        if not changed and not updated_settings:
            module.exit_json(
                changed=False, message="Zone already present", zone=current
            )

        module.exit_json(
            changed=True,
            message="Zone updated",
            zone=current,
            settings=updated_settings,
        )


if __name__ == "__main__":
    main()
