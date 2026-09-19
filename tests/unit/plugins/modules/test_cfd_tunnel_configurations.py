# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class CfdTunnelConfigurationsTests(TestCase):
    def test_ingress_access_required_is_applied_independently_of_global_access(self):
        access = {"required": True, "teamName": "example", "audTag": ["aud"]}
        desired = {
            "originRequest": {"access": access},
            "ingress": [
                {
                    "hostname": "app.example.com",
                    "service": "http://localhost:8080",
                    "originRequest": {"access": access},
                },
                {"service": "http_status:404"},
            ],
        }
        for local_access in (None, {"teamName": "example", "audTag": ["aud"]}):
            current = deepcopy(desired)
            current["ingress"][0]["originRequest"] = {} if local_access is None else {"access": local_access}
            original = deepcopy(current)
            for check_mode, applied in ((True, False), (False, False), (False, True)):
                module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": desired}, check_mode)
                with (
                    self.subTest(local_access=local_access, check_mode=check_mode, applied=applied),
                    patch.object(cfd_tunnel_configurations, "get_result", return_value={"config": current}),
                    patch.object(
                        cfd_tunnel_configurations,
                        "put_result",
                        return_value={"config": desired if applied else current},
                    ) as put,
                    self.assertRaises(ModuleExit if check_mode or applied else ModuleFail) as raised,
                ):
                    cfd_tunnel_configurations.ensure_present(module, {})

                if check_mode:
                    put.assert_not_called()
                else:
                    put.assert_called_once_with(
                        {}, "/accounts/account/cfd_tunnel/tunnel/configurations", {"config": desired}
                    )

                if check_mode or applied:
                    self.assertTrue(raised.exception.values["changed"])
                else:
                    self.assertIn("did not apply", raised.exception.values["msg"])

                self.assertEqual(current, original)

        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": desired})
        with (
            patch.object(cfd_tunnel_configurations, "get_result", return_value={"config": desired}),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        self.assertFalse(raised.exception.values["changed"])
        put.assert_not_called()

    def test_nested_provider_fields_do_not_cause_change(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {
            "config": {
                "provider_metadata": "ignored",
                "originRequest": {"future_default": True},
                "ingress": [{"service": "http_status:404", "provider_field": "ignored"}],
            }
        }
        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config})
        with (
            patch.object(cfd_tunnel_configurations, "get_result", return_value=current),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_update_tolerates_server_added_fields(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        returned = {
            "config": {
                "provider_metadata": {"version": 1},
                "originRequest": {"future_default": True},
                "ingress": [{"service": "http_status:404", "originRequest": {"future_default": "value"}}],
            }
        }
        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config})
        with (
            patch.object(cfd_tunnel_configurations, "get_result", return_value={"config": {}}),
            patch.object(cfd_tunnel_configurations, "put_result", return_value=returned),
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        self.assertTrue(raised.exception.values["changed"])

    def test_explicit_new_api_fields_are_compared(self):
        desired = {"ingress": [{"service": "http_status:404", "originRequest": {"future_option": True}}]}
        current = {"ingress": [{"service": "http_status:404", "originRequest": {"future_option": False}}]}
        self.assertNotEqual(
            cfd_tunnel_configurations.comparable_config(current, desired),
            cfd_tunnel_configurations.comparable_config(desired),
        )

    def test_returned_defaults_do_not_cause_change(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {
            "config": {
                "ingress": [{"service": "http_status:404", "hostname": "", "originRequest": {"noTLSVerify": False}}],
                "originRequest": {
                    "connectTimeout": 30,
                    "keepAliveTimeout": 90,
                    "bastionMode": False,
                    "proxyAddress": "127.0.0.1",
                    "proxyPort": 0,
                    "access": {"required": False, "audTag": [], "teamName": ""},
                },
                "warp-routing": {"enabled": False},
            }
        }
        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config})

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value=current,
            ),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_removed_origin_setting_is_updated_and_then_idempotent(self):
        config = {"ingress": [{"service": "https://localhost:443"}, {"service": "http_status:404"}]}
        current = {
            "config": {
                "ingress": [
                    {"service": "https://localhost:443", "originRequest": {"noTLSVerify": True}},
                    {"service": "http_status:404"},
                ]
            }
        }
        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config})
        with (
            patch.object(cfd_tunnel_configurations, "get_result", return_value=current),
            patch.object(cfd_tunnel_configurations, "put_result", return_value={"config": config}) as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        self.assertTrue(raised.exception.values["changed"])
        put.assert_called_once_with({}, "/accounts/account/cfd_tunnel/tunnel/configurations", {"config": config})
        with (
            patch.object(cfd_tunnel_configurations, "get_result", return_value={"config": config}),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        self.assertFalse(raised.exception.values["changed"])
        put.assert_not_called()

    def test_removal_is_predicted_and_postcondition_is_checked(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {"config": {**config, "originRequest": {"noTLSVerify": True}}}
        for check_mode in (True, False):
            module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config}, check_mode)
            with (
                self.subTest(check_mode=check_mode),
                patch.object(cfd_tunnel_configurations, "get_result", return_value=current),
                patch.object(cfd_tunnel_configurations, "put_result", return_value=current) as put,
                self.assertRaises(ModuleExit if check_mode else ModuleFail) as raised,
            ):
                cfd_tunnel_configurations.ensure_present(module, {})

            if check_mode:
                put.assert_not_called()
                self.assertTrue(raised.exception.values["changed"])
            else:
                self.assertIn("did not apply", raised.exception.values["msg"])

    def test_ingress_defaults_inherit_global_origin_settings(self):
        current = {
            "originRequest": {"noTLSVerify": True},
            "ingress": [{"service": "https://localhost:443", "originRequest": {"noTLSVerify": False}}],
        }
        desired = {"originRequest": {"noTLSVerify": True}, "ingress": [{"service": "https://localhost:443"}]}
        self.assertNotEqual(
            cfd_tunnel_configurations.comparable_config(current),
            cfd_tunnel_configurations.comparable_config(desired),
        )
        self.assertFalse(current["ingress"][0]["originRequest"]["noTLSVerify"])

    def test_check_mode_does_not_update(self):
        module = FakeModule(
            {"account_id": "account", "tunnel_id": "tunnel", "config": {"warp": True}},
            check_mode=True,
        )

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value={"config": {"warp": False}},
            ),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_unconfigured_tunnel_is_updated(self):
        module = FakeModule(
            {"account_id": "account", "tunnel_id": "tunnel", "config": {"warp": True}},
            check_mode=True,
        )

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value={"config": None},
            ),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_rejects_an_unmet_update_postcondition(self):
        module = FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": {"warp": True}})

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value={"config": {"warp": False}},
            ),
            patch.object(
                cfd_tunnel_configurations,
                "put_result",
                return_value={"config": {"warp": False}},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare did not apply the tunnel configuration",
        )
