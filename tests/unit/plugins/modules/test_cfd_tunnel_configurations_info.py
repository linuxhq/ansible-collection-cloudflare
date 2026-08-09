# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class CfdTunnelConfigurationsInfoTests(TestCase):
    def test_lists_only_remote_tunnel_configurations(self):
        module = FakeModule({"account_id": "account"})
        tunnels = [
            {"id": "remote", "name": "one", "remote_config": True},
            {"id": "local", "name": "two", "remote_config": False},
        ]

        with (
            patch.object(
                cfd_tunnel_configurations_info,
                "list_all",
                return_value=tunnels,
            ) as listed,
            patch.object(
                cfd_tunnel_configurations_info,
                "get_result",
                return_value={"config": {"ingress": []}},
            ) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations_info.list_resources(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/cfd_tunnel?is_deleted=false",
            per_page=1000,
        )
        get.assert_called_once_with(
            {},
            "/accounts/account/cfd_tunnel/remote/configurations",
            default={},
        )
        self.assertEqual(
            raised.exception.values["cfd_tunnel_configurations"],
            [{"id": "remote", "name": "one", "config": {"ingress": []}}],
        )
