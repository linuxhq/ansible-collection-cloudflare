# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

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


def settings(**updates):
    return {key: value for key, value in params(**updates).items() if key != "account_id"}


class DevicesSettingsTests(TestCase):
    def run_module(self, module, current, edited=None):
        client = Mock()
        api = client.zero_trust.devices.settings
        api.get.return_value = current
        api.edit.return_value = edited
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            devices_settings.run(module, client)

        return raised.exception.values, api

    def test_equivalent_settings_are_unchanged(self):
        result, api = self.run_module(FakeModule(params()), settings())

        api.get.assert_called_once_with(account_id="account")
        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_edit(self):
        result, api = self.run_module(FakeModule(params(gateway_proxy_enabled=True), check_mode=True), settings())

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_edits_changed_settings(self):
        result, api = self.run_module(
            FakeModule(params(gateway_proxy_enabled=True)), settings(), edited=settings(gateway_proxy_enabled=True)
        )

        api.edit.assert_called_once_with(account_id="account", **settings(gateway_proxy_enabled=True))
        self.assertTrue(result["changed"])

    def test_rejects_unapplied_settings(self):
        result, _ignored = self.run_module(
            FakeModule(params(gateway_proxy_enabled=True)), settings(), edited=settings()
        )

        self.assertIn("did not apply", result["msg"])

    def test_omitted_settings_are_left_unchanged(self):
        omitted = dict.fromkeys(settings(), None)
        current = settings(root_certificate_installation_enabled=True)
        module = FakeModule({"account_id": "account", **omitted, "gateway_proxy_enabled": True})

        result, api = self.run_module(module, current, edited={**current, "gateway_proxy_enabled": True})

        api.edit.assert_called_once_with(account_id="account", gateway_proxy_enabled=True)
        self.assertTrue(result["changed"])
