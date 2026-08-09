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
        projects = [{"name": "docs"}]

        with (
            patch.object(
                pages_projects_info,
                "list_all",
                return_value=projects,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            pages_projects_info.list(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/pages/projects",
            per_page=10,
        )
        self.assertEqual(raised.exception.values["pages_projects"], projects)
