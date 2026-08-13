# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import pages_projects_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class PagesProjectsInfoTests(TestCase):
    def test_lists_projects(self):
        module = FakeModule({"account_id": "account"})
        projects = [
            {
                "name": "docs",
                "build_config": {"web_analytics_token": "analytics-secret"},
                "deployment_configs": {
                    "production": {"env_vars": {"TOKEN": {"type": "secret_text", "value": "secret"}}}
                },
                "canonical_deployment": {
                    "build_config": {"web_analytics_token": "canonical-analytics"},
                    "env_vars": {
                        "CANONICAL_TOKEN": {
                            "type": "secret_text",
                            "value": "canonical-secret",
                        }
                    },
                },
                "latest_deployment": {
                    "build_config": {"web_analytics_token": "latest-analytics"},
                    "env_vars": {
                        "LATEST_TOKEN": {
                            "type": "secret_text",
                            "value": "latest-secret",
                        }
                    },
                },
                "unexpected": [
                    {
                        "web_analytics_token": "unexpected-analytics",
                        "variable": {
                            "type": "secret_text",
                            "value": "unexpected-secret",
                        },
                    }
                ],
            }
        ]

        with (
            patch.object(
                pages_projects_info,
                "list_all",
                return_value=projects,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects_info.list_resources(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/pages/projects",
            per_page=10,
        )
        self.assertEqual(
            raised.exception.values["pages_projects"][0]["deployment_configs"]["production"]["env_vars"]["TOKEN"],
            {"type": "secret_text"},
        )
        self.assertNotIn(
            "web_analytics_token",
            raised.exception.values["pages_projects"][0]["build_config"],
        )
        for field, variable in (
            ("canonical_deployment", "CANONICAL_TOKEN"),
            ("latest_deployment", "LATEST_TOKEN"),
        ):
            self.assertEqual(
                raised.exception.values["pages_projects"][0][field]["env_vars"][variable],
                {"type": "secret_text"},
            )
            self.assertNotIn(
                "web_analytics_token",
                raised.exception.values["pages_projects"][0][field]["build_config"],
            )
        self.assertEqual(
            projects[0]["deployment_configs"]["production"]["env_vars"]["TOKEN"]["value"],
            "secret",
        )
        self.assertEqual(projects[0]["build_config"]["web_analytics_token"], "analytics-secret")
        self.assertEqual(
            projects[0]["latest_deployment"]["env_vars"]["LATEST_TOKEN"]["value"],
            "latest-secret",
        )
        self.assertEqual(
            projects[0]["latest_deployment"]["build_config"]["web_analytics_token"],
            "latest-analytics",
        )
        self.assertEqual(
            raised.exception.values["pages_projects"][0]["unexpected"],
            [{"variable": {"type": "secret_text"}}],
        )
        self.assertEqual(
            projects[0]["unexpected"][0]["variable"]["value"],
            "unexpected-secret",
        )
