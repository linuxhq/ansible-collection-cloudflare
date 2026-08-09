# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_settings_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class DevicesSettingsInfoTests(TestCase):
    def test_gets_settings(self):
        module = FakeModule({"account_id": "account"})
        settings = {"gateway_proxy_enabled": True}

        with (
            patch.object(
                devices_settings_info,
                "get_result",
                return_value=settings,
            ) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_settings_info.info(module, {})

        get.assert_called_once_with(
            {},
            "/accounts/account/devices/settings",
            default={},
        )
        self.assertEqual(raised.exception.values["devices_settings"], settings)
