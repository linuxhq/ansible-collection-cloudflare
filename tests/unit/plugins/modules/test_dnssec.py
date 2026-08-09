# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


def params(**updates):
    values = {
        "zone_id": "zone",
        "dnssec_multi_signer": None,
        "dnssec_presigned": None,
        "dnssec_use_nsec3": None,
        "status": "active",
    }
    values.update(updates)
    return values


class DnssecTests(TestCase):
    def test_pending_status_is_equivalent_to_active(self):
        module = FakeModule(params())
        client = Mock()
        client.dns.dnssec.get.return_value = SimpleNamespace(status="pending")

        with self.assertRaises(ModuleExit) as raised:
            dnssec.ensure_present(module, client)

        client.dns.dnssec.edit.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_updates_only_explicit_fields(self):
        module = FakeModule(params(dnssec_presigned=True))
        client = Mock()
        client.dns.dnssec.get.return_value = SimpleNamespace(
            status="disabled",
            dnssec_multi_signer=False,
            dnssec_presigned=False,
            dnssec_use_nsec3=False,
        )
        client.dns.dnssec.edit.return_value = SimpleNamespace(status="active")

        with self.assertRaises(ModuleExit) as raised:
            dnssec.ensure_present(module, client)

        client.dns.dnssec.edit.assert_called_once_with(
            zone_id="zone",
            dnssec_presigned=True,
            status="active",
        )
        self.assertTrue(raised.exception.values["changed"])
