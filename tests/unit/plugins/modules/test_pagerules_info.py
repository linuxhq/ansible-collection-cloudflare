# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class PageRulesInfoTests(TestCase):
    def test_lists_rules_for_zones_with_ids(self):
        module = FakeModule({})
        zones = [{"id": "zone", "name": "example.com"}]
        rules = [{"id": "rule", "actions": [], "targets": []}]

        with (
            patch.object(
                pagerules_info,
                "list_all",
                side_effect=[zones, rules],
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules_info.list_resources(module, {})

        self.assertEqual(listed.call_count, 2)
        listed.assert_any_call({}, "/zones")
        listed.assert_any_call({}, "/zones/zone/pagerules")
        self.assertEqual(
            raised.exception.values["pagerules"],
            [
                {
                    "id": "zone",
                    "name": "example.com",
                    "pagerules": rules,
                }
            ],
        )

    def test_rejects_malformed_rule_collections(self):
        for rule in (
            {"id": "rule", "actions": {}, "targets": []},
            {"id": "rule", "actions": [], "targets": ["invalid"]},
        ):
            with (
                self.subTest(rule=rule),
                patch.object(
                    pagerules_info,
                    "list_all",
                    side_effect=[[{"id": "zone", "name": "example.com"}], [rule]],
                ),
                self.assertRaises(ModuleFail) as raised,
            ):
                pagerules_info.list_resources(FakeModule({}), {})

            self.assertIn("malformed page rule", raised.exception.values["msg"])
