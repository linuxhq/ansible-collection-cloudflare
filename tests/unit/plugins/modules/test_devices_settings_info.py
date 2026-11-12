# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_settings_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class DevicesSettingsInfoTests(TestCase):
    def test_returns_settings(self):
        client = Mock()
        client.zero_trust.devices.settings.get.return_value = {"gateway_proxy_enabled": True}

        with self.assertRaises(ModuleExit) as raised:
            devices_settings_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.devices.settings.get.assert_called_once_with(account_id="account")
        self.assertEqual(raised.exception.values["devices_settings"], {"gateway_proxy_enabled": True})
