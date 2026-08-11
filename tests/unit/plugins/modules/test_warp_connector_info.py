# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import warp_connector_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class WarpConnectorInfoTests(TestCase):
    def test_includes_tokens_when_requested(self):
        module = FakeModule({"account_id": "account", "include_token": True})
        connectors = [{"id": "connector", "name": "example"}]

        with (
            patch.object(warp_connector_info, "list_all", return_value=connectors),
            patch.object(
                warp_connector_info,
                "get_result",
                return_value="token",
            ) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            warp_connector_info.list_resources(module, {})

        get.assert_called_once_with(
            {},
            "/accounts/account/warp_connector/connector/token",
        )
        self.assertEqual(
            raised.exception.values["warp_connectors"],
            [{"id": "connector", "name": "example", "token": "token"}],
        )

    def test_omits_tokens_when_not_requested(self):
        module = FakeModule({"account_id": "account", "include_token": False})

        with (
            patch.object(warp_connector_info, "list_all", return_value=[]),
            patch.object(warp_connector_info, "get_result") as get,
            self.assertRaises(ModuleExit),
        ):
            warp_connector_info.list_resources(module, {})

        get.assert_not_called()
