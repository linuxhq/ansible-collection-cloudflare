# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import cfd_tunnel
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

SECRET = "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg="
CREDENTIALS = {
    "token": "EXAMPLE-generated-token",
    "credentials_file": {"TunnelSecret": "EXAMPLE-generated-secret"},
    "tunnel_secret": "EXAMPLE-secret",
}


def params(**updates):
    values = {
        "account_id": "account",
        "name": "tunnel",
        "config_src": "cloudflare",
        "tunnel_secret": None,
        "rotate_secrets": False,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(tunnels=(), created=None, edited=None):
    client = Mock()
    api = client.zero_trust.tunnels.cloudflared
    api.list.return_value = list(tunnels)
    api.create.return_value = created
    api.edit.return_value = edited
    api.delete.return_value = None
    return client, api


class CfdTunnelTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            cfd_tunnel.run(module, client)

        return raised.exception.values

    def test_looks_up_active_tunnel_by_name(self):
        client, api = client_with()
        self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account", name="tunnel", is_deleted=False)

    def test_returns_generated_credentials_on_create(self):
        safe = {"id": "tunnel-id", "name": "tunnel", "config_src": "cloudflare"}
        client, api = client_with(created={**safe, **CREDENTIALS})

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", config_src="cloudflare", name="tunnel")
        api.edit.assert_not_called()
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], {**safe, **CREDENTIALS})

    def test_rotates_secret_and_returns_result(self):
        safe = {"id": "tunnel-id", "name": "tunnel", "config_src": "local"}
        client, api = client_with([safe], edited={**safe, **CREDENTIALS})

        result = self.run_module(
            FakeModule(params(config_src="local", rotate_secrets=True, tunnel_secret=SECRET)), client
        )

        api.edit.assert_called_once_with("tunnel-id", account_id="account", tunnel_secret=SECRET)
        api.create.assert_not_called()
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], {**safe, **CREDENTIALS})

    def test_returns_credentials_from_existing_tunnel_results(self):
        for state, check_mode in (("present", False), ("present", True), ("absent", False), ("absent", True)):
            with self.subTest(state=state, check_mode=check_mode):
                client, api = client_with([{"id": "tunnel-id", "name": "tunnel", **CREDENTIALS}])

                result = self.run_module(FakeModule(params(state=state), check_mode=check_mode), client)

                self.assertEqual(result["cfd_tunnel"], {"id": "tunnel-id", "name": "tunnel", **CREDENTIALS})
                if state == "absent" and not check_mode:
                    api.delete.assert_called_once_with("tunnel-id", account_id="account")
                else:
                    api.delete.assert_not_called()

    def test_existing_tunnel_is_unchanged(self):
        client, api = client_with([{"id": "tunnel-id", "name": "tunnel"}])

        result = self.run_module(FakeModule(params()), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_requires_config_source_only_when_creating(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(config_src=None)), client)

        api.create.assert_not_called()
        self.assertEqual(result["msg"], "config_src is required when creating a cloudflared tunnel")

    def test_creates_remote_tunnel_with_secret(self):
        created = {"id": "tunnel-id", "name": "tunnel", "config_src": "cloudflare"}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(tunnel_secret=SECRET)), client)

        api.create.assert_called_once_with(
            account_id="account", config_src="cloudflare", name="tunnel", tunnel_secret=SECRET
        )
        self.assertTrue(result["changed"])

    def test_rejects_create_response_with_wrong_config_source(self):
        client, _ignored = client_with(created={"id": "tunnel-id", "name": "tunnel", "config_src": "local"})

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("wrong cloudflared tunnel", result["msg"])

    def test_rejects_invalid_secret_before_lookup(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(config_src="local", tunnel_secret="short")), client)

        api.list.assert_not_called()
        self.assertIn("at least 32 bytes", result["msg"])

    def test_check_mode_does_not_rotate_secret(self):
        client, api = client_with([{"id": "tunnel-id", "name": "tunnel", "config_src": "local"}])
        module = FakeModule(params(config_src="local", rotate_secrets=True, tunnel_secret=SECRET), check_mode=True)

        result = self.run_module(module, client)

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rotates_secret_for_remote_tunnel(self):
        current = {"id": "tunnel-id", "name": "tunnel", "config_src": "cloudflare", "remote_config": True}
        client, api = client_with([current], edited=current)

        result = self.run_module(FakeModule(params(rotate_secrets=True, tunnel_secret=SECRET)), client)

        api.edit.assert_called_once_with("tunnel-id", account_id="account", tunnel_secret=SECRET)
        self.assertTrue(result["changed"])
