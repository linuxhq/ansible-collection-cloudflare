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
    def test_encodes_project_path_segments(self):
        self.assertEqual(
            pages_projects.item_endpoint("account/id", "docs/site"),
            "/accounts/account%2Fid/pages/projects/docs%2Fsite",
        )

    def test_secret_values_are_ignored_without_mutating_payload(self):
        payload = {
            "build_config": {"web_analytics_token": "analytics-secret"},
            "deployment_configs": {
                "production": {
                    "env_vars": {
                        "TOKEN": {"type": "secret_text", "value": "secret"},
                        "MODE": {"type": "plain_text", "value": "prod"},
                    }
                }
            },
        }

        comparable = pages_projects.redact_pages_secrets(payload)

        self.assertNotIn(
            "value",
            comparable["deployment_configs"]["production"]["env_vars"]["TOKEN"],
        )
        self.assertEqual(
            payload["deployment_configs"]["production"]["env_vars"]["TOKEN"]["value"],
            "secret",
        )
        self.assertNotIn("web_analytics_token", comparable["build_config"])
        self.assertEqual(payload["build_config"]["web_analytics_token"], "analytics-secret")

    def test_removed_environment_variables_are_sent_as_null(self):
        payload = {"deployment_configs": {"production": {"env_vars": {"KEEP": {"value": "yes"}}}}}
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

        self.assertIsNone(merged["deployment_configs"]["production"]["env_vars"]["REMOVE"])
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

    def test_rotation_requires_credentials(self):
        for updates in (
            {},
            {"deployment_configs": {"production": {"env_vars": {"MODE": {"type": "plain_text", "value": "prod"}}}}},
        ):
            module = FakeModule(params(rotate_secrets=True, **updates))

            with (
                self.subTest(updates=updates),
                patch.object(pages_projects, "get_result") as get,
                self.assertRaises(ModuleFail) as raised,
            ):
                pages_projects.ensure_present(module, {})

            get.assert_not_called()
            self.assertEqual(
                raised.exception.values["msg"],
                "rotate_secrets requires a secret_text value or build_config.web_analytics_token",
            )

    def test_rejects_invalid_requested_domains_before_api_calls(self):
        module = FakeModule(params(domains=[{"name": " invalid.example.com"}]))

        with (
            patch.object(pages_projects, "get_result") as get,
            self.assertRaises(ModuleFail) as raised,
        ):
            pages_projects.ensure_present(module, {})

        get.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "Each Pages project domain requires a valid name",
        )

        with (
            patch.object(pages_projects, "get_result") as get,
            self.assertRaises(ModuleFail),
        ):
            pages_projects.ensure_absent(module, {})

        get.assert_not_called()

    def test_redacts_secret_values_from_result(self):
        module = FakeModule(
            params(
                deployment_configs={"production": {"env_vars": {"TOKEN": {"type": "secret_text", "value": "secret"}}}}
            )
        )
        project = {"name": "docs", **module.params}

        with (
            patch.object(pages_projects, "get_result", return_value=None),
            patch.object(pages_projects, "post_result", return_value=project),
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects.ensure_present(module, {})

        secret = raised.exception.values["pages_project"]["deployment_configs"]["production"]["env_vars"]["TOKEN"]
        self.assertEqual(secret, {"type": "secret_text"})

    def test_rotates_web_analytics_token(self):
        module = FakeModule(
            params(
                build_config={"web_analytics_token": "new-secret"},
                rotate_secrets=True,
            )
        )
        current = {"name": "docs", "production_branch": "main"}

        with (
            patch.object(pages_projects, "get_result", return_value=current),
            patch.object(
                pages_projects,
                "patch_result",
                return_value={"name": "docs", "production_branch": "main"},
            ) as patched,
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects.ensure_present(module, {})

        patched.assert_called_once_with(
            {},
            "/accounts/account/pages/projects/docs",
            {
                "name": "docs",
                "production_branch": "main",
                "build_config": {"web_analytics_token": "new-secret"},
            },
        )
        self.assertTrue(raised.exception.values["changed"])

    def test_write_only_analytics_token_does_not_force_rotation(self):
        module = FakeModule(params(build_config={"web_analytics_token": "write-only"}))
        current = {
            "name": "docs",
            "production_branch": "main",
            "build_config": {"build_command": "npm run build"},
        }

        with (
            patch.object(pages_projects, "get_result", return_value=current),
            patch.object(pages_projects, "patch_result") as patched,
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects.ensure_present(module, {})

        patched.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_empty_build_config_remains_managed(self):
        self.assertEqual(
            pages_projects.comparable_pages_payload({"build_config": {}}),
            {"build_config": {}},
        )

    def test_rejects_update_response_with_wrong_branch(self):
        module = FakeModule(params(production_branch="release"))
        current = {"name": "docs", "production_branch": "main"}

        with (
            patch.object(pages_projects, "get_result", return_value=current),
            patch.object(pages_projects, "patch_result", return_value=current),
            self.assertRaises(ModuleFail) as raised,
        ):
            pages_projects.ensure_present(module, {})

        self.assertIn("did not apply", raised.exception.values["msg"])

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

    def test_rejects_malformed_project_domains(self):
        for domains in ("docs.example.com", [" docs.example.com "]):
            module = FakeModule(params(domains=[{"name": "new.example.com"}]))

            with (
                self.subTest(domains=domains),
                patch.object(
                    pages_projects,
                    "get_result",
                    return_value={
                        "name": "docs",
                        "production_branch": "main",
                        "domains": domains,
                    },
                ),
                patch.object(pages_projects, "list_all", return_value=[]),
                self.assertRaises(ModuleFail) as raised,
            ):
                pages_projects.ensure_present(module, {})

            self.assertEqual(
                raised.exception.values["msg"],
                "Cloudflare API returned malformed Pages domain data",
            )
