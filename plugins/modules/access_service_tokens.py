#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_service_tokens
short_description: Manage cloudflare access service tokens
description:
- Create, update, and delete Cloudflare Access service tokens.
- The module identifies service tokens by C(name) within an account.
author:
- Taylor Kimball (@tkimball83)
options:
  account_id:
    description:
    - Cloudflare account identifier.
    required: true
    type: str
  api_token:
    description:
    - Cloudflare API token with permissions to manage Access service tokens.
    required: true
    type: str
  name:
    description:
    - Name of the service token.
    required: true
    type: str
  duration:
    description:
    - Lifetime for the service token.
    - When omitted for C(state=present), the module does not manage the token duration.
    type: str
  state:
    description:
    - Desired state of the service token.
    type: str
    choices:
    - present
    - absent
    default: present
notes:
- Cloudflare only returns the client secret when a token is created.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Ensure a service token exists
  linuxhq.cloudflare.access_service_tokens:
    account_id: "{{ access_service_tokens_account_id }}"
    api_token: "{{ access_service_tokens_api_token }}"
    name: "{{ cloudflare_domain }}"
    duration: forever

- name: Ensure a service token is absent
  linuxhq.cloudflare.access_service_tokens:
    account_id: "{{ access_service_tokens_account_id }}"
    api_token: "{{ access_service_tokens_api_token }}"
    name: old-token
    state: absent
"""

RETURN = r"""
---
service_token:
  description: Cloudflare service token object after the requested operation.
  returned: when state is present or when the token existed before an absent operation
  type: dict
  sample:
    id: 023e105f4ecef8ad9ca31a8372d0c353
    name: example.com
message:
  description: Summary of the action taken.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    serialize_resource,
)


def create_service_token(client, account_id, params):
    payload = {"account_id": account_id, "name": params["name"]}
    if params.get("duration") is not None:
        payload["duration"] = params["duration"]

    return client.zero_trust.access.service_tokens.create(**payload)


def delete_service_token(client, account_id, token_id):
    return client.zero_trust.access.service_tokens.delete(
        token_id,
        account_id=account_id,
    )


def find_service_token(client, account_id, name):
    page = client.zero_trust.access.service_tokens.list(
        account_id=account_id,
        name=name,
    )
    for service_token in iter_service_tokens(page):
        if getattr(service_token, "name", None) == name:
            return service_token
    return None


def iter_service_tokens(page):
    result = getattr(page, "result", None)
    if result is not None:
        return result

    return page


def needs_update(current, params):
    if getattr(current, "name", None) != params["name"]:
        return True

    return not normalize_duration(current, params.get("duration"))


def normalize_duration(current, desired_duration):
    if desired_duration is None:
        return True

    current_duration = getattr(current, "duration", None)
    if current_duration is not None:
        return current_duration == desired_duration

    if desired_duration == "forever" and getattr(current, "expires_at", None) in (
        None,
        "",
    ):
        return True

    return False


def update_service_token(client, account_id, token_id, params):
    payload = {"account_id": account_id, "name": params["name"]}
    if params.get("duration") is not None:
        payload["duration"] = params["duration"]

    return client.zero_trust.access.service_tokens.update(
        token_id,
        **payload,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "duration": {"required": False, "type": "str"},
            "state": {
                "required": False,
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    account_id = params["account_id"]
    state = params["state"]

    with cloudflare_client(module) as client:
        current = find_service_token(client, account_id, params["name"])

        if state == "absent":
            if current is None:
                module.exit_json(changed=False, message="Service token already absent")

            current_dict = serialize_resource(current)
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Service token would be deleted",
                    service_token=current_dict,
                )

            delete_service_token(client, account_id, current.id)
            module.exit_json(
                changed=True,
                message="Service token deleted",
                service_token=current_dict,
            )

        if current is None:
            if module.check_mode:
                module.exit_json(changed=True, message="Service token would be created")

            service_token = create_service_token(client, account_id, params)
            module.exit_json(
                changed=True,
                message="Service token created",
                service_token=serialize_resource(service_token),
            )

        current_dict = serialize_resource(current)
        if not needs_update(current, params):
            module.exit_json(
                changed=False,
                message="Service token already present",
                service_token=current_dict,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Service token would be updated",
                service_token=current_dict,
            )

        service_token = update_service_token(
            client,
            account_id,
            current.id,
            params,
        )
        module.exit_json(
            changed=True,
            message="Service token updated",
            service_token=serialize_resource(service_token),
        )


if __name__ == "__main__":
    main()
