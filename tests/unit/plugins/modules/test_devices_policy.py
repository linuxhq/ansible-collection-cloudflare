# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_policy
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class DevicesPolicyTests(TestCase):
    def run_module(self, module, current=None, edited=None):
        client = Mock()
        api = client.zero_trust.devices.policies.default
        api.get.return_value = current
        api.edit.return_value = edited
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            devices_policy.run(module, client)

        return raised.exception.values, api

    def test_no_managed_fields_skips_api(self):
        result, api = self.run_module(FakeModule({"account_id": "account"}))

        api.get.assert_not_called()
        self.assertFalse(result["changed"])

    def test_equivalent_nested_policy_is_unchanged(self):
        result, api = self.run_module(
            FakeModule({"account_id": "account", "service_mode_v2": {"mode": "warp"}}),
            {"service_mode_v2": {"mode": "warp", "port": 0}, "allow_updates": True},
        )

        api.get.assert_called_once_with(account_id="account")
        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_patch_nested_change(self):
        result, api = self.run_module(
            FakeModule({"account_id": "account", "service_mode_v2": {"mode": "warp"}}, check_mode=True),
            {"service_mode_v2": {"mode": "proxy", "provider": "ignored"}},
        )

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_edits_changed_policy(self):
        result, api = self.run_module(
            FakeModule({"account_id": "account", "allow_updates": True}),
            {"allow_updates": False},
            {"allow_updates": True},
        )

        api.edit.assert_called_once_with(account_id="account", allow_updates=True)
        self.assertTrue(result["changed"])
        self.assertEqual(result["devices_policy"], {"allow_updates": True})

    def test_rejects_update_response_with_wrong_policy(self):
        result, _ignored = self.run_module(
            FakeModule({"account_id": "account", "service_mode_v2": {"mode": "warp"}}),
            {"service_mode_v2": {"mode": "proxy"}},
            {"service_mode_v2": {"mode": "proxy"}},
        )

        self.assertIn("did not apply", result["msg"])
