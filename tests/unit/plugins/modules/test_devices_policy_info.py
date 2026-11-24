# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

import httpx

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_policy_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    UNION_MISFIT,
    FakeModule,
    ModuleExit,
    run_through_client,
)


class DevicesPolicyInfoTests(TestCase):
    def test_gets_policy(self):
        client = Mock()
        api = client.zero_trust.devices.policies.default
        api.get.return_value = {"allow_updates": True}

        with self.assertRaises(ModuleExit) as raised:
            devices_policy_info.run(FakeModule({"account_id": "account"}), client)

        api.get.assert_called_once_with(account_id="account")
        self.assertEqual(raised.exception.values, {"changed": False, "devices_policy": {"allow_updates": True}})

    def test_unserializable_policy_fails_naming_the_read(self):
        # The SDK builds the policy, but fails to serialize a route that fits no split tunnel type.
        def respond(request):
            return httpx.Response(200, json={"success": True, "result": {"exclude": [UNION_MISFIT]}})

        result, requests = run_through_client(
            devices_policy_info.run, FakeModule({"account_id": "account", "api_token": "token"}), respond
        )

        self.assertEqual([method for method, _path in requests], ["GET"])
        self.assertEqual(result["msg"], "Cloudflare API request failed while gathering the device policy")
        self.assertEqual(result["account_id"], "account")
        self.assertTrue(result["error"].startswith("TypeError: "))
        self.assertNotIn("changed", result)
