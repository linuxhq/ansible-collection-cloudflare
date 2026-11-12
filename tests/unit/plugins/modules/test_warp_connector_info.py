# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import warp_connector_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)


class WarpConnectorInfoTests(TestCase):
    def run_module(self, listed, include_token, token="token"):
        client = Mock()
        api = client.zero_trust.tunnels.warp_connector
        api.list.return_value = listed
        api.token.get.return_value = token
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            warp_connector_info.run(FakeModule({"account_id": "account", "include_token": include_token}), client)

        return raised.exception.values, api

    def test_lists_active_resources(self):
        result, api = self.run_module([], False)

        api.list.assert_called_once_with(account_id="account", is_deleted=False, per_page=1000)
        self.assertEqual(result, {"changed": False, "warp_connectors": []})

    def test_includes_tokens_when_requested(self):
        result, api = self.run_module([{"id": "connector", "name": "example", "token": "stale"}], True)

        api.token.get.assert_called_once_with("connector", account_id="account")
        self.assertEqual(result["warp_connectors"], [{"id": "connector", "name": "example", "token": "token"}])

    def test_rejects_malformed_token(self):
        result, _ignored = self.run_module([{"id": "connector", "name": "example"}], True, token="")

        self.assertIn("malformed WARP Connector token", result["msg"])

    def test_token_failure_names_resource(self):
        client = Mock()
        api = client.zero_trust.tunnels.warp_connector
        api.list.return_value = [{"id": "connector", "name": "example"}]
        error = status_error(403)
        api.token.get.side_effect = error

        with self.assertRaises(type(error)) as raised:
            warp_connector_info.run(FakeModule({"account_id": "account", "include_token": True}), client)

        self.assertEqual(raised.exception._cloudflare_context, {"account_id": "account", "resource_id": "connector"})

    def test_omits_tokens_when_not_requested(self):
        _ignored, api = self.run_module([{"id": "connector", "name": "example"}], False)

        api.token.get.assert_not_called()

    def test_returns_credentials_from_listed_resources(self):
        listed = [
            {
                "id": "connector",
                "name": "example",
                "token": "secret",
                "credentials_file": {"TunnelSecret": "secret"},
            }
        ]

        result, _ignored = self.run_module(listed, False)

        self.assertEqual(result["warp_connectors"], listed)
