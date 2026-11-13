# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.testing import patch_module_args

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
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

    def run_ansible_module(self, cache):
        client = Mock()
        client.cache.purge.return_value = {"id": "zone"}
        context = Mock()
        context.__enter__ = Mock(return_value=client)
        context.__exit__ = Mock(return_value=False)

        def exit_json(_module, **values):
            raise ModuleExit(values)

        def fail_json(_module, **values):
            raise ModuleFail(values)

        with (
            patch_module_args(params(cache=cache)),
            patch.object(AnsibleModule, "exit_json", exit_json),
            patch.object(AnsibleModule, "fail_json", fail_json),
            patch.object(purge_cache, "cloudflare_client", return_value=context),
            self.assertRaises((ModuleExit, ModuleFail)) as raised,
        ):
            purge_cache.main()

        return raised.exception.values, client.cache.purge

    def test_rejects_unsupported_keys_before_opening_a_client(self):
        result, purge = self.run_ansible_module({"purge_everything": True, "everything": True})

        purge.assert_not_called()
        self.assertIn("Unsupported parameters", result["msg"])
        self.assertIn("everything", result["msg"])

    def test_rejects_cache_without_values(self):
        result, purge = self.run_ansible_module({"tags": None})

        purge.assert_not_called()
        self.assertEqual(result["msg"], "cache must not be empty")

    def test_sends_only_set_cache_options_with_their_types(self):
        files = ["https://example.com/a.css", {"url": "https://example.com/", "headers": {"Accept-Language": "en"}}]

        result, purge = self.run_ansible_module({"purge_everything": "true", "files": files})

        purge.assert_called_once_with(zone_id="zone", purge_everything=True, files=files)
        self.assertTrue(result["changed"])

    def test_check_mode_reports_missing_sdk(self):
        with patch.object(cloudflare_utils, "Cloudflare", None):
            result, client = self.run_main(FakeModule(params(), check_mode=True))

        client.assert_not_called()
        self.assertEqual(result["missing_python_package"], "cloudflare")

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
