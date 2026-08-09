# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_policy_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class DevicesPolicyInfoTests(TestCase):
    def test_gets_policy(self):
        module = FakeModule({"account_id": "account"})
        policy = {"allow_updates": True}

        with (
            patch.object(devices_policy_info, "get_result", return_value=policy) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_policy_info.info(module, {})

        get.assert_called_once_with({}, "/accounts/account/devices/policy", default={})
        self.assertEqual(raised.exception.values["devices_policy"], policy)
        self.assertFalse(raised.exception.values["changed"])
