# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

REMOTE_TUNNEL = {"id": "tunnel", "config_src": "cloudflare", "remote_config": True}


def module_for(config, check_mode=False):
    return FakeModule({"account_id": "account", "tunnel_id": "tunnel", "config": config}, check_mode)


class CfdTunnelConfigurationsTests(TestCase):
    def run_module(self, module, current, updated=None):
        client = Mock()
        client.zero_trust.tunnels.cloudflared.get.return_value = REMOTE_TUNNEL
        api = client.zero_trust.tunnels.cloudflared.configurations
        api.get.return_value = current
        api.update.return_value = updated
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            cfd_tunnel_configurations.run(module, client)

        api.get.assert_called_once_with("tunnel", account_id="account")
        return raised.exception, api

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
                with self.subTest(local_access=local_access, check_mode=check_mode, applied=applied):
                    raised, api = self.run_module(
                        module_for(desired, check_mode),
                        {"config": current},
                        {"config": desired if applied else current},
                    )

                    if check_mode:
                        api.update.assert_not_called()
                    else:
                        api.update.assert_called_once_with("tunnel", account_id="account", config=desired)

                    if check_mode or applied:
                        self.assertIsInstance(raised, ModuleExit)
                        self.assertTrue(raised.values["changed"])
                    else:
                        self.assertIsInstance(raised, ModuleFail)
                        self.assertIn("did not apply", raised.values["msg"])

                    self.assertEqual(current, original)

        raised, api = self.run_module(module_for(desired), {"config": desired})

        self.assertFalse(raised.values["changed"])
        api.update.assert_not_called()

    def test_nested_provider_fields_do_not_cause_change(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {
            "config": {
                "provider_metadata": "ignored",
                "originRequest": {"future_default": True},
                "ingress": [{"service": "http_status:404", "provider_field": "ignored"}],
            }
        }

        raised, api = self.run_module(module_for(config), current)

        api.update.assert_not_called()
        self.assertFalse(raised.values["changed"])

    def test_update_tolerates_server_added_fields(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        returned = {
            "config": {
                "provider_metadata": {"version": 1},
                "originRequest": {"future_default": True},
                "ingress": [{"service": "http_status:404", "originRequest": {"future_default": "value"}}],
            }
        }

        raised, _ignored = self.run_module(module_for(config), {"config": {}}, returned)

        self.assertIsInstance(raised, ModuleExit)
        self.assertTrue(raised.values["changed"])

    def test_explicit_new_api_fields_are_compared(self):
        desired = {"ingress": [{"service": "http_status:404", "originRequest": {"future_option": True}}]}
        current = {"ingress": [{"service": "http_status:404", "originRequest": {"future_option": False}}]}
        self.assertNotEqual(
            cfd_tunnel_configurations.comparable_config(current, desired),
            cfd_tunnel_configurations.comparable_config(desired),
        )

    def test_warp_routing_is_not_compared(self):
        config = {"ingress": [{"service": "http_status:404"}], "warp-routing": {"enabled": True}}
        current = {"config": {"ingress": [{"service": "http_status:404"}], "warp-routing": {"enabled": False}}}

        raised, api = self.run_module(module_for(config), current)

        api.update.assert_not_called()
        self.assertFalse(raised.values["changed"])

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

        raised, api = self.run_module(module_for(config), current)

        api.update.assert_not_called()
        self.assertFalse(raised.values["changed"])

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

        raised, api = self.run_module(module_for(config), current, {"config": config})

        self.assertTrue(raised.values["changed"])
        api.update.assert_called_once_with("tunnel", account_id="account", config=config)

        raised, api = self.run_module(module_for(config), {"config": config})

        self.assertFalse(raised.values["changed"])
        api.update.assert_not_called()

    def test_removal_is_predicted_and_postcondition_is_checked(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {"config": {**config, "originRequest": {"noTLSVerify": True}}}
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                raised, api = self.run_module(module_for(config, check_mode), current, current)

                if check_mode:
                    api.update.assert_not_called()
                    self.assertTrue(raised.values["changed"])
                else:
                    self.assertIn("did not apply", raised.values["msg"])

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

    def test_sdk_origin_request_spelling_fails_before_any_request(self):
        origin = {"no_tls_verify": True}
        for config in (
            {"origin_request": origin, "ingress": [{"service": "http_status:404"}]},
            {
                "ingress": [
                    {"hostname": "app.example.com", "service": "http://localhost", "origin_request": origin},
                    {"service": "http_status:404"},
                ]
            },
        ):
            for check_mode in (False, True):
                with self.subTest(config=config, check_mode=check_mode):
                    client = Mock()
                    with self.assertRaises(ModuleFail) as raised:
                        cfd_tunnel_configurations.run(module_for(config, check_mode), client)

                    self.assertIn("'originRequest'", raised.exception.values["msg"])
                    self.assertEqual(client.mock_calls, [])

    def test_check_mode_does_not_update(self):
        raised, api = self.run_module(module_for({"warp": True}, check_mode=True), {"config": {"warp": False}})

        api.update.assert_not_called()
        self.assertTrue(raised.values["changed"])

    def test_unconfigured_tunnel_is_updated(self):
        for current in ({"config": None}, None):
            with self.subTest(current=current):
                raised, api = self.run_module(module_for({"warp": True}, check_mode=True), current)

                api.update.assert_not_called()
                self.assertTrue(raised.values["changed"])

    def test_rejects_an_unmet_update_postcondition(self):
        raised, _ignored = self.run_module(
            module_for({"warp": True}), {"config": {"warp": False}}, {"config": {"warp": False}}
        )

        self.assertEqual(raised.values["msg"], "Cloudflare did not apply the tunnel configuration")

    def test_locally_managed_tunnel_fails_before_any_change(self):
        for tunnel in (
            {"id": "tunnel", "config_src": "local", "remote_config": False},
            {"id": "tunnel", "config_src": "local"},
            {"id": "tunnel", "remote_config": False},
        ):
            for check_mode in (False, True):
                with self.subTest(tunnel=tunnel, check_mode=check_mode):
                    client = Mock()
                    tunnels = client.zero_trust.tunnels.cloudflared
                    tunnels.get.return_value = tunnel
                    with self.assertRaises(ModuleFail) as raised:
                        cfd_tunnel_configurations.run(module_for({"warp": True}, check_mode), client)

                    tunnels.get.assert_called_once_with("tunnel", account_id="account")
                    tunnels.configurations.get.assert_not_called()
                    tunnels.configurations.update.assert_not_called()
                    self.assertEqual(
                        raised.exception.values["msg"],
                        "Cloudflared tunnel tunnel is locally managed and cannot use a remote configuration",
                    )
                    self.assertEqual(raised.exception.values["tunnel_id"], "tunnel")

    def test_rejects_wrong_tunnel(self):
        client = Mock()
        client.zero_trust.tunnels.cloudflared.get.return_value = {**REMOTE_TUNNEL, "id": "other"}
        with self.assertRaises(ModuleFail) as raised:
            cfd_tunnel_configurations.run(module_for({"warp": True}), client)

        client.zero_trust.tunnels.cloudflared.configurations.update.assert_not_called()
        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned the wrong cloudflared tunnel")
