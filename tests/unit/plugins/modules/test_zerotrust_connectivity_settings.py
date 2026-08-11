# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    zerotrust_connectivity_settings,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class ZeroTrustConnectivitySettingsTests(TestCase):
    def test_equivalent_settings_are_unchanged(self):
        module = FakeModule(
            {
                "account_id": "account",
                "icmp_proxy_enabled": False,
                "offramp_warp_enabled": False,
            }
        )

        with (
            patch.object(
                zerotrust_connectivity_settings,
                "get_result",
                return_value={
                    "icmp_proxy_enabled": False,
                    "offramp_warp_enabled": False,
                },
            ),
            patch.object(
                zerotrust_connectivity_settings,
                "patch_result",
            ) as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            zerotrust_connectivity_settings.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_check_mode_does_not_update(self):
        module = FakeModule(
            {
                "account_id": "account",
                "icmp_proxy_enabled": True,
                "offramp_warp_enabled": False,
            },
            check_mode=True,
        )

        with (
            patch.object(
                zerotrust_connectivity_settings,
                "get_result",
                return_value={"icmp_proxy_enabled": False},
            ),
            patch.object(
                zerotrust_connectivity_settings,
                "patch_result",
            ) as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            zerotrust_connectivity_settings.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_rejects_update_response_with_wrong_settings(self):
        module = FakeModule(
            {
                "account_id": "account",
                "icmp_proxy_enabled": True,
                "offramp_warp_enabled": False,
            }
        )

        with (
            patch.object(
                zerotrust_connectivity_settings,
                "get_result",
                return_value={"icmp_proxy_enabled": False},
            ),
            patch.object(
                zerotrust_connectivity_settings,
                "patch_result",
                return_value={"icmp_proxy_enabled": False},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            zerotrust_connectivity_settings.ensure_present(module, {})

        self.assertIn("did not apply", raised.exception.values["msg"])
