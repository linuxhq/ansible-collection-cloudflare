# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pages_projects
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "docs",
        "production_branch": "main",
        "rotate_secrets": False,
        "domains": None,
    }
    values.update(updates)
    return values


class PagesProjectsTests(TestCase):
    def test_secret_values_are_ignored_without_mutating_payload(self):
        payload = {
            "deployment_configs": {
                "production": {
                    "env_vars": {
                        "TOKEN": {"type": "secret_text", "value": "secret"},
                        "MODE": {"type": "plain_text", "value": "prod"},
                    }
                }
            }
        }

        comparable = pages_projects.comparable_payload(payload)

        self.assertNotIn(
            "value",
            comparable["deployment_configs"]["production"]["env_vars"]["TOKEN"],
        )
        self.assertEqual(
            payload["deployment_configs"]["production"]["env_vars"]["TOKEN"]["value"],
            "secret",
        )

    def test_removed_environment_variables_are_sent_as_null(self):
        payload = {
            "deployment_configs": {
                "production": {"env_vars": {"KEEP": {"value": "yes"}}}
            }
        }
        current = {
            "deployment_configs": {
                "production": {
                    "env_vars": {
                        "KEEP": {"value": "yes"},
                        "REMOVE": {"value": "old"},
                    }
                }
            }
        }

        merged = pages_projects.payload_with_removed_env_vars(payload, current)

        self.assertIsNone(
            merged["deployment_configs"]["production"]["env_vars"]["REMOVE"]
        )
        self.assertNotIn(
            "REMOVE",
            payload["deployment_configs"]["production"]["env_vars"],
        )

    def test_create_requires_production_branch(self):
        module = FakeModule(params(production_branch=None))

        with (
            patch.object(pages_projects, "get_result", return_value=None),
            patch.object(pages_projects, "post_result") as post,
            self.assertRaises(ModuleFail) as raised,
        ):
            pages_projects.ensure_present(module, {})

        post.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "production_branch is required when creating a Pages project",
        )

    def test_adds_only_missing_unique_domains(self):
        module = FakeModule(
            params(
                domains=[
                    {"name": "docs.example.com"},
                    {"name": "new.example.com"},
                    {"name": "new.example.com"},
                ]
            )
        )
        current = {
            "name": "docs",
            "production_branch": "main",
            "domains": ["docs.example.com"],
        }

        with (
            patch.object(pages_projects, "get_result", return_value=current),
            patch.object(
                pages_projects,
                "list_all",
                return_value=[{"name": "docs.example.com"}],
            ),
            patch.object(
                pages_projects,
                "post_result",
                return_value={"name": "new.example.com"},
            ) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects.ensure_present(module, {})

        post.assert_called_once_with(
            {},
            "/accounts/account/pages/projects/docs/domains",
            {"name": "new.example.com"},
        )
        self.assertTrue(raised.exception.values["changed"])
