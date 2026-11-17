# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import zones_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)


class ZonesInfoTests(TestCase):
    def test_lists_every_zone_type(self):
        client = Mock()
        zones = [{"id": "zone", "name": "example.com"}, {"id": "other", "name": "example.net"}]
        client.zones.list.return_value = iter(zones)

        with self.assertRaises(ModuleExit) as raised:
            zones_info.run(FakeModule({}), client)

        # The match option was removed; it changed nothing, as no zone filter is sent.
        client.zones.list.assert_called_once_with(type="full,partial,secondary,internal")
        self.assertEqual(raised.exception.values, {"changed": False, "zones": zones})

    def test_rejects_malformed_zones(self):
        client = Mock()
        client.zones.list.return_value = [{"id": "zone"}]

        with self.assertRaises(ModuleFail):
            zones_info.run(FakeModule({}), client)

    def test_api_error_names_operation(self):
        client = Mock()
        client.zones.list.side_effect = status_error(403)

        with self.assertRaises(Exception) as raised:
            zones_info.run(FakeModule({}), client)

        self.assertEqual(raised.exception._cloudflare_message, "Cloudflare API request failed while gathering zones")
