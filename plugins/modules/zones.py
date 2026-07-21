#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: zones
short_description: Manage cloudflare zones
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
    description:
      - Resource type.
      - Defaults to C(full) when creating a zone.
      - An existing zone's type is only changed when explicitly provided.
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
  - cloudflare >= 5.5.0, < 6

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
    get_result,
    patch_result,
    post_result,
    select_fields,
    values_differ,
)


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


def zone_endpoint(zone_id=None):
    if zone_id is None:
        return "/zones"
    return "/zones/%s" % zone_id


def ensure_present(module, client):
    params = module.params

    current = None
    zones = get_result(
        client, "/zones?name=%s&per_page=50" % params["name"], default=[]
    )

    for zone in zones:
        if zone.get("name") == params["name"]:
            current = zone
            break

    if current is None:
        if params.get("account_id") is None:
            module.fail_json(msg="account_id is required when creating a zone")

        if module.check_mode:
            module.exit_json(changed=True, message="Zone would be created")

        current = post_result(
            client,
            zone_endpoint(),
            {
                "account": {"id": params["account_id"]},
                "name": params["name"],
                "type": params.get("type") or "full",
            },
        )

        if params.get("vanity_name_servers") is not None:
            current = patch_result(
                client,
                zone_endpoint(current["id"]),
                {"vanity_name_servers": params["vanity_name_servers"]},
            )

        changed = True
    else:
        payloads = []
        if params.get("type") is not None:
            payloads.append({"type": params["type"]})
        if params.get("vanity_name_servers") is not None:
            payloads.append({"vanity_name_servers": params["vanity_name_servers"]})

        changed = False
        for payload in payloads:
            if not values_differ(select_fields(current, payload.keys()), payload):
                continue

            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Zone would be updated",
                    zone=current,
                )

            current = patch_result(client, zone_endpoint(current["id"]), payload)
            changed = True

    updated_settings = []
    for setting in params.get("settings") or []:
        if setting.get("id") is None or "value" not in setting:
            module.fail_json(msg="Each zone setting requires id and value")
        existing = get_result(
            client,
            settings_endpoint(current["id"], setting["id"]),
            default={},
        )

        if normalize_setting_value(existing.get("value")) == normalize_setting_value(
            setting["value"]
        ):
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
        module.exit_json(changed=False, message="Zone already present", zone=current)

    module.exit_json(
        changed=True,
        message="Zone updated",
        zone=current,
        settings=updated_settings,
    )


def ensure_absent(module, client):
    params = module.params

    current = None
    zones = get_result(
        client, "/zones?name=%s&per_page=50" % params["name"], default=[]
    )

    for zone in zones:
        if zone.get("name") == params["name"]:
            current = zone
            break

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
            "settings": {"type": "list", "elements": "dict"},
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
