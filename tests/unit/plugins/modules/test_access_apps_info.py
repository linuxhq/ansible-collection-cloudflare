# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

import httpx

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    UNION_MISFIT,
    FakeModule,
    ModuleExit,
    ModuleFail,
    run_through_client,
)


class AccessAppsInfoTests(TestCase):
    def test_lists_apps_with_all_fields(self):
        client = Mock()
        client.zero_trust.access.applications.list.return_value = iter(
            [
                {
                    "id": "app-id",
                    "name": "app",
                    "saas_app": {"client_secret": "secret", "name": "example"},
                    "scim_config": {"authentication": {"client_secret": "secret", "method": "oauth"}},
                }
            ]
        )

        with self.assertRaises(ModuleExit) as raised:
            access_apps_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.access.applications.list.assert_called_once_with(account_id="account")
        values = raised.exception.values
        self.assertFalse(values["changed"])
        self.assertEqual(values["access_apps"][0]["saas_app"], {"client_secret": "secret", "name": "example"})

    def test_rejects_malformed_apps(self):
        client = Mock()
        client.zero_trust.access.applications.list.return_value = [{"id": "app-id"}]

        with self.assertRaises(ModuleFail) as raised:
            access_apps_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(raised.exception.values["account_id"], "account")

    def test_unconvertible_item_fails_cleanly(self):
        def respond(request):
            return httpx.Response(200, json={"success": True, "result": [UNION_MISFIT]})

        result, requests = run_through_client(
            access_apps_info.run, FakeModule({"account_id": "account", "api_token": "token"}), respond
        )

        self.assertEqual([method for method, _path in requests], ["GET"])
        self.assertEqual(result["msg"], "Cloudflare API request failed while gathering Access applications")
        self.assertEqual(result["account_id"], "account")
        self.assertTrue(result["error"].startswith("RuntimeError: "))
        self.assertNotIn("changed", result)
