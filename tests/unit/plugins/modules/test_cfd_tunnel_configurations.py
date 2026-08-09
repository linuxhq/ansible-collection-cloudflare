# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    cfd_tunnel_configurations,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class CfdTunnelConfigurationsTests(TestCase):
    def test_nested_provider_fields_do_not_cause_change(self):
        config = {"ingress": [{"service": "http_status:404"}]}
        current = {
            "config": {
                "ingress": [{"service": "http_status:404", "provider_field": "ignored"}]
            }
        }
        module = FakeModule(
            {"account_id": "account", "tunnel_id": "tunnel", "config": config}
        )

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value=current,
            ),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_check_mode_does_not_update(self):
        module = FakeModule(
            {"account_id": "account", "tunnel_id": "tunnel", "config": {"warp": True}},
            check_mode=True,
        )

        with (
            patch.object(
                cfd_tunnel_configurations,
                "get_result",
                return_value={"config": {"warp": False}},
            ),
            patch.object(cfd_tunnel_configurations, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            cfd_tunnel_configurations.ensure_present(module, {})

        put.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
