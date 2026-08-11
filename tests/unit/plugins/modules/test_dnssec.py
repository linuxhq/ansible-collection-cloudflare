# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
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


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class DnssecTests(TestCase):
    def test_pending_status_is_equivalent_to_active(self):
        module = FakeModule(params())
        client = Mock()
        client.dns.dnssec.get.return_value = Model({"status": "pending"})

        with self.assertRaises(ModuleExit) as raised:
            dnssec.ensure_present(module, client)

        client.dns.dnssec.edit.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_updates_only_explicit_fields(self):
        module = FakeModule(params(dnssec_presigned=True))
        client = Mock()
        client.dns.dnssec.get.return_value = Model(
            {
                "status": "disabled",
                "dnssec_multi_signer": False,
                "dnssec_presigned": False,
                "dnssec_use_nsec3": False,
            }
        )
        client.dns.dnssec.edit.return_value = Model(
            {"status": "pending", "dnssec_presigned": True}
        )

        with self.assertRaises(ModuleExit) as raised:
            dnssec.ensure_present(module, client)

        client.dns.dnssec.edit.assert_called_once_with(
            zone_id="zone",
            dnssec_presigned=True,
            status="active",
        )
        self.assertTrue(raised.exception.values["changed"])

    def test_rejects_an_unmet_update_postcondition(self):
        module = FakeModule(params(dnssec_presigned=True))
        client = Mock()
        client.dns.dnssec.get.return_value = Model(
            {"status": "active", "dnssec_presigned": False}
        )
        client.dns.dnssec.edit.return_value = Model(
            {"status": "active", "dnssec_presigned": False}
        )

        with self.assertRaises(ModuleFail) as raised:
            dnssec.ensure_present(module, client)

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare did not apply the requested DNSSEC settings",
        )
