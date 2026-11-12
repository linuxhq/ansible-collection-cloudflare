# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    zerotrust_connectivity_settings,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    return {"account_id": "account", "icmp_proxy_enabled": False, "offramp_warp_enabled": False, **updates}


class ZeroTrustConnectivitySettingsTests(TestCase):
    def run_module(self, module, current, edited=None):
        client = Mock()
        api = client.zero_trust.connectivity_settings
        api.get.return_value = current
        api.edit.return_value = edited
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            zerotrust_connectivity_settings.run(module, client)

        return raised.exception.values, api

    def test_equivalent_settings_are_unchanged(self):
        result, api = self.run_module(
            FakeModule(params()), {"icmp_proxy_enabled": False, "offramp_warp_enabled": False}
        )

        api.get.assert_called_once_with(account_id="account")
        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_update(self):
        result, api = self.run_module(
            FakeModule(params(icmp_proxy_enabled=True), check_mode=True), {"icmp_proxy_enabled": False}
        )

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_edits_changed_settings(self):
        applied = {"icmp_proxy_enabled": True, "offramp_warp_enabled": False}
        result, api = self.run_module(
            FakeModule(params(icmp_proxy_enabled=True)), {"icmp_proxy_enabled": False}, applied
        )

        api.edit.assert_called_once_with(account_id="account", icmp_proxy_enabled=True, offramp_warp_enabled=False)
        self.assertEqual(result["connectivity_settings"], applied)

    def test_rejects_update_response_with_wrong_settings(self):
        result, _ignored = self.run_module(
            FakeModule(params(icmp_proxy_enabled=True)), {"icmp_proxy_enabled": False}, {"icmp_proxy_enabled": False}
        )

        self.assertIn("did not apply", result["msg"])
