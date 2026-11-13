# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

ACTIONS = [{"id": "always_use_https"}]
TARGETS = [{"target": "url", "constraint": {"value": "example.com/*"}}]


def params(**updates):
    values = {
        "zone_id": "zone",
        "actions": ACTIONS,
        "targets": TARGETS,
        "priority": None,
        "status": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(rules=(), created=None, updated=None, deleted=None):
    client = Mock()
    api = client.page_rules
    api.list.return_value = list(rules)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class PageRulesTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            pagerules.run(module, client)

        return raised.exception.values

    def test_finds_rule_by_targets(self):
        rules = [{"id": str(index), "targets": []} for index in range(124)]
        rules.append({"id": "match", "actions": ACTIONS, "targets": TARGETS})
        client, api = client_with(rules)

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(zone_id="zone")
        self.assertEqual(result["pagerule"], rules[-1])

    def test_rejects_malformed_targets(self):
        for targets in ({}, ["invalid"]):
            with self.subTest(targets=targets):
                client, _ignored = client_with([{"id": "rule", "targets": targets}])

                result = self.run_module(FakeModule(params()), client)

                self.assertIn("malformed page rule", result["msg"])

    def test_rejects_ambiguous_target_match(self):
        client, _ignored = client_with([{"id": "one", "targets": TARGETS}, {"id": "two", "targets": TARGETS}])

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("Multiple page rules", result["msg"])

    def test_check_mode_does_not_create(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_create_defaults_status_to_active(self):
        created = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": TARGETS}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(zone_id="zone", actions=ACTIONS, status="active", targets=TARGETS)
        self.assertEqual(result["pagerule"], created)

    def test_rejects_a_create_response_with_different_targets(self):
        client, _ignored = client_with(created={"id": "rule", "targets": []})

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare did not apply the requested page rule")

    def test_omitted_status_and_priority_preserve_current_values(self):
        current = {"id": "rule", "actions": ACTIONS, "priority": 10, "status": "disabled", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_update_sends_preserved_status_and_priority(self):
        actions = [{"id": "ssl", "value": "full"}]
        current = {"id": "rule", "actions": ACTIONS, "priority": 10, "status": "disabled", "targets": TARGETS}
        updated = {**current, "actions": actions}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_called_once_with(
            pagerule_id="rule", zone_id="zone", actions=actions, priority=10, status="disabled", targets=TARGETS
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["pagerule"], updated)

    def test_check_mode_does_not_update(self):
        current = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(status="disabled"), check_mode=True), client)

        api.update.assert_not_called()
        self.assertTrue(result["changed"])

    def test_nested_provider_fields_do_not_cause_change(self):
        current = {
            "id": "rule",
            "actions": [{"id": "always_use_https", "provider_default": True}],
            "targets": [{"target": "url", "constraint": {"value": "example.com/*", "provider_default": True}}],
        }
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_matches_target_urls_as_cloudflare_stores_them(self):
        cases = (
            ("Example.COM/Path/*", "example.com/Path/*"),
            ("example.com", "example.com/"),
            ("HTTPS://WWW.Example.com", "https://www.example.com/"),
        )
        for requested, stored in cases:
            with self.subTest(requested=requested):
                stored_targets = [{"target": "url", "constraint": {"operator": "matches", "value": stored}}]
                targets = [{"target": "url", "constraint": {"operator": "matches", "value": requested}}]
                current = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": stored_targets}
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(targets=targets)), client)

                api.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_creates_rule_with_canonical_target_url(self):
        stored_targets = [{"target": "url", "constraint": {"operator": "matches", "value": "example.com/"}}]
        targets = [{"target": "url", "constraint": {"operator": "matches", "value": "Example.com"}}]
        created = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": stored_targets}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(targets=targets)), client)

        self.assertEqual(api.create.call_args.kwargs["targets"], stored_targets)
        self.assertTrue(result["changed"])

    def test_action_order_is_not_significant(self):
        actions = [{"id": "ssl", "value": "full"}, {"id": "browser_check", "value": "on"}]
        listed = [{"id": "browser_check", "value": "on"}, {"id": "ssl", "value": "full"}]
        current = {"id": "rule", "actions": listed, "status": "active", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_creates_actions_sorted_by_id(self):
        actions = [{"id": "ssl", "value": "full"}, {"id": "browser_check", "value": "on"}]
        listed = [{"id": "browser_check", "value": "on"}, {"id": "ssl", "value": "full"}]
        client, api = client_with(created={"id": "rule", "actions": listed, "status": "active", "targets": TARGETS})

        result = self.run_module(FakeModule(params(actions=actions)), client)

        self.assertEqual(api.create.call_args.kwargs["actions"], listed)
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_delete_matching_rule(self):
        client, api = client_with([{"id": "rule", "targets": TARGETS}])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        api.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_deletes_matching_rule(self):
        client, api = client_with([{"id": "rule", "targets": TARGETS}], deleted={"id": "rule"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with(pagerule_id="rule", zone_id="zone")
        self.assertTrue(result["changed"])
