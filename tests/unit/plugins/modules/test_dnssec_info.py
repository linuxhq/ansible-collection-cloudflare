# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class DnssecInfoTests(TestCase):
    def test_lists_dnssec_for_valid_zones(self):
        module = FakeModule({})
        client = Mock()
        client.zones.list.return_value = [
            Model({"id": "zone", "name": "example.com"}),
            Model({"name": "missing-id"}),
        ]
        client.dns.dnssec.get.return_value = Model({"status": "active"})

        with self.assertRaises(ModuleExit) as raised:
            dnssec_info.list(module, client)

        client.dns.dnssec.get.assert_called_once_with(zone_id="zone")
        self.assertEqual(
            raised.exception.values["dnssec"],
            [
                {
                    "id": "zone",
                    "name": "example.com",
                    "dnssec": {"status": "active"},
                }
            ],
        )
        self.assertEqual(raised.exception.values["skipped_zones"], [])
        self.assertFalse(raised.exception.values["changed"])
