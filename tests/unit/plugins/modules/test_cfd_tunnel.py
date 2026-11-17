# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import cfd_tunnel
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    connection_error,
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
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
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

    def test_create_recovers_the_tunnel_after_a_lost_response(self):
        recovered = {"id": "tunnel-id", "name": "tunnel", "config_src": "cloudflare"}
        client, api = client_with()
        api.create.side_effect = connection_error()
        api.list.side_effect = [[], [recovered]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(api.list.call_args.kwargs, {"account_id": "account", "name": "tunnel", "is_deleted": False})
        self.assertEqual(result["message"], "Cloudflared tunnel created")
        self.assertEqual(result["cfd_tunnel"], recovered)

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

    def test_rejects_config_source_change_before_any_write(self):
        for rotate in (False, True):
            with self.subTest(rotate_secrets=rotate):
                current = {"id": "tunnel-id", "name": "tunnel", "config_src": "local"}
                client, api = client_with([current], edited=current)
                options = {"rotate_secrets": True, "tunnel_secret": SECRET} if rotate else {}

                result = self.run_module(FakeModule(params(config_src="cloudflare", **options)), client)

                api.edit.assert_not_called()
                api.create.assert_not_called()
                self.assertEqual(
                    result["msg"],
                    "Cannot change config_src of the existing cloudflared tunnel from local to cloudflare",
                )
                self.assertEqual(result["current_config_src"], "local")
                self.assertEqual(result["requested_config_src"], "cloudflare")
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["resource_id"], "tunnel-id")
                self.assertEqual(result["cfd_tunnel_id"], "tunnel-id")

    def test_tunnel_without_config_source_is_local(self):
        # Cloudflare stores a tunnel created without config_src as null with remote_config false.
        current = {"id": "tunnel-id", "name": "tunnel", "config_src": None, "remote_config": False}
        client, api = client_with([current], edited=current)

        result = self.run_module(FakeModule(params(config_src="cloudflare")), client)

        api.edit.assert_not_called()
        self.assertEqual(result["current_config_src"], "local")
        self.assertEqual(result["requested_config_src"], "cloudflare")

        client, api = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(config_src="local")), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_creates_tunnel_without_config_source(self):
        # Cloudflare creates a tunnel without a configuration source.
        created = {"id": "tunnel-id", "name": "tunnel"}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(config_src=None)), client)

        api.create.assert_called_once_with(account_id="account", name="tunnel")
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], created)

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

    def test_sends_secret_without_local_checks(self):
        # Cloudflare validates the secret on the only write, so it is sent as given.
        created = {"id": "tunnel-id", "name": "tunnel", "config_src": "local"}
        client, api = client_with(created=created)

        self.run_module(FakeModule(params(config_src="local", tunnel_secret="short")), client)

        api.create.assert_called_once_with(
            account_id="account", config_src="local", name="tunnel", tunnel_secret="short"
        )

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

    def test_created_tunnel_with_another_config_src_reports_the_write(self):
        created = {"id": "tunnel-id", "name": "tunnel", "config_src": "local", **CREDENTIALS}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong cloudflared tunnel")
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], created)
        self.assertEqual(result["resource_id"], "tunnel-id")
        self.assertEqual(result["account_id"], "account")

    def test_recovered_tunnel_with_another_config_src_reports_the_write(self):
        recovered = {"id": "tunnel-id", "name": "tunnel", "config_src": "local"}
        client, api = client_with()
        api.create.side_effect = connection_error()
        api.list.side_effect = [[], [recovered]]

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong cloudflared tunnel")
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], recovered)
        self.assertEqual(result["resource_id"], "tunnel-id")

    def test_rotated_tunnel_with_another_id_reports_the_write(self):
        current = {"id": "tunnel-id", "name": "tunnel", "config_src": "cloudflare"}
        edited = {"id": "other", "name": "tunnel", "config_src": "cloudflare", **CREDENTIALS}
        client, api = client_with([current], edited=edited)

        result = self.run_module(FakeModule(params(rotate_secrets=True, tunnel_secret=SECRET)), client)

        api.edit.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong cloudflared tunnel")
        self.assertTrue(result["changed"])
        self.assertEqual(result["cfd_tunnel"], edited)
        self.assertEqual(result["resource_id"], "tunnel-id")
        self.assertEqual(result["account_id"], "account")
