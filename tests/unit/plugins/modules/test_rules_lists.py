# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import rules_lists
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class ApiConnectionError(Exception):
    pass


class ApiStatusError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


ERRORS = SimpleNamespace(
    APIConnectionError=ApiConnectionError,
    APIStatusError=ApiStatusError,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


def params(**updates):
    values = {
        "account_id": "account",
        "name": "addresses",
        "kind": "ip",
        "description": None,
        "elements": None,
        "operation_timeout": 30,
    }
    values.update(updates)
    return values


class RulesListsTests(TestCase):
    def test_normalizes_metadata_defaults_and_duplicates(self):
        items = [
            {
                "id": "provider-id",
                "comment": "",
                "redirect": {
                    "source_url": "example.com",
                    "status_code": 301,
                    "preserve_path_suffix": True,
                },
            },
            {"redirect": {"source_url": "example.com"}},
        ]

        self.assertEqual(
            rules_lists.normalize_items(items),
            [{"redirect": {"source_url": "example.com"}}],
        )

    def test_submit_retries_pending_operation_within_deadline(self):
        pending = ApiStatusError("bulk operation pending", status_code=409)

        with (
            patch.object(rules_lists, "cloudflare", ERRORS),
            patch.object(
                rules_lists,
                "put_result",
                side_effect=[pending, {"operation_id": "operation"}],
            ) as put,
            patch.object(
                rules_lists.time,
                "monotonic",
                side_effect=[1, 2, 3],
            ),
            patch.object(rules_lists.time, "sleep") as sleep,
        ):
            result = rules_lists.submit_items(
                {},
                "account",
                "list",
                [{"ip": "192.0.2.1"}],
                30,
            )

        self.assertEqual(result, {"operation_id": "operation"})
        self.assertEqual(put.call_count, 2)
        sleep.assert_called_once_with(rules_lists.OPERATION_POLL_SECONDS)

    def test_wait_rejects_missing_operation_identifier(self):
        module = FakeModule({})

        with self.assertRaises(ModuleFail) as raised:
            rules_lists.wait_for_operation(module, {}, "account", {}, 30)

        self.assertEqual(
            raised.exception.values["msg"],
            "Rules list items submission did not return an operation id",
        )

    def test_wait_returns_completed_operation(self):
        module = FakeModule({})
        completed = {"id": "operation", "status": "completed"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            patch.object(rules_lists, "get_result", return_value=completed) as get,
        ):
            result = rules_lists.wait_for_operation(
                module,
                {},
                "account",
                {"operation_id": "operation"},
                30,
            )

        get.assert_called_once_with(
            {},
            "/accounts/account/rules/lists/bulk_operations/operation",
            default={},
            timeout=29,
        )
        self.assertEqual(result, completed)

    def test_wait_rejects_unknown_operation_status(self):
        module = FakeModule({})

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            patch.object(
                rules_lists,
                "get_result",
                return_value={"id": "operation", "status": "unknown"},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(
                module,
                {},
                "account",
                {"operation_id": "operation"},
                30,
            )

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned an unknown Rules list operation status",
        )

    def test_check_mode_does_not_create(self):
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(rules_lists, "find_by_field", return_value=None),
            patch.object(rules_lists, "post_result") as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, {})

        post.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_existing_list_without_managed_items_is_unchanged(self):
        module = FakeModule(params())
        current = {
            "id": "list",
            "name": "addresses",
            "description": "current",
        }

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_generated_sdk_iterator_reads_all_current_items(self):
        module = FakeModule(params(elements=[{"ip": "192.0.2.1"}, {"ip": "192.0.2.2"}]))
        current = {"id": "list", "name": "addresses", "num_items": 2}
        client = Mock()
        client.rules.lists.items.list.return_value = [
            Model({"ip": "192.0.2.1"}),
            Model({"ip": "192.0.2.2"}),
        ]

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "submit_items") as submit,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, client)

        client.rules.lists.items.list.assert_called_once_with(
            "list",
            account_id="account",
            per_page=rules_lists.ITEMS_PER_PAGE,
        )
        submit.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])
