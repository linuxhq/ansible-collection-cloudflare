#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_service_tokens
short_description: Manage Cloudflare Access service tokens
description:
  - Create, update, and delete Cloudflare Access service tokens.
  - The module identifies service tokens by O(name) within an account.
  - Creation may return a sensitive client secret; protect registered results and
    task output appropriately.
version_added: '2.0.0'
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
      - When omitted for O(state=present), the module does not manage the token duration.
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
  contains:
    id:
      description: Service token identifier.
      returned: always
      type: str
    name:
      description: Service token name.
      returned: always
      type: str
    client_id:
      description: Client identifier used to authenticate the service token.
      returned: when available
      type: str
    client_secret:
      description: Sensitive client secret returned only when created or rotated.
      returned: when provided by Cloudflare
      type: str
    duration:
      description: Configured service token lifetime.
      returned: when available
      type: str
message:
  description: Summary of the action taken.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    cloudflare_path,
    find_by_name,
    resource_field,
    resource_id,
    serialize_resource,
)


def service_token_payload(module):
    params = module.params
    payload = {"account_id": params["account_id"], "name": params["name"]}
    duration = params.get("duration")
    if duration is not None:
        payload["duration"] = duration

    return payload


def duration_matches(service_token, duration):
    if duration is None:
        return True
    current_duration = service_token.get("duration")
    if current_duration is not None:
        return current_duration == duration
    return duration == "forever" and service_token.get("expires_at") in (None, "")


def ensure_present(module, client):
    params = module.params

    current = find_by_name(
        client,
        cloudflare_path("accounts", params["account_id"], "access", "service_tokens"),
        params["name"],
    )

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Service token would be created")

        with cloudflare_error_context(
            "Cloudflare API request failed while creating a service token",
            account_id=params["account_id"],
            name=params["name"],
        ):
            service_token = serialize_resource(
                client.zero_trust.access.service_tokens.create(
                    **service_token_payload(module)
                )
            )
        resource_id(module, service_token, "service token")
        resource_field(
            module, service_token, "name", "service token", expected=params["name"]
        )
        if not duration_matches(service_token, params["duration"]):
            module.fail_json(
                msg="Cloudflare did not apply the requested service token duration"
            )
        module.exit_json(
            changed=True,
            message="Service token created",
            service_token=service_token,
        )

    current_id = resource_id(module, current, "service token")
    if duration_matches(current, params["duration"]):
        module.exit_json(
            changed=False,
            message="Service token already present",
            service_token=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Service token would be updated",
            service_token=current,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while updating a service token",
        account_id=params["account_id"],
        service_token_id=current_id,
    ):
        service_token = client.zero_trust.access.service_tokens.update(
            current_id,
            **service_token_payload(module),
        )
    service_token = serialize_resource(service_token)
    resource_id(module, service_token, "service token", expected=current_id)
    resource_field(
        module, service_token, "name", "service token", expected=params["name"]
    )
    if not duration_matches(service_token, params["duration"]):
        module.fail_json(
            msg="Cloudflare did not apply the requested service token duration"
        )
    module.exit_json(
        changed=True,
        message="Service token updated",
        service_token=service_token,
    )


def ensure_absent(module, client):
    params = module.params

    current = find_by_name(
        client,
        cloudflare_path("accounts", params["account_id"], "access", "service_tokens"),
        params["name"],
    )

    if current is None:
        module.exit_json(changed=False, message="Service token already absent")

    current_id = resource_id(module, current, "service token")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Service token would be deleted",
            service_token=current,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while deleting a service token",
        account_id=params["account_id"],
        service_token_id=current_id,
    ):
        deleted_token = serialize_resource(
            client.zero_trust.access.service_tokens.delete(
                current_id,
                account_id=params["account_id"],
            )
        )
    resource_id(module, deleted_token, "service token", expected=current_id)
    module.exit_json(
        changed=True,
        message="Service token deleted",
        service_token=current,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "duration": {"type": "str"},
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
