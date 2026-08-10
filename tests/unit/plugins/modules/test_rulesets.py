# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import rulesets
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "zone_id": "zone",
        "name": "default",
        "rules": None,
        "phase": "http_request_firewall_custom",
        "kind": "zone",
    }
    values.update(updates)
    return values


class RulesetsTests(TestCase):
    def test_create_requires_name(self):
        module = FakeModule(params(name=None))

        with (
            patch.object(rulesets, "get_result", return_value=None),
            patch.object(rulesets, "post_result") as post,
            self.assertRaises(ModuleFail) as raised,
        ):
            rulesets.ensure_present(module, {})

        post.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "name is required when creating a ruleset",
        )

    def test_omitted_rules_preserve_current_rules(self):
        current = {
            "id": "ruleset",
            "name": "default",
            "rules": [{"action": "block", "expression": "true"}],
        }
        module = FakeModule(params())

        with (
            patch.object(rulesets, "get_result", return_value=current),
            patch.object(rulesets, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            rulesets.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_rejects_rename_before_update(self):
        current = {"id": "ruleset", "name": "existing", "rules": []}
        module = FakeModule(params(name="renamed", rules=[]))

        with (
            patch.object(rulesets, "get_result", return_value=current),
            patch.object(rulesets, "put_result") as put,
            self.assertRaises(ModuleFail) as raised,
        ):
            rulesets.ensure_present(module, {})

        put.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "An existing ruleset cannot be renamed",
        )

    def test_deletes_entrypoint_ruleset_by_id(self):
        current = {"id": "ruleset", "name": "default"}
        module = FakeModule(params())

        with (
            patch.object(rulesets, "get_result", return_value=current),
            patch.object(rulesets, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            rulesets.ensure_absent(module, {})

        delete.assert_called_once_with({}, "/zones/zone/rulesets/ruleset")
        self.assertTrue(raised.exception.values["changed"])
