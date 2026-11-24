# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

import httpx

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    access_identity_providers_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    UNION_MISFIT,
    FakeModule,
    ModuleExit,
    ModuleFail,
    run_through_client,
)


def client_with(providers):
    client = Mock()
    client.zero_trust.identity_providers.list.return_value = iter(providers)
    return client


class AccessIdentityProvidersInfoTests(TestCase):
    def test_lists_providers_with_all_fields(self):
        client = client_with(
            [
                {
                    "id": "provider",
                    "name": "",
                    "type": "onetimepin",
                    "config": {
                        "client_id": "id",
                        "nested": [{"client_secret": "secret"}],
                    },
                    "scim_config": [{"secret": "secret"}],
                }
            ]
        )

        with self.assertRaises(ModuleExit) as raised:
            access_identity_providers_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.identity_providers.list.assert_called_once_with(account_id="account")
        self.assertEqual(
            raised.exception.values,
            {
                "changed": False,
                "access_identity_providers": [
                    {
                        "id": "provider",
                        "name": "",
                        "type": "onetimepin",
                        "config": {"client_id": "id", "nested": [{"client_secret": "secret"}]},
                        "scim_config": [{"secret": "secret"}],
                    }
                ],
            },
        )

    def test_returns_padded_name(self):
        providers = [{"id": "provider", "name": " idp", "type": "onetimepin"}]
        client = client_with(providers)

        with self.assertRaises(ModuleExit) as raised:
            access_identity_providers_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(raised.exception.values["access_identity_providers"], providers)

    def test_rejects_non_string_name(self):
        client = client_with([{"id": "provider", "name": None, "type": "onetimepin"}])

        with self.assertRaises(ModuleFail) as raised:
            access_identity_providers_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned malformed Access identity provider data",
        )
        self.assertEqual(raised.exception.values["account_id"], "account")

    def test_unconvertible_item_fails_cleanly(self):
        def respond(request):
            return httpx.Response(200, json={"success": True, "result": [UNION_MISFIT]})

        result, requests = run_through_client(
            access_identity_providers_info.run, FakeModule({"account_id": "account", "api_token": "token"}), respond
        )

        self.assertEqual([method for method, _path in requests], ["GET"])
        self.assertEqual(result["msg"], "Cloudflare API request failed while gathering Access identity providers")
        self.assertEqual(result["account_id"], "account")
        self.assertTrue(result["error"].startswith("RuntimeError: "))
        self.assertNotIn("changed", result)
