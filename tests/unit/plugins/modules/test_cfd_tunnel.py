# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import cfd_tunnel
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "tunnel",
        "config_src": "cloudflare",
        "tunnel_secret": None,
        "rotate_secrets": False,
    }
    values.update(updates)
    return values


class CfdTunnelTests(TestCase):
    def test_existing_tunnel_is_unchanged(self):
        current = {"id": "tunnel-id", "name": "tunnel"}
        module = FakeModule(params())

        with (
            patch.object(cfd_tunnel, "find_by_name", return_value=current),
            patch.object(cfd_tunnel, "patch_result") as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_requires_config_source_only_when_creating(self):
        module = FakeModule(params(config_src=None))

        with (
            patch.object(cfd_tunnel, "find_by_name", return_value=None),
            patch.object(cfd_tunnel, "post_result") as post,
            self.assertRaises(ModuleFail) as raised,
        ):
            cfd_tunnel.ensure_present(module, {})

        post.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "config_src is required when creating a cloudflared tunnel",
        )

    def test_check_mode_does_not_rotate_secret(self):
        current = {"id": "tunnel-id", "name": "tunnel"}
        module = FakeModule(
            params(rotate_secrets=True, tunnel_secret="secret"),
            check_mode=True,
        )

        with (
            patch.object(cfd_tunnel, "find_by_name", return_value=current),
            patch.object(cfd_tunnel, "patch_result") as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
