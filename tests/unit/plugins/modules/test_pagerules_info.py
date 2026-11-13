# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)

ZONES = [{"id": "zone", "name": "example.com"}, {"id": "other", "name": "example.net"}]


def client_with(zones, rules_by_zone):
    client = Mock()
    client.zones.list.return_value = iter(zones)
    client.page_rules.list.side_effect = lambda zone_id: list(rules_by_zone[zone_id])
    return client


class PageRulesInfoTests(TestCase):
    def test_lists_rules_grouped_by_zone(self):
        rules = [{"id": str(index), "actions": [{"id": "ssl"}], "targets": []} for index in range(125)]
        client = client_with(ZONES, {"zone": rules, "other": []})

        with self.assertRaises(ModuleExit) as raised:
            pagerules_info.run(FakeModule({}), client)

        client.zones.list.assert_called_once_with()
        self.assertEqual(
            [call.kwargs for call in client.page_rules.list.call_args_list],
            [{"zone_id": "zone"}, {"zone_id": "other"}],
        )
        self.assertEqual(
            raised.exception.values,
            {
                "changed": False,
                "pagerules": [
                    {"id": "zone", "name": "example.com", "pagerules": rules},
                    {"id": "other", "name": "example.net", "pagerules": []},
                ],
            },
        )

    def test_rejects_malformed_zones(self):
        client = client_with([{"id": "zone"}], {})

        with self.assertRaises(ModuleFail) as raised:
            pagerules_info.run(FakeModule({}), client)

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed zone data")

    def test_rejects_malformed_rule_collections(self):
        for rule in (
            {"actions": [], "targets": []},
            {"id": "rule", "actions": {}, "targets": []},
            {"id": "rule", "actions": [], "targets": ["invalid"]},
        ):
            with self.subTest(rule=rule):
                client = client_with(ZONES[:1], {"zone": [rule]})

                with self.assertRaises(ModuleFail) as raised:
                    pagerules_info.run(FakeModule({}), client)

                self.assertIn("malformed page rule", raised.exception.values["msg"])

    def test_skips_zones_deleted_after_listing(self):
        invalid_zone = {"success": False, "errors": [{"code": 1001, "message": "Invalid zone identifier"}]}
        for error in (status_error(404), status_error(400, invalid_zone)):
            with self.subTest(status_code=error.status_code):
                client = client_with(ZONES, {})
                client.page_rules.list.side_effect = [error, []]

                with self.assertRaises(ModuleExit) as raised:
                    pagerules_info.run(FakeModule({}), client)

                self.assertEqual(
                    raised.exception.values,
                    {"changed": False, "pagerules": [{"id": "other", "name": "example.net", "pagerules": []}]},
                )

    def test_other_errors_still_fail(self):
        other_error = {"success": False, "errors": [{"code": 1004, "message": "Bad request"}]}
        for error in (status_error(400, other_error), status_error(403)):
            with self.subTest(status_code=error.status_code):
                client = client_with(ZONES, {})
                client.page_rules.list.side_effect = error

                with self.assertRaises(error.__class__):
                    pagerules_info.run(FakeModule({}), client)
