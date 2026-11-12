# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    CloudflareResponseError,
)
from ansible_collections.linuxhq.cloudflare.plugins.modules import warp_connector
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)

SECRET = "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg="
CREATED = {"id": "connector-id", "name": "connector"}


def params(**updates):
    values = {
        "account_id": "account",
        "name": "connector",
        "tunnel_secret": None,
        "rotate_secrets": False,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(connectors=(), created=None, edited=None):
    client = Mock()
    api = client.zero_trust.tunnels.warp_connector
    api.list.return_value = list(connectors)
    api.create.return_value = created
    api.edit.return_value = edited
    api.delete.return_value = None
    return client, api


class WarpConnectorTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            warp_connector.run(module, client)

        return raised.exception.values

    def test_looks_up_active_connector_by_name(self):
        client, api = client_with()
        self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account", name="connector", is_deleted=False)
        api.create.assert_not_called()

    def test_creates_connector(self):
        client, api = client_with(created=CREATED)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", name="connector")
        api.edit.assert_not_called()
        self.assertEqual(result["warp_connector"], CREATED)

    def test_returns_credentials_from_created_connector(self):
        created = {**CREATED, "token": "secret", "credentials_file": {"TunnelSecret": "secret"}}
        client, _ignored = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["warp_connector"], created)

    def test_creates_connector_then_applies_secret(self):
        client, api = client_with(created=CREATED, edited={**CREATED, "tunnel_secret": SECRET})

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET)), client)

        api.edit.assert_called_once_with("connector-id", account_id="account", tunnel_secret=SECRET)
        api.delete.assert_not_called()
        self.assertEqual(result["warp_connector"], {**CREATED, "tunnel_secret": SECRET})

    def test_secret_failure_rolls_back_created_connector(self):
        client, api = client_with(created=CREATED)
        error = status_error(400)
        api.edit.side_effect = error

        with self.assertRaises(type(error)) as raised:
            warp_connector.run(FakeModule(params(tunnel_secret=SECRET)), client)

        self.assertIs(raised.exception, error)
        api.delete.assert_called_once_with("connector-id", account_id="account")

    def test_reports_connector_id_when_rollback_fails(self):
        client, api = client_with(created=CREATED)
        api.edit.side_effect = status_error(400)
        api.delete.side_effect = status_error(500)

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET)), client)

        self.assertEqual(result["warp_connector_id"], "connector-id")

    def test_reports_connector_id_when_rollback_response_is_wrong(self):
        client, api = client_with(created=CREATED)
        api.edit.side_effect = status_error(400)
        api.delete.return_value = {"id": "other"}

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET)), client)

        self.assertEqual(result["warp_connector_id"], "connector-id")

    def test_wrong_secret_response_rolls_back_created_connector(self):
        client, api = client_with(created=CREATED, edited={"id": "wrong", "name": "connector"})

        with self.assertRaises(CloudflareResponseError):
            warp_connector.run(FakeModule(params(tunnel_secret=SECRET)), client)

        api.delete.assert_called_once_with("connector-id", account_id="account")

    def test_rotates_secret_on_existing_connector(self):
        client, api = client_with([CREATED], edited={**CREATED, "token": "secret"})

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET, rotate_secrets=True)), client)

        api.edit.assert_called_once_with("connector-id", account_id="account", tunnel_secret=SECRET)
        self.assertTrue(result["changed"])
        self.assertEqual(result["warp_connector"], {**CREATED, "token": "secret"})

    def test_check_mode_does_not_rotate_secret(self):
        client, api = client_with([CREATED])

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET, rotate_secrets=True), check_mode=True), client)

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_existing_connector_is_unchanged(self):
        client, api = client_with([{**CREATED, "token": "secret"}])

        result = self.run_module(FakeModule(params()), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["warp_connector"], {**CREATED, "token": "secret"})

    def test_deletes_connector(self):
        client, api = client_with([CREATED])

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("connector-id", account_id="account")
        self.assertTrue(result["changed"])

    def test_missing_connector_is_already_absent(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])
