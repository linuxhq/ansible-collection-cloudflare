# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import devices_policy
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class DevicesPolicyTests(TestCase):
    def test_no_managed_fields_skips_api(self):
        module = FakeModule({"account_id": "account"})

        with (
            patch.object(devices_policy, "get_result") as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_policy.ensure_present(module, {})

        get.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_check_mode_does_not_patch_nested_change(self):
        module = FakeModule(
            {"account_id": "account", "service_mode_v2": {"mode": "warp"}},
            check_mode=True,
        )
        current = {"service_mode_v2": {"mode": "proxy", "provider": "ignored"}}

        with (
            patch.object(devices_policy, "get_result", return_value=current),
            patch.object(devices_policy, "patch_result") as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            devices_policy.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
