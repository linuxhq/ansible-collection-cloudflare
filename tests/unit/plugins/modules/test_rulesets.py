# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible.module_utils import basic

from ansible_collections.linuxhq.cloudflare.plugins.modules import rulesets
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)

PHASE = "http_request_firewall_custom"
RULES = [{"action": "block", "expression": "true", "enabled": True}]
CURRENT = {"id": "ruleset", "name": "default", "kind": "zone", "phase": PHASE, "rules": RULES}


def params(**updates):
    values = {
        "zone_id": "zone",
        "name": "default",
        "rules": None,
        "phase": PHASE,
        "kind": "zone",
        "state": "present",
    }
    values.update(updates)
    return values


def make_client(current=None, created=None, updated=None):
    client = Mock()
    api = client.rulesets
    if current is None:
        api.phases.get.side_effect = status_error(404)
    else:
        api.phases.get.return_value = current

    api.create.return_value = created
    api.phases.update.return_value = updated
    api.delete.return_value = None
    return client, api


class RulesetsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_unsupported_kinds_fail_before_opening_client(self):
        for kind in ("custom", "managed", "root"):
            for state in ("present", "absent"):
                for check_mode in (False, True):
                    arguments = {
                        **params(kind=kind, state=state),
                        "api_token": "test-token",
                        "_ansible_check_mode": check_mode,
                    }
                    with (
                        self.subTest(kind=kind, state=state, check_mode=check_mode),
                        patch.object(basic, "_load_params", return_value=arguments),
                        patch.object(basic.AnsibleModule, "fail_json", side_effect=FakeModule({}).fail_json),
                        patch.object(rulesets, "cloudflare_client") as client,
                        self.assertRaises(ModuleFail) as raised,
                    ):
                        rulesets.main()

                    self.assertIn("value of kind must be one of", raised.exception.values["msg"])
                    client.assert_not_called()

    def test_rejects_malformed_rules(self):
        for rules in ({}, ["invalid"]):
            client, _ignored = make_client({**CURRENT, "rules": rules})
            with self.subTest(rules=rules):
                result = self.run_module(FakeModule(params()), client)

            self.assertIn("malformed ruleset", result["msg"])

    def test_rejects_sdk_cache_control_spellings_before_any_request(self):
        for key in (
            "max_age",
            "must_revalidate",
            "must_understand",
            "no_cache",
            "no_store",
            "no_transform",
            "proxy_revalidate",
            "s_maxage",
            "stale_if_error",
            "stale_while_revalidate",
        ):
            api_key = key.replace("_", "-")
            rules = [{"action": "set_cache_control", "expression": "true", "action_parameters": {key: {}}}]
            client, api = make_client(CURRENT)
            with self.subTest(key=key):
                result = self.run_module(FakeModule(params(rules=rules)), client)

            api.phases.get.assert_not_called()
            api.phases.update.assert_not_called()
            self.assertEqual(
                result["msg"], f"action_parameters key {key!r} must use the Cloudflare API key {api_key!r}"
            )

    def test_accepts_api_cache_control_spellings(self):
        rules = [
            {
                "action": "set_cache_control",
                "expression": "true",
                "enabled": True,
                "action_parameters": {"max-age": {"operation": "set", "value": 60}},
            }
        ]
        client, api = make_client(CURRENT, updated={**CURRENT, "rules": rules})

        result = self.run_module(FakeModule(params(rules=rules)), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=rules)
        self.assertTrue(result["changed"])

    def test_create_requires_name(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(name=None)), client)

        api.create.assert_not_called()
        self.assertEqual(result["msg"], "name is required when creating a ruleset")

    def test_check_mode_does_not_create(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.phases.get.assert_called_once_with(PHASE, zone_id="zone")
        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_creates_ruleset(self):
        client, api = make_client(created=CURRENT)

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        api.create.assert_called_once_with(zone_id="zone", kind="zone", name="default", phase=PHASE, rules=RULES)
        self.assertEqual(result["message"], "Ruleset created")
        self.assertEqual(result["ruleset"], CURRENT)

    def test_omitted_rules_preserve_current_rules(self):
        for current in (CURRENT, {key: value for key, value in CURRENT.items() if key != "rules"}):
            client, api = make_client(current)
            with self.subTest(current=current):
                result = self.run_module(FakeModule(params()), client)

            api.phases.update.assert_not_called()
            self.assertFalse(result["changed"])

    def test_rejects_rename_before_update(self):
        client, api = make_client({**CURRENT, "name": "existing"})

        result = self.run_module(FakeModule(params(name="renamed", rules=[])), client)

        api.phases.update.assert_not_called()
        self.assertEqual(result["msg"], "An existing ruleset cannot be renamed")

    def test_updates_rules_through_phase_entrypoint(self):
        client, api = make_client(CURRENT, updated={**CURRENT, "rules": []})

        result = self.run_module(FakeModule(params(name=None, rules=[])), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=[])
        self.assertEqual(result["message"], "Ruleset updated")

    def test_deletes_entrypoint_ruleset_by_id(self):
        client, api = make_client(CURRENT)

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("ruleset", zone_id="zone")
        self.assertTrue(result["changed"])

    def test_absent_ruleset_is_unchanged(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_a_response_for_the_wrong_phase(self):
        client, _ignored = make_client(created={**CURRENT, "phase": "http_request_transform"})

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong ruleset")

    def test_rejects_update_response_with_wrong_rules(self):
        client, _ignored = make_client({**CURRENT, "rules": []}, updated={**CURRENT, "rules": []})

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        self.assertIn("did not apply", result["msg"])


HEADER_RULE = {
    "enabled": True,
    "action": "rewrite",
    "expression": "true",
    "action_parameters": {
        "headers": {
            "X-Keep": {"operation": "set", "value": "yes"},
            "Authorization": {"operation": "set", "value": "Bearer secret"},
        }
    },
}


class RulesetHeaderTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_removing_a_header_is_a_change(self):
        current = {**CURRENT, "rules": [HEADER_RULE]}
        desired = [{**HEADER_RULE, "action_parameters": {"headers": {"X-Keep": {"operation": "set", "value": "yes"}}}}]
        client, api = make_client(current, updated={**CURRENT, "rules": desired})

        result = self.run_module(FakeModule(params(rules=desired)), client)

        api.phases.update.assert_called_once()
        self.assertTrue(result["changed"])

    def test_returns_header_values(self):
        client, api = make_client({**CURRENT, "rules": [HEADER_RULE]})

        result = self.run_module(FakeModule(params(rules=[HEADER_RULE])), client)

        api.phases.update.assert_not_called()
        headers = result["ruleset"]["rules"][0]["action_parameters"]["headers"]
        self.assertEqual(headers, HEADER_RULE["action_parameters"]["headers"])

    def test_removing_a_skip_rule_entry_is_a_change(self):
        skip = {
            "enabled": True,
            "action": "skip",
            "expression": "true",
            "action_parameters": {"rules": {"a": ["1"], "b": ["2"]}},
        }
        desired = [{**skip, "action_parameters": {"rules": {"a": ["1"]}}}]
        client, api = make_client({**CURRENT, "rules": [skip]}, updated={**CURRENT, "rules": desired})

        result = self.run_module(FakeModule(params(rules=desired)), client)

        api.phases.update.assert_called_once()
        self.assertTrue(result["changed"])

    def test_rule_without_enabled_does_not_match_a_disabled_rule(self):
        disabled = {"ref": "keep", "action": "block", "expression": "true", "enabled": False}
        requested = {"ref": "keep", "action": "block", "expression": "true"}
        client, api = make_client(
            {**CURRENT, "rules": [disabled]}, updated={**CURRENT, "rules": [{**requested, "enabled": True}]}
        )

        result = self.run_module(FakeModule(params(rules=[requested])), client)

        self.assertEqual(api.phases.update.call_args.kwargs["rules"], [{"enabled": True, **requested}])
        self.assertTrue(result["changed"])
