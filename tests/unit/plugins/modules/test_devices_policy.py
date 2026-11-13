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

    def test_no_managed_fields_returns_current_policy(self):
        current = {"allow_updates": True}
        result, api = self.run_module(FakeModule({"account_id": "account"}), current=current)

        api.get.assert_called_once_with(account_id="account")
        api.edit.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["devices_policy"], current)

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

    def test_split_tunnel_entries_are_compared_exactly(self):
        for field in ("include", "exclude"):
            desired = [{"address": "192.0.2.0/24"}]
            current = {field: [{"address": "192.0.2.0/24", "description": "removed"}]}
            for check_mode in (True, False):
                with self.subTest(field=field, check_mode=check_mode):
                    result, api = self.run_module(
                        FakeModule({"account_id": "account", field: desired}, check_mode=check_mode),
                        current,
                        {field: desired},
                    )

                    self.assertTrue(result["changed"])
                    if check_mode:
                        api.edit.assert_not_called()
                    else:
                        api.edit.assert_called_once_with(account_id="account", **{field: desired})

            with self.subTest(field=field, applied=False):
                result, _ignored = self.run_module(
                    FakeModule({"account_id": "account", field: desired}), current, current
                )

                self.assertIn("did not apply", result["msg"])

            with self.subTest(field=field, converged=True):
                result, api = self.run_module(FakeModule({"account_id": "account", field: desired}), {field: desired})

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_empty_include_fails_before_any_request(self):
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                result, api = self.run_module(
                    FakeModule({"account_id": "account", "include": []}, check_mode=check_mode),
                    {"include": [{"address": "192.0.2.0/24"}]},
                )

                api.get.assert_not_called()
                api.edit.assert_not_called()
                self.assertIn("exclude: []", result["msg"])

    def test_empty_exclude_is_sent(self):
        result, api = self.run_module(
            FakeModule({"account_id": "account", "exclude": []}),
            {"exclude": [{"address": "192.0.2.0/24"}]},
            {"exclude": []},
        )

        api.edit.assert_called_once_with(account_id="account", exclude=[])
        self.assertTrue(result["changed"])

    def test_bare_ip_addresses_match_stored_cidr(self):
        requested = [
            {"address": "192.0.2.1", "description": "v4"},
            {"address": "2001:db8::1"},
            {"address": "198.51.100.7/24"},
            {"host": "Example.COM"},
        ]
        stored = [
            {"address": "192.0.2.1/32", "description": "v4"},
            {"address": "2001:db8::1/128"},
            {"address": "198.51.100.7/24"},
            {"host": "Example.COM"},
        ]
        for field in ("include", "exclude"):
            with self.subTest(field=field, converged=True):
                result, api = self.run_module(FakeModule({"account_id": "account", field: requested}), {field: stored})

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

            with self.subTest(field=field, converged=False):
                result, api = self.run_module(
                    FakeModule({"account_id": "account", field: requested}), {field: []}, {field: stored}
                )

                api.edit.assert_called_once_with(account_id="account", **{field: stored})
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)
