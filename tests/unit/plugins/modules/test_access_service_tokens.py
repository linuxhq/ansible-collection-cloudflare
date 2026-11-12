# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_service_tokens
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {"account_id": "account", "name": "automation", "duration": "1y", "state": "present"}
    values.update(updates)
    return values


def client_with(tokens=(), created=None, updated=None, deleted=None):
    client = Mock()
    api = client.zero_trust.access.service_tokens
    api.list.return_value = list(tokens)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class AccessServiceTokensTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            access_service_tokens.run(module, client)

        return raised.exception.values

    def test_creates_token_with_explicit_duration_and_returns_secret(self):
        created = {"id": "token", "name": "automation", "duration": "1y", "client_secret": "secret"}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(account_id="account", name="automation")
        api.create.assert_called_once_with(account_id="account", name="automation", duration="1y")
        self.assertTrue(result["changed"])
        self.assertEqual(result["service_token"], created)

    def test_creates_token_without_duration(self):
        client, api = client_with(created={"id": "token", "name": "automation"})

        self.run_module(FakeModule(params(duration=None)), client)

        api.create.assert_called_once_with(account_id="account", name="automation")

    def test_check_mode_does_not_create(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_updates_token_duration(self):
        current = {"id": "token", "name": "automation", "duration": "1h"}
        client, api = client_with([current], updated={**current, "duration": "1y"})

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_called_once_with("token", account_id="account", name="automation", duration="1y")
        self.assertTrue(result["changed"])

    def test_rejects_update_response_with_wrong_duration(self):
        current = {"id": "token", "name": "automation", "duration": "1h"}
        client, _ignored = client_with([current], updated=current)

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])

    def test_forever_token_without_expiry_is_unchanged(self):
        client, api = client_with([{"id": "token", "name": "automation", "expires_at": None}])

        result = self.run_module(FakeModule(params(duration="forever")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_deletes_token_by_sdk_identifier(self):
        client, api = client_with([{"id": "token", "name": "automation"}], deleted={"id": "token"})

        result = self.run_module(FakeModule(params(duration=None, state="absent")), client)

        api.delete.assert_called_once_with("token", account_id="account")
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_delete(self):
        client, api = client_with([{"id": "token", "name": "automation"}])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        api.delete.assert_not_called()
        self.assertTrue(result["changed"])
