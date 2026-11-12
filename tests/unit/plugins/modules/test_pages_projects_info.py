# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import pages_projects_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
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

        client = Mock()
        client.pages.projects.list.return_value = iter(projects)

        with self.assertRaises(ModuleExit) as raised:
            pages_projects_info.run(module, client)

        client.pages.projects.list.assert_called_once_with(account_id="account", per_page=10)
        self.assertEqual(raised.exception.values, {"changed": False, "pages_projects": projects})

    def test_rejects_projects_without_name(self):
        client = Mock()
        client.pages.projects.list.return_value = [{"id": "project"}]

        with self.assertRaises(ModuleFail):
            pages_projects_info.run(FakeModule({"account_id": "account"}), client)
