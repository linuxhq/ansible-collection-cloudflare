#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_identity_providers_info
short_description: Gather information about Cloudflare Access identity providers
description:
  - Gather Cloudflare Access identity providers for an account.
  - Results include sensitive values returned by Cloudflare, such as C(config.client_secret) and C(scim_config.secret); protect registered
    results and task output, for example with C(no_log).
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
"""

EXAMPLES = r"""
- name: Gather Access identity providers
  linuxhq.cloudflare.access_identity_providers_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
access_identity_providers:
  description: Cloudflare Access identity providers.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Identity provider identifier.
      returned: always
      type: str
    name:
      description: Identity provider name.
      returned: always
      type: str
    type:
      description: Identity provider type.
      returned: always
      type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    resource_list,
)


def run(module, client):
    account_id = module.params["account_id"]
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Access identity providers",
        account_id=account_id,
    ):
        providers = resource_list(
            module,
            client.zero_trust.identity_providers.list(account_id=account_id),
            "Access identity provider",
            required_fields=("id", "type"),
        )

    # Cloudflare allows an empty name, so only require a string without padding.
    for provider in providers:
        name = provider.get("name")
        if not isinstance(name, str) or name != name.strip():
            module.fail_json(msg="Cloudflare API returned malformed Access identity provider data")

    module.exit_json(
        changed=False,
        access_identity_providers=providers,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
