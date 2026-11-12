# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_policy_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
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
