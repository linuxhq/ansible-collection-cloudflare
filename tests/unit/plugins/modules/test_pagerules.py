# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
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
    def test_create_defaults_status_to_active(self):
        module = FakeModule(params())
        created = {"id": "rule", "targets": TARGETS}

        with (
            patch.object(pagerules, "get_result", return_value=[]),
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
            patch.object(pagerules, "get_result", return_value=[current]),
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
            patch.object(pagerules, "get_result", return_value=[current]),
            patch.object(pagerules, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            pagerules.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
