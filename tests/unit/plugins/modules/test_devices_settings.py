# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_settings
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "account_id": "account",
        "disable_for_time": 0,
        "gateway_proxy_enabled": False,
        "gateway_udp_proxy_enabled": False,
        "root_certificate_installation_enabled": False,
        "use_zt_virtual_ip": False,
    }
    values.update(updates)
    return values


class DevicesSettingsTests(TestCase):
    def test_equivalent_settings_are_unchanged(self):
        module = FakeModule(params())

        with (
            patch.object(devices_settings, "get_result", return_value=params()),
            patch.object(devices_settings, "patch_result") as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_settings.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_updates_changed_settings(self):
        module = FakeModule(params(gateway_proxy_enabled=True))
        updated = params(gateway_proxy_enabled=True)

        with (
            patch.object(devices_settings, "get_result", return_value=params()),
            patch.object(
                devices_settings,
                "patch_result",
                return_value=updated,
            ) as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_settings.ensure_present(module, {})

        patch_result.assert_called_once_with(
            {},
            "/accounts/account/devices/settings",
            {
                "disable_for_time": 0,
                "gateway_proxy_enabled": True,
                "gateway_udp_proxy_enabled": False,
                "root_certificate_installation_enabled": False,
                "use_zt_virtual_ip": False,
            },
        )
        self.assertEqual(raised.exception.values["devices_settings"], updated)

    def test_rejects_update_response_with_wrong_settings(self):
        module = FakeModule(params(gateway_proxy_enabled=True))

        with (
            patch.object(devices_settings, "get_result", return_value=params()),
            patch.object(devices_settings, "patch_result", return_value=params()),
            self.assertRaises(ModuleFail) as raised,
        ):
            devices_settings.ensure_present(module, {})

        self.assertIn("did not apply", raised.exception.values["msg"])
