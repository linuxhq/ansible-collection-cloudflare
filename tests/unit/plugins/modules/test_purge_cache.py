# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import purge_cache
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {"api_token": "token", "cache": {"purge_everything": True}, "zone_id": "zone"}
    values.update(updates)
    return values


class PurgeCacheTests(TestCase):
    def run_main(self, module):
        with (
            patch.object(purge_cache, "AnsibleModule", return_value=module),
            patch.object(purge_cache, "cloudflare_client") as client,
            self.assertRaises((ModuleExit, ModuleFail)) as raised,
        ):
            purge_cache.main()

        return raised.exception.values, client

    def run_module(self, module, purged):
        client = Mock()
        client.cache.purge.return_value = purged
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            purge_cache.run(module, client)

        return raised.exception.values, client.cache.purge

    def test_rejects_empty_cache(self):
        result, client = self.run_main(FakeModule(params(cache={})))

        client.assert_not_called()
        self.assertEqual(result["msg"], "cache must not be empty")

    def test_rejects_unsupported_keys_before_opening_a_client(self):
        for check_mode in (False, True):
            with self.subTest(check_mode=check_mode):
                module = FakeModule(params(cache={"purge_everything": True, "everything": True}), check_mode)

                result, client = self.run_main(module)

                client.assert_not_called()
                self.assertIn("Unsupported cache keys: everything", result["msg"])

    def test_check_mode_does_not_purge(self):
        result, client = self.run_main(FakeModule(params(), check_mode=True))

        client.assert_not_called()
        self.assertTrue(result["changed"])
        self.assertEqual(result["message"], "Cache would be purged")

    def test_check_mode_validates_identifiers_without_opening_a_client(self):
        result, client = self.run_main(FakeModule(params(zone_id=" "), check_mode=True))

        client.assert_not_called()
        self.assertEqual(result["msg"], "zone_id must not be empty")

    def test_purges_cache(self):
        cache = {"files": ["https://example.com/a.css"], "tags": ["a"]}

        result, purge = self.run_module(FakeModule(params(cache=cache)), {"id": "zone"})

        purge.assert_called_once_with(zone_id="zone", files=["https://example.com/a.css"], tags=["a"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["purge_cache"], {"id": "zone"})

    def test_rejects_response_for_wrong_zone(self):
        for purged in (None, {"id": "other"}):
            with self.subTest(purged=purged):
                result, _ignored = self.run_module(FakeModule(params()), purged)

                self.assertIn("cache purge", result["msg"])
