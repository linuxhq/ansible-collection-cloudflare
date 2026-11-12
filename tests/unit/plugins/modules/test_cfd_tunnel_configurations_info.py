# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
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

    def test_rejects_malformed_configuration(self):
        result, _ignored = self.run_module([{"id": "remote", "name": "one"}], {"config": ["invalid"]})

        self.assertIn("malformed tunnel configuration", result["msg"])
