# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from contextlib import nullcontext
from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import purge_cache
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class PurgeCacheTests(TestCase):
    def test_rejects_empty_cache(self):
        module = FakeModule({"cache": {}, "zone_id": "zone"})

        with (
            patch.object(purge_cache, "AnsibleModule", return_value=module),
            patch.object(purge_cache, "cloudflare_client") as client,
            self.assertRaises(ModuleFail) as raised,
        ):
            purge_cache.main()

        client.assert_not_called()
        self.assertEqual(raised.exception.values["msg"], "cache must not be empty")

    def test_check_mode_does_not_purge(self):
        module = FakeModule(
            {"cache": {"purge_everything": True}, "zone_id": "zone"},
            check_mode=True,
        )

        with (
            patch.object(purge_cache, "AnsibleModule", return_value=module),
            patch.object(purge_cache, "post_result") as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            purge_cache.main()

        post.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_purges_cache(self):
        module = FakeModule({"cache": {"purge_everything": True}, "zone_id": "zone"})
        result = {"id": "zone"}

        with (
            patch.object(purge_cache, "AnsibleModule", return_value=module),
            patch.object(
                purge_cache,
                "cloudflare_client",
                return_value=nullcontext({}),
            ),
            patch.object(purge_cache, "post_result", return_value=result) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            purge_cache.main()

        post.assert_called_once_with(
            {},
            "/zones/zone/purge_cache",
            {"purge_everything": True},
        )
        self.assertEqual(raised.exception.values["purge_cache"], result)
