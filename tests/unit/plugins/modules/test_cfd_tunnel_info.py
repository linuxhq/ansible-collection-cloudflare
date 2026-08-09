# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import cfd_tunnel_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class CfdTunnelInfoTests(TestCase):
    def test_includes_tokens_when_requested(self):
        module = FakeModule({"account_id": "account", "include_token": True})
        tunnels = [{"id": "tunnel"}]

        with (
            patch.object(cfd_tunnel_info, "list_all", return_value=tunnels),
            patch.object(cfd_tunnel_info, "get_result", return_value="token") as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_info.list_resources(module, {})

        get.assert_called_once_with(
            {},
            "/accounts/account/cfd_tunnel/tunnel/token",
        )
        self.assertEqual(
            raised.exception.values["cfd_tunnels"],
            [{"id": "tunnel", "token": "token"}],
        )

    def test_omits_tokens_when_not_requested(self):
        module = FakeModule({"account_id": "account", "include_token": False})

        with (
            patch.object(cfd_tunnel_info, "list_all", return_value=[]),
            patch.object(cfd_tunnel_info, "get_result") as get,
            self.assertRaises(ModuleExit),
        ):
            cfd_tunnel_info.list_resources(module, {})

        get.assert_not_called()
