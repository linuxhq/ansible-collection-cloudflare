# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

TARGETS = [{"target": "url", "constraint": {"value": "example.com/*"}}]


def params(**updates):
    values = {
        "zone_id": "zone",
        "actions": [{"id": "always_use_https"}],
        "targets": TARGETS,
        "priority": None,
        "status": None,
    }
    values.update(updates)
    return values


class PageRulesTests(TestCase):
    def test_rejects_malformed_targets(self):
        for targets in ({}, ["invalid"]):
            module = FakeModule(params())

            with (
                self.subTest(targets=targets),
                patch.object(
                    pagerules, "list_all", return_value=[{"targets": targets}]
                ),
                self.assertRaises(ModuleFail) as raised,
            ):
                pagerules.find_pagerule(module, {})

            self.assertIn("malformed page rule", raised.exception.values["msg"])

    def test_rejects_ambiguous_target_match(self):
        module = FakeModule(params())

        with (
            patch.object(
                pagerules,
                "list_all",
                return_value=[
                    {"id": "one", "targets": TARGETS},
                    {"id": "two", "targets": TARGETS},
                ],
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            pagerules.find_pagerule(module, {})

        self.assertIn("Multiple page rules", raised.exception.values["msg"])

    def test_create_defaults_status_to_active(self):
        module = FakeModule(params())
        created = {
            "id": "rule",
            "actions": [{"id": "always_use_https"}],
            "status": "active",
            "targets": TARGETS,
        }

        with (
            patch.object(pagerules, "list_all", return_value=[]),
            patch.object(pagerules, "post_result", return_value=created) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules.ensure_present(module, {})

        post.assert_called_once_with(
            {},
            "/zones/zone/pagerules",
            {
                "actions": [{"id": "always_use_https"}],
                "status": "active",
                "targets": TARGETS,
            },
        )
        self.assertEqual(raised.exception.values["pagerule"], created)

    def test_rejects_a_create_response_with_different_targets(self):
        module = FakeModule(params())

        with (
            patch.object(pagerules, "list_all", return_value=[]),
            patch.object(
                pagerules,
                "post_result",
                return_value={"id": "rule", "targets": []},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            pagerules.ensure_present(module, {})

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare did not apply the requested page rule",
        )

    def test_omitted_status_and_priority_preserve_current_values(self):
        current = {
            "id": "rule",
            "actions": [{"id": "always_use_https"}],
            "priority": 10,
            "status": "disabled",
            "targets": TARGETS,
        }
        module = FakeModule(params())

        with (
            patch.object(pagerules, "list_all", return_value=[current]),
            patch.object(pagerules, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_nested_provider_fields_do_not_cause_change(self):
        current = {
            "id": "rule",
            "actions": [{"id": "always_use_https", "provider_default": True}],
            "targets": [
                {
                    "target": "url",
                    "constraint": {
                        "value": "example.com/*",
                        "provider_default": True,
                    },
                }
            ],
        }
        module = FakeModule(params())

        with (
            patch.object(pagerules, "list_all", return_value=[current]),
            patch.object(pagerules, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_check_mode_does_not_delete_matching_rule(self):
        current = {"id": "rule", "targets": TARGETS}
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(pagerules, "list_all", return_value=[current]),
            patch.object(pagerules, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
