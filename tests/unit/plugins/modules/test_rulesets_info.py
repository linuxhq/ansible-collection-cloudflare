# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import rulesets_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class RulesetsInfoTests(TestCase):
    def test_lists_entrypoints_for_zones_with_ids(self):
        module = FakeModule({"phase": "http_request_firewall_custom"})
        zones = [{"id": "zone", "name": "example.com"}, {"name": "missing-id"}]
        entrypoint = {"id": "ruleset", "phase": module.params["phase"]}

        with (
            patch.object(rulesets_info, "list_all", return_value=zones),
            patch.object(
                rulesets_info,
                "get_result",
                return_value=entrypoint,
            ) as get,
            self.assertRaises(ModuleExit) as raised,
        ):
            rulesets_info.list(module, {})

        get.assert_called_once_with(
            {},
            "/zones/zone/rulesets/phases/http_request_firewall_custom/entrypoint",
            default={},
            ok_statuses=[404],
        )
        self.assertEqual(
            raised.exception.values["rulesets"],
            [
                {
                    "id": "ruleset",
                    "name": "example.com",
                    "phase": module.params["phase"],
                    "rules": [],
                    "zone_id": "zone",
                }
            ],
        )
