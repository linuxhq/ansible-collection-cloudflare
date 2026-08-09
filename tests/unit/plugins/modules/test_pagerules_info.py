# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class PageRulesInfoTests(TestCase):
    def test_lists_rules_for_zones_with_ids(self):
        module = FakeModule({})
        zones = [{"id": "zone", "name": "example.com"}, {"name": "missing-id"}]

        with (
            patch.object(pagerules_info, "list_all", return_value=zones),
            patch.object(
                pagerules_info,
                "get_result",
                return_value=[{"id": "rule"}],
            ) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules_info.list(module, {})

        get.assert_called_once_with({}, "/zones/zone/pagerules", default=[])
        self.assertEqual(
            raised.exception.values["pagerules"],
            [
                {
                    "id": "zone",
                    "name": "example.com",
                    "pagerules": [{"id": "rule"}],
                }
            ],
        )
