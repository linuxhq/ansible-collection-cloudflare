# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import zones_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class ZonesInfoTests(TestCase):
    def test_lists_zones_with_match_mode(self):
        module = FakeModule({"match": "all"})
        zones = [{"id": "zone"}]

        with (
            patch.object(zones_info, "list_all", return_value=zones) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            zones_info.list(module, {})

        listed.assert_called_once_with({}, "/zones?match=all")
        self.assertEqual(raised.exception.values["zones"], zones)
        self.assertFalse(raised.exception.values["changed"])
