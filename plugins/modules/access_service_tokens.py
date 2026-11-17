#!/usr/bin/python
# Copyright: Ansible Project
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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
  - linuxhq.cloudflare.cloudflare.create
options:
  name:
    description:
      - Name of the service token.
      - Cloudflare trims surrounding whitespace from the name, so a name with
        leading or trailing whitespace is not idempotent; each run creates
        another resource and then fails because Cloudflare returns the
        trimmed name.
      - An empty or whitespace-only name fails before any change, because
        Cloudflare does not store it.
    required: true
    type: str
  duration:
    description:
      - Lifetime for the service token, such as V(8760h), or V(forever) for a
        token that does not expire.
      - When omitted for O(state=present), the module does not manage the token duration;
        Cloudflare creates the token with a duration of V(8760h).
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
  - Cloudflare only returns the client secret when a token is created. A token found by name again after a failed
    create request is returned without it.
  - When a token is created but Cloudflare stores another name or duration, the failure includes the created token
    in C(service_token), with its client secret.
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
"""

EXAMPLES = r"""
- name: Ensure a service token exists
  linuxhq.cloudflare.access_service_tokens:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: automation
    duration: forever

- name: Ensure a service token is absent
  linuxhq.cloudflare.access_service_tokens:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: old-token
    state: absent
"""

RETURN = r"""
---
service_token:
  description:
    - Cloudflare service token after the requested operation.
    - With O(state=absent), the token as it was before deletion.
  returned: when available
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
      description: Sensitive client secret returned only when the token is created.
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
    create_once,
    ensure_resource_absent,
    fail_not_applied,
    find_resource,
    matching_resources,
    payload_from_params,
    resource_field,
    resource_id,
    serialize_resource,
    without_retries,
)


def duration_matches(service_token, duration):
    if duration is None:
        return True

    current_duration = service_token.get("duration")
    if current_duration is not None:
        return current_duration == duration

    return duration == "forever" and service_token.get("expires_at") in (None, "")


def checked_token(module, service_token, expected_id=None):
    """Serialize and validate the service token a create or update returned.

    A failure reports changed=True and includes the token, as a created
    token's client secret is returned only once.
    """
    service_token = serialize_resource(service_token)
    failure = {"changed": True, "account_id": module.params["account_id"], "service_token": service_token}
    if expected_id is not None:
        failure["resource_id"] = expected_id

    token_id = resource_id(module, service_token, "service token", expected=expected_id, context=failure)
    failure = {"resource_id": token_id, **failure}
    name = resource_field(module, service_token, "name", "service token", context=failure)
    if name != module.params["name"]:
        module.fail_json(msg="Cloudflare API returned the wrong service token", **failure)

    if not duration_matches(service_token, module.params["duration"]):
        fail_not_applied(
            module,
            "service token",
            [{"field": "duration", "requested": module.params["duration"], "stored": service_token.get("duration")}],
            **failure,
        )

    return service_token


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    service_tokens = client.zero_trust.access.service_tokens
    # Cloudflare stores an empty name as null, so the token is never found again.
    if params["state"] == "present" and not params["name"].strip():
        module.fail_json(msg="name must not be empty or only whitespace")

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the service token",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            service_tokens.list(account_id=account_id, name=params["name"]),
            "service token",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "service_token",
            "service token",
            current,
            delete=lambda token_id: service_tokens.delete(token_id, account_id=account_id),
            context={"account_id": account_id},
        )

    payload = payload_from_params(params, ("duration", "name"))

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Service token would be created")

        with cloudflare_error_context(
            "Cloudflare API request failed while creating the service token",
            account_id=account_id,
            name=params["name"],
        ):
            service_token = create_once(
                lambda: without_retries(client).zero_trust.access.service_tokens.create(
                    account_id=account_id, **payload
                ),
                lambda: matching_resources(
                    service_tokens.list(account_id=account_id, name=params["name"]), "name", params["name"]
                ),
            )

        # The client secret is only returned on creation and is part of the result.
        module.exit_json(
            changed=True,
            message="Service token created",
            service_token=checked_token(module, service_token),
        )

    current_id = resource_id(module, current, "service token")
    if duration_matches(current, params["duration"]):
        module.exit_json(changed=False, message="Service token already present", service_token=current)

    if module.check_mode:
        module.exit_json(changed=True, message="Service token would be updated", service_token=current)

    with cloudflare_error_context(
        "Cloudflare API request failed while updating the service token",
        account_id=account_id,
        resource_id=current_id,
    ):
        service_token = service_tokens.update(current_id, account_id=account_id, **payload)

    module.exit_json(
        changed=True,
        message="Service token updated",
        service_token=checked_token(module, service_token, expected_id=current_id),
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
        run(module, client)


if __name__ == "__main__":
    main()
