# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

import cloudflare
import httpx

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    UNION_MISFIT,
    FakeModule,
    ModuleExit,
    ModuleFail,
    run_through_client,
    status_error,
)


class CfdTunnelConfigurationsInfoTests(TestCase):
    def run_module(self, tunnels, configuration):
        client = Mock()
        api = client.zero_trust.tunnels.cloudflared
        api.list.return_value = tunnels
        api.configurations.get.return_value = configuration
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            cfd_tunnel_configurations_info.run(FakeModule({"account_id": "account"}), client)

        return raised.exception.values, api

    def test_lists_only_remote_tunnel_configurations(self):
        tunnels = [
            {"id": "remote", "name": "one", "remote_config": True},
            {"id": "local", "name": "two", "config_src": "local"},
        ]

        result, api = self.run_module(tunnels, {"config": {"ingress": []}})

        api.list.assert_called_once_with(account_id="account", is_deleted=False, per_page=1000)
        api.configurations.get.assert_called_once_with("remote", account_id="account")
        self.assertEqual(
            result["cfd_tunnel_configurations"],
            [{"id": "remote", "name": "one", "config": {"ingress": []}}],
        )

    def test_returns_empty_config_for_unconfigured_remote_tunnel(self):
        for configuration in ({"config": None}, None):
            with self.subTest(configuration=configuration):
                result, _ignored = self.run_module([{"id": "remote", "name": "one"}], configuration)

                self.assertEqual(result["cfd_tunnel_configurations"], [{"id": "remote", "name": "one", "config": {}}])

    def test_skips_tunnel_deleted_after_listing(self):
        tunnels = [{"id": "deleted", "name": "one"}, {"id": "remote", "name": "two"}]
        client = Mock()
        api = client.zero_trust.tunnels.cloudflared
        api.list.return_value = tunnels
        api.configurations.get.side_effect = [status_error(404), {"config": {"ingress": []}}]

        with self.assertRaises(ModuleExit) as raised:
            cfd_tunnel_configurations_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(
            raised.exception.values["cfd_tunnel_configurations"],
            [{"id": "remote", "name": "two", "config": {"ingress": []}}],
        )

    def test_other_configuration_errors_propagate(self):
        client = Mock()
        api = client.zero_trust.tunnels.cloudflared
        api.list.return_value = [{"id": "remote", "name": "one"}]
        api.configurations.get.side_effect = status_error(403)

        with self.assertRaises(cloudflare.PermissionDeniedError) as raised:
            cfd_tunnel_configurations_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(raised.exception.status_code, 403)

    def test_malformed_configuration_fails_naming_the_tunnel(self):
        for configuration in (["config"], "malformed", [], False):
            with self.subTest(configuration=configuration):
                result, _ignored = self.run_module([{"id": "remote", "name": "one"}], configuration)

                self.assertEqual(
                    result,
                    {
                        "msg": "Cloudflare API returned malformed tunnel configuration data",
                        "account_id": "account",
                        "tunnel_id": "remote",
                    },
                )

    def test_returns_non_null_config_unmodified(self):
        for config in ("x", [], ["ingress"], False):
            with self.subTest(config=config):
                result, _ignored = self.run_module([{"id": "remote", "name": "one"}], {"config": config})

                self.assertEqual(
                    result["cfd_tunnel_configurations"], [{"id": "remote", "name": "one", "config": config}]
                )

    def test_unserializable_configuration_fails_naming_the_tunnel(self):
        # The SDK builds the configuration, but fails to serialize an ingress rule.
        def respond(request):
            if request.url.path.endswith("/configurations"):
                return httpx.Response(200, json={"success": True, "result": {"config": {"ingress": [UNION_MISFIT]}}})

            # Later pages are empty, which ends the SDK pager.
            tunnels = [{"id": "remote", "name": "one"}] if request.url.params.get("page", "1") == "1" else []
            return httpx.Response(200, json={"success": True, "result": tunnels})

        result, requests = run_through_client(
            cfd_tunnel_configurations_info.run, FakeModule({"account_id": "account", "api_token": "token"}), respond
        )

        self.assertEqual([method for method, _path in requests], ["GET", "GET", "GET"])
        self.assertEqual(result["msg"], "Cloudflare API request failed while gathering the tunnel configuration")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["tunnel_id"], "remote")
        self.assertTrue(result["error"].startswith("TypeError: "))
        self.assertNotIn("changed", result)
