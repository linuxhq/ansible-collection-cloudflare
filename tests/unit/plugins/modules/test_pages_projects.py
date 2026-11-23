# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase, skipUnless
from unittest.mock import Mock, call
from urllib.parse import unquote

import cloudflare
import httpx

from ansible_collections.linuxhq.cloudflare.plugins.modules import pages_projects
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FALSY_PAGE_RESULTS,
    OVERLONG_VALUE,
    URL_LENGTH_LIMITED,
    FakeModule,
    ModuleExit,
    ModuleFail,
    failed_create,
    list_response,
    run_through_client,
    sdk_client,
    status_error,
    timeout_error,
)

PROJECT = {"name": "docs", "production_branch": "main"}


def params(**updates):
    values = {
        "account_id": "account",
        "name": "docs",
        "production_branch": "main",
        "build_config": None,
        "deployment_configs": None,
        "rotate_secrets": False,
        "source": None,
        "domains": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(
    projects=(), created=None, edited=None, domains=(), created_domain=None, account_projects=(), other_domains=None
):
    """Return a client whose successive project reads return projects; None means not found.

    other_domains maps another project's name to its domain list.
    """
    client = Mock()
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    api = client.pages.projects
    api.list.return_value = list(account_projects)
    api.get.side_effect = [status_error(404) if project is None else project for project in projects]
    api.create.return_value = created
    api.edit.return_value = edited
    api.domains.list.side_effect = lambda project_name, account_id: list(
        (other_domains or {}).get(project_name, domains)
    )
    api.domains.create.return_value = created_domain

    def get(path, cast_to, options):
        # Domains are read page by page with raw requests; serve them from
        # api.domains.list as one page, so the calls stay observable there.
        _ignored, _accounts, account_id, _pages, _projects, project_name, _domains = path.split("/")
        result = api.domains.list(project_name=unquote(project_name), account_id=unquote(account_id))
        return {"result": list(result), "result_info": {"page": options["params"]["page"], "total_pages": 1}}

    client.get.side_effect = get
    return client, api


class PagesProjectsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            pages_projects.run(module, client)

        return raised.exception.values

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

        comparable = pages_projects.comparable_pages_payload(payload)

        self.assertEqual(
            comparable,
            {
                "build_config": {"web_analytics_token": "analytics-secret"},
                "deployment_configs": {
                    "production": {
                        "env_vars": {
                            "TOKEN": {"type": "secret_text"},
                            "MODE": {"type": "plain_text", "value": "prod"},
                        }
                    }
                },
            },
        )
        self.assertEqual(payload["deployment_configs"]["production"]["env_vars"]["TOKEN"]["value"], "secret")
        self.assertEqual(payload["build_config"]["web_analytics_token"], "analytics-secret")

    def test_create_requires_production_branch(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(production_branch=None)), client)

        api.get.assert_called_once_with(project_name="docs", account_id="account")
        api.create.assert_not_called()
        self.assertEqual(result["msg"], "production_branch is required when creating a Pages project")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_check_mode_does_not_create(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rotation_without_credentials_changes_nothing(self):
        # Nothing secret is requested, so rotation has nothing to resend.
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(rotate_secrets=True)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_name_and_production_branch_fail_before_any_request(self):
        for updates, message in (
            ({"name": ""}, "name must not be empty"),
            ({"name": "", "state": "absent"}, "name must not be empty"),
            ({"production_branch": ""}, "production_branch must not be empty"),
        ):
            with self.subTest(updates=updates):
                client, _ignored = client_with([PROJECT])

                result = self.run_module(FakeModule(params(**updates)), client)

                self.assertEqual(result["msg"], message)
                self.assertEqual(client.mock_calls, [])

    def test_padded_production_branch_is_sent(self):
        # Cloudflare stores the branch as sent.
        client, api = client_with([PROJECT], edited={**PROJECT, "production_branch": " main "})

        result = self.run_module(FakeModule(params(production_branch=" main ")), client)

        self.assertEqual(api.edit.call_args.kwargs["production_branch"], " main ")
        self.assertTrue(result["changed"])

    def test_rejects_padded_domain_names_before_api_calls(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(domains=[{"name": " invalid.example.com"}])), client)

        api.get.assert_not_called()
        self.assertIn("may contain only ASCII letters", result["msg"])

    def test_absent_ignores_requested_domain_names(self):
        # Deleting a project sends no domains, so invalid names must not block it.
        client, api = client_with([PROJECT])

        result = self.run_module(
            FakeModule(params(state="absent", domains=[{"name": " invalid"}, {"name": "x.workers.dev"}])), client
        )

        api.delete.assert_called_once_with(project_name="docs", account_id="account")
        self.assertTrue(result["changed"])

    def test_rejects_unsupported_domain_names_before_api_calls(self):
        for name in (
            "p38fix.linuxhq.dev.",
            "bücher.example.com",
            "a_b.example.com",
            "*.example.com",
            "a..example.com",
            ".example.com",
            "-a.example.com",
            "a-.example.com",
            f"{'a' * 64}.example.com",
            ".".join(["a" * 63] * 4) + ".com",
        ):
            for state, check_mode in (("present", False), ("present", True)):
                with self.subTest(name=name, state=state, check_mode=check_mode):
                    client, api = client_with([PROJECT], created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(state=state, domains=[{"name": name}]), check_mode=check_mode), client
                    )

                    self.assertIn("Each Pages project domain name may contain only", result["msg"])
                    self.assertEqual(result["domain"], name)
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()
                    api.domains.create.assert_not_called()

    def test_rejects_provider_invalid_domain_names_before_api_calls(self):
        for name in (
            "localhost",
            "com",
            "a.123",
            "192.0.2.1",
            "pages.dev",
            "other-p39fix.pages.dev",
            "Other.Pages.Dev",
            "workers.dev",
            "p40fix.workers.dev",
            "P40fix.Workers.Dev",
            "p40fix.x",
            "p40fix.test",
            "p40fix.example",
            "p40fix.invalid",
            "p40fix.localhost",
            "p40fix.local",
            "p40fix.Test",
        ):
            for state, check_mode in (("present", False), ("present", True)):
                with self.subTest(name=name, state=state, check_mode=check_mode):
                    client, api = client_with([PROJECT], created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(state=state, domains=[{"name": name}]), check_mode=check_mode), client
                    )

                    self.assertIn("must have at least two labels", result["msg"])
                    self.assertEqual(result["domain"], name)
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()
                    api.domains.create.assert_not_called()

    def test_rejects_invalid_punycode_labels_before_api_calls(self):
        # Cloudflare rejects these when it adds the domain, after the project is created or updated.
        for name in (
            "xn--zz.example.com",
            "xn--a.example.com",
            "xn--abc.example.com",
            "xn--a-ecp.example.com",
            "xn--0.example.com",
            "a.XN--ZZ.example.com",
            "site.xn--zz",
        ):
            for state, check_mode in (("present", False), ("present", True)):
                with self.subTest(name=name, state=state, check_mode=check_mode):
                    client, api = client_with([PROJECT], created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(state=state, domains=[{"name": name}]), check_mode=check_mode), client
                    )

                    self.assertIn("starts with 'xn--' must be the valid punycode form", result["msg"])
                    self.assertEqual(result["domain"], name)
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()
                    api.domains.create.assert_not_called()

    def test_accepts_valid_punycode_labels(self):
        # Cloudflare adds each of these domains.
        for name in (
            "xn--bcher-kva.example.com",
            "XN--BCHER-KVA.example.com",
            "xn--strae-oqa.example.com",
            "xn--zca.example.com",
            "xn--ls8h.example.com",
            "site.xn--p1ai",
        ):
            with self.subTest(name=name):
                client, api = client_with([PROJECT], domains=[{"name": name.lower()}])

                result = self.run_module(FakeModule(params(domains=[{"name": name}])), client)

                self.assertFalse(result["changed"])
                api.domains.create.assert_not_called()

    def test_accepts_domain_names_with_numeric_inner_labels(self):
        for name in (
            "123.example.com",
            "mypages.dev",
            "pages.dev.example.com",
            "myworkers.dev",
            "workers.dev.example.com",
            "test.example.com",
            "p40fix.co.uk",
            "p40fix.onion",
            "p40fix.xn--p1ai",
            "p40fix.trycloudflare.com",
        ):
            with self.subTest(name=name):
                client, api = client_with([PROJECT], domains=[{"name": name}])

                result = self.run_module(FakeModule(params(domains=[{"name": name}])), client)

                self.assertFalse(result["changed"])
                api.domains.create.assert_not_called()

    def test_accepts_domain_names_at_the_length_limits(self):
        for name in (f"{'a' * 63}.example.com", ".".join(["a" * 63] * 3 + ["b" * 61]), "xn--bcher-kva.Example.com"):
            with self.subTest(name=name):
                client, api = client_with([PROJECT], domains=[{"name": name.lower()}])

                result = self.run_module(FakeModule(params(domains=[{"name": name}])), client)

                self.assertFalse(result["changed"])
                api.domains.create.assert_not_called()

    def test_null_bindings_are_deleted(self):
        keep = {"namespace_id": "keep-id"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"kv_namespaces": {"OLD": {"namespace_id": "old-id"}, "KEEP": keep}}},
        }
        desired = {"production": {"kv_namespaces": {"OLD": None, "KEEP": keep}}}
        edited = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"KEEP": keep}}}}
        client, api = client_with([current], edited=edited)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

        client, _ignored = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)
        self.assertIn("did not apply", result["msg"])

    def test_deleting_one_binding_keeps_unmanaged_bindings(self):
        keep = {"namespace_id": "keep-id"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"kv_namespaces": {"OLD": {"namespace_id": "old-id"}, "KEEP": keep}}},
        }
        desired = {"production": {"kv_namespaces": {"OLD": None}}}
        edited = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"KEEP": keep}}}}
        client, _ignored = client_with([current], edited=edited)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertTrue(result["changed"])

        client, api = client_with([edited])
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_build_setting_is_cleared(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_tag": "tag"}}
        cleared = {**PROJECT, "build_config": {"build_command": "make"}}
        desired = {"build_command": "make", "web_analytics_tag": None}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(build_config=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["build_config"], desired)
        self.assertTrue(result["changed"])

        client, api = client_with([cleared])
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_null_for_settings_cloudflare_keeps_before_any_request(self):
        cases = (
            ({"build_config": {"build_caching": None}}, ["build_config.build_caching"]),
            (
                {"deployment_configs": {"production": {"compatibility_date": None, "env_vars": {"A": None}}}},
                ["deployment_configs.production.compatibility_date"],
            ),
            ({"deployment_configs": {"preview": None}}, ["deployment_configs.preview"]),
            (
                {
                    "deployment_configs": {
                        "production": {
                            "always_use_latest_compatibility_date": None,
                            "browsers": None,
                            # Cloudflare accepts it but keeps the stored version.
                            "build_image_major_version": None,
                            "compatibility_flags": None,
                            "env_vars": None,
                            "fail_open": None,
                            "kv_namespaces": None,
                            "limits": None,
                            "placement": None,
                            "usage_model": None,
                        }
                    }
                },
                [
                    "deployment_configs.production.always_use_latest_compatibility_date",
                    "deployment_configs.production.browsers",
                    "deployment_configs.production.build_image_major_version",
                    "deployment_configs.production.compatibility_flags",
                    "deployment_configs.production.env_vars",
                    "deployment_configs.production.fail_open",
                    "deployment_configs.production.kv_namespaces",
                    "deployment_configs.production.limits",
                    "deployment_configs.production.placement",
                    "deployment_configs.production.usage_model",
                ],
            ),
            (
                # Cloudflare keeps a whole binding map set to null.
                {
                    "deployment_configs": {
                        "preview": {
                            "ai_bindings": None,
                            "analytics_engine_datasets": None,
                            "d1_databases": None,
                            "durable_object_namespaces": None,
                            "hyperdrive_bindings": None,
                            "mtls_certificates": None,
                            "queue_producers": None,
                            "r2_buckets": None,
                            "services": None,
                            "vectorize_bindings": None,
                        }
                    }
                },
                [
                    "deployment_configs.preview.ai_bindings",
                    "deployment_configs.preview.analytics_engine_datasets",
                    "deployment_configs.preview.d1_databases",
                    "deployment_configs.preview.durable_object_namespaces",
                    "deployment_configs.preview.hyperdrive_bindings",
                    "deployment_configs.preview.mtls_certificates",
                    "deployment_configs.preview.queue_producers",
                    "deployment_configs.preview.r2_buckets",
                    "deployment_configs.preview.services",
                    "deployment_configs.preview.vectorize_bindings",
                ],
            ),
            (
                {
                    "deployment_configs": {
                        "production": {"env_vars": {"A": {"type": "plain_text", "value": None}, "B": {"type": None}}}
                    }
                },
                ["deployment_configs.production.env_vars.B.type"],
            ),
        )
        for options, unsupported in cases:
            with self.subTest(options=options):
                client, api = client_with([PROJECT])

                result = self.run_module(FakeModule(params(**options)), client)

                self.assertEqual(result["unsupported_settings"], unsupported)
                self.assertIn("does not clear Pages project settings set to null", result["msg"])
                api.get.assert_not_called()
                api.edit.assert_not_called()

    def test_other_null_settings_are_sent(self):
        # Cloudflare rejects or clears these on the only write, or the module reports a value it kept.
        desired = {
            "production": {
                "kv_namespaces": {"NS": {"namespace_id": None}},
                "services": {"S": {"service": "worker", "environment": None}},
            }
        }
        client, api = client_with([PROJECT], edited=PROJECT)

        self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)

    def test_null_settings_cloudflare_clears_converge(self):
        desired = {
            "production": {"wrangler_config_hash": None, "placement": {"mode": None}, "limits": {"cpu_ms": None}}
        }
        current = {
            **PROJECT,
            "deployment_configs": {
                "production": {"wrangler_config_hash": "abc", "placement": {"mode": "smart"}, "limits": {"cpu_ms": 50}}
            },
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"placement": {}}}}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)

        client, api = client_with([cleared])

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_wrangler_config_hash_before_any_request(self):
        # Cloudflare drops it on create and update, so the run never converges.
        for value in ("abc", ""):
            for found in ([PROJECT], [None]):
                with self.subTest(value=value, existing=found != [None]):
                    client, api = client_with(found, created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(deployment_configs={"production": {"wrangler_config_hash": value}})), client
                    )

                    self.assertEqual(
                        result["unsupported_settings"], ["deployment_configs.production.wrangler_config_hash"]
                    )
                    api.get.assert_not_called()

    def test_null_environment_variable_value_is_sent_and_converges(self):
        # Cloudflare stores a null value as "".
        desired = {"production": {"env_vars": {"A": {"type": "plain_text", "value": None}}}}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"env_vars": {"A": {"type": "plain_text", "value": "1"}}}},
        }
        cleared = {
            **PROJECT,
            "deployment_configs": {"production": {"env_vars": {"A": {"type": "plain_text", "value": ""}}}},
        }
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertNotIn("msg", result)
        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)

        client, api = client_with([cleared])

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_service_environment_is_sent_and_converges(self):
        # Cloudflare stores a null environment as "".
        desired = {"production": {"services": {"API": {"service": "worker", "environment": None}}}}
        cleared = {
            **PROJECT,
            "deployment_configs": {"production": {"services": {"API": {"service": "worker", "environment": ""}}}},
        }
        for stored in (None, "production"):
            current = PROJECT
            if stored is not None:
                services = {"API": {"service": "worker", "environment": stored}}
                current = {**PROJECT, "deployment_configs": {"production": {"services": services}}}

            with self.subTest(stored=stored):
                client, api = client_with([current], edited=cleared)

                result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])
                self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)

        client, api = client_with([cleared])

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_empty_settings_cloudflare_does_not_store_before_any_request(self):
        cases = (
            (
                {"preview": {"placement": {"mode": ""}}, "production": {"placement": {"mode": "smart"}}},
                ["deployment_configs.preview.placement.mode"],
            ),
            (
                {"production": {"compatibility_date": ""}},
                ["deployment_configs.production.compatibility_date"],
            ),
            (
                {"preview": {"usage_model": "", "compatibility_date": "2024-01-01"}},
                ["deployment_configs.preview.usage_model"],
            ),
            (
                {"production": {"usage_model": "", "compatibility_date": ""}},
                [
                    "deployment_configs.production.compatibility_date",
                    "deployment_configs.production.usage_model",
                ],
            ),
        )
        for deployment_configs, empty in cases:
            for check_mode in (True, False):
                with self.subTest(deployment_configs=deployment_configs, check_mode=check_mode):
                    client, api = client_with([PROJECT])

                    result = self.run_module(
                        FakeModule(params(deployment_configs=deployment_configs), check_mode=check_mode), client
                    )

                    self.assertEqual(result["empty_settings"], empty)
                    self.assertEqual(
                        result["msg"],
                        "Cloudflare does not store an empty value for these Pages project settings: "
                        f"{', '.join(empty)}; omit them instead",
                    )
                    api.get.assert_not_called()
                    api.edit.assert_not_called()

    def test_rejects_unstored_setting_names_before_any_request(self):
        cases = (
            (
                {"build_config": {"build_command": "true", "build_image_major_version": 3}},
                ["build_config.build_image_major_version"],
            ),
            ({"build_config": {"bogus_key": 1}}, ["build_config.bogus_key"]),
            (
                {"deployment_configs": {"production": {"compatibility_date": "2024-01-01", "bogus_key": 1}}},
                ["deployment_configs.production.bogus_key"],
            ),
            (
                {
                    "build_config": {"bogus_key": 1},
                    "deployment_configs": {"preview": {"bogus_key": 1}, "production": {"other": 2}},
                },
                [
                    "build_config.bogus_key",
                    "deployment_configs.preview.bogus_key",
                    "deployment_configs.production.other",
                ],
            ),
        )
        for options, unsupported in cases:
            for found, check_mode in (([PROJECT], False), ([PROJECT], True), ([None], False)):
                with self.subTest(options=options, existing=found != [None], check_mode=check_mode):
                    client, api = client_with(found, created=PROJECT, edited=PROJECT)

                    result = self.run_module(FakeModule(params(**options), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_settings"], unsupported)
                    self.assertEqual(
                        result["msg"],
                        f"Cloudflare does not store these Pages project settings: {', '.join(unsupported)}",
                    )
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()

    def test_unstored_setting_names_set_to_null_count_as_omitted(self):
        # Cloudflare drops an unknown setting set to null, so it is not rejected.
        build_config = {"build_command": "true", "bogus_key": None}
        deployment = {
            "compatibility_date": "2024-01-01",
            "bogus_key": None,
            "placement": {"mode": "smart", "bogus": None},
            "env_vars": {"A": {"type": "plain_text", "value": "x", "extra": None}},
            "kv_namespaces": {"KV": {"namespace_id": "id", "bogus": None}},
        }
        stored = {
            "compatibility_date": "2024-01-01",
            "placement": {"mode": "smart"},
            "env_vars": {"A": {"type": "plain_text", "value": "x"}},
            "kv_namespaces": {"KV": {"namespace_id": "id"}},
        }
        project = {
            **PROJECT,
            "build_config": {"build_command": "true"},
            "deployment_configs": {"preview": stored, "production": stored},
        }
        options = params(
            build_config=build_config, deployment_configs={"preview": deployment, "production": deployment}
        )
        for check_mode in (False, True):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([PROJECT], edited=project)

                result = self.run_module(FakeModule(options, check_mode=check_mode), client)

                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])

        client, api = client_with([project])

        result = self.run_module(FakeModule(options), client)

        self.assertNotIn("msg", result)
        self.assertFalse(result["changed"])
        api.edit.assert_not_called()

    def test_stored_setting_names_are_sent(self):
        build_config = dict.fromkeys(pages_projects.BUILD_SETTINGS, "value")
        build_config.pop("web_analytics_token")
        deployment = {"build_image_major_version": 3, "compatibility_date": "2024-01-01"}
        project = {
            **PROJECT,
            "build_config": build_config,
            "deployment_configs": {"preview": deployment, "production": deployment},
        }
        client, api = client_with([{**PROJECT, "build_config": {}}], edited=project)

        result = self.run_module(
            FakeModule(
                params(
                    build_config=build_config,
                    deployment_configs={"preview": deployment, "production": deployment},
                )
            ),
            client,
        )

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        api.edit.assert_called_once()

    def test_rejects_unstored_nested_setting_names_before_any_request(self):
        cases = (
            (
                {"production": {"env_vars": {"A": {"type": "plain_text", "value": "x", "extra": 1}}}},
                ["deployment_configs.production.env_vars.A.extra"],
            ),
            (
                {"preview": {"kv_namespaces": {"KV": {"namespace_id": "id", "bogus": 1}}}},
                ["deployment_configs.preview.kv_namespaces.KV.bogus"],
            ),
            (
                {"production": {"vectorize_bindings": {"V": {"index_name": "idx", "bogus": 1}}}},
                ["deployment_configs.production.vectorize_bindings.V.bogus"],
            ),
            ({"production": {"browsers": {"B": {"bogus": 1}}}}, ["deployment_configs.production.browsers.B.bogus"]),
            (
                {"production": {"placement": {"mode": "smart", "bogus": 1}}},
                ["deployment_configs.production.placement.bogus"],
            ),
            ({"preview": {"limits": {"cpu_ms": 50, "bogus": 1}}}, ["deployment_configs.preview.limits.bogus"]),
            (
                {
                    "preview": {"bogus_key": {"extra": 1}, "env_vars": {"A": None, "B": {"extra": 1}}},
                    "production": {"r2_buckets": {"R": {"name": "bucket", "jurisdiction": None, "bogus": None}}},
                },
                ["deployment_configs.preview.bogus_key", "deployment_configs.preview.env_vars.B.extra"],
            ),
        )
        for deployment_configs, unsupported in cases:
            for found, check_mode in (([PROJECT], False), ([PROJECT], True), ([None], False)):
                with self.subTest(
                    deployment_configs=deployment_configs, existing=found != [None], check_mode=check_mode
                ):
                    client, api = client_with(found, created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(deployment_configs=deployment_configs), check_mode=check_mode), client
                    )

                    self.assertEqual(result["unsupported_settings"], unsupported)
                    self.assertEqual(
                        result["msg"],
                        f"Cloudflare does not store these Pages project settings: {', '.join(unsupported)}",
                    )
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()

    def test_other_binding_entry_fields_are_sent(self):
        # Whether Cloudflare stores these is unverified, so they are left to it.
        desired = {
            "production": {
                "services": {"S": {"service": "api", "bogus": 1}},
                "r2_buckets": {"R": {"name": "bucket", "bogus": 1}},
                "d1_databases": {"D": {"id": "db", "bogus": 1}},
            }
        }
        client, api = client_with([PROJECT], edited=PROJECT)

        self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)

    def test_stored_nested_setting_names_are_sent(self):
        entries = {
            key: {"X": dict.fromkeys(fields, "value"), "GONE": None}
            for key, fields in pages_projects.DEPLOYMENT_ENTRY_FIELDS.items()
        }
        deployment = {**entries, "limits": {"cpu_ms": 50}, "placement": {"mode": "smart"}}
        stored = {
            **{key: {"X": entry["X"]} for key, entry in entries.items()},
            "limits": {"cpu_ms": 50},
            "placement": {"mode": "smart"},
        }
        client, api = client_with([PROJECT], edited={**PROJECT, "deployment_configs": {"production": stored}})

        result = self.run_module(FakeModule(params(deployment_configs={"production": deployment})), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], {"production": deployment})

    def test_null_r2_jurisdiction_is_sent(self):
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"r2_buckets": {"B": {"name": "bucket", "jurisdiction": "eu"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"r2_buckets": {"B": {"name": "bucket"}}}}}
        desired = {"production": {"r2_buckets": {"B": {"name": "bucket", "jurisdiction": None}}}}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

    def test_empty_string_build_setting_counts_as_cleared(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_tag": ""}}
        client, api = client_with([current])

        result = self.run_module(
            FakeModule(params(build_config={"build_command": "make", "web_analytics_tag": None})), client
        )

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_binding_map_keeps_existing_bindings(self):
        current = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"NS": {"namespace_id": "id"}}}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"kv_namespaces": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_binding_map_matches_a_null_collection(self):
        current = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": None}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"kv_namespaces": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_source_is_unchanged(self):
        client, api = client_with([{**PROJECT, "source": {"type": "github"}}])

        result = self.run_module(FakeModule(params(source={})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_nested_binding_field_is_cleared(self):
        service = {"service": "worker", "environment": "production"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"services": {"API": {**service, "entrypoint": "Main"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"services": {"API": service}}}}
        desired = {"production": {"services": {"API": {**service, "entrypoint": None}}}}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

        client, _ignored = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)
        self.assertIn("did not apply", result["msg"])

    def test_binding_named_env_vars_keeps_omitted_fields(self):
        for binding, stored in (
            ("services", {"service": "worker", "environment": "production", "entrypoint": "Main"}),
            ("r2_buckets", {"name": "bucket", "jurisdiction": "eu"}),
        ):
            with self.subTest(binding=binding):
                current = {**PROJECT, "deployment_configs": {"production": {binding: {"env_vars": stored}}}}
                name = "service" if binding == "services" else "name"
                desired = {"production": {binding: {"env_vars": {name: stored[name]}}}}
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_nested_deletion_only_request_ignores_unmanaged_fields(self):
        service = {"service": "worker", "environment": "production"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"services": {"API": {**service, "entrypoint": "Main"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"services": {"API": service}}}}
        desired = {"production": {"services": {"API": {"entrypoint": None}}}}
        client, _ignored = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertTrue(result["changed"])

        client, api = client_with([cleared])
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_plain_variable_named_like_a_secret_is_compared(self):
        def project(value):
            env_vars = {"web_analytics_token": {"type": "plain_text", "value": value}}
            return {**PROJECT, "deployment_configs": {"production": {"env_vars": env_vars}}}

        client, api = client_with([project("old")], edited=project("new"))

        result = self.run_module(FakeModule(params(deployment_configs=project("new")["deployment_configs"])), client)

        api.edit.assert_called_once()
        self.assertTrue(result["changed"])

    def test_returns_project_values(self):
        deployment_configs = {"production": {"env_vars": {"TOKEN": {"type": "secret_text", "value": "secret"}}}}
        created = {**PROJECT, "deployment_configs": deployment_configs}
        client, api = client_with([None], created=created)

        result = self.run_module(FakeModule(params(deployment_configs=deployment_configs)), client)

        api.create.assert_called_once_with(
            account_id="account", name="docs", production_branch="main", deployment_configs=deployment_configs
        )
        secret = result["pages_project"]["deployment_configs"]["production"]["env_vars"]["TOKEN"]
        self.assertEqual(secret, {"type": "secret_text", "value": "secret"})
        self.assertEqual(result["message"], "Pages project created")

    def test_rotates_web_analytics_token(self):
        client, api = client_with([PROJECT], edited={**PROJECT, "build_config": {"web_analytics_token": "new-secret"}})

        result = self.run_module(
            FakeModule(params(build_config={"web_analytics_token": "new-secret"}, rotate_secrets=True)),
            client,
        )

        api.edit.assert_called_once_with(
            project_name="docs",
            account_id="account",
            name="docs",
            production_branch="main",
            build_config={"web_analytics_token": "new-secret"},
        )
        self.assertTrue(result["changed"])

    def test_changed_analytics_token_is_applied(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_token": "old-token"}}
        desired = {"web_analytics_token": "new-token"}
        updated = {**PROJECT, "build_config": {"build_command": "make", **desired}}
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([current], edited=updated)

                result = self.run_module(FakeModule(params(build_config=desired), check_mode=check_mode), client)

                self.assertTrue(result["changed"])
                if check_mode:
                    api.edit.assert_not_called()
                else:
                    self.assertEqual(api.edit.call_args.kwargs["build_config"], desired)

        client, api = client_with([updated])
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

        client, api = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        self.assertIn("did not apply", result["msg"])

    def test_cleared_analytics_token_matches_null(self):
        for stored in (None, ""):
            with self.subTest(stored=stored):
                client, api = client_with([{**PROJECT, "build_config": {"web_analytics_token": stored}}])

                result = self.run_module(FakeModule(params(build_config={"web_analytics_token": None})), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_empty_build_config_is_unchanged(self):
        client, api = client_with([{**PROJECT, "build_config": {"build_command": "make"}}])

        result = self.run_module(FakeModule(params(build_config={})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_environment_variables_are_sent_as_null(self):
        keep = {"type": "plain_text", "value": "yes"}
        current = {
            **PROJECT,
            "deployment_configs": {
                "production": {"env_vars": {"KEEP": keep, "REMOVE": {"type": "plain_text", "value": "old"}}}
            },
        }
        desired = {"production": {"env_vars": {"KEEP": keep}}}
        client, api = client_with([current], edited={**PROJECT, "deployment_configs": desired})

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        sent = api.edit.call_args.kwargs["deployment_configs"]
        self.assertEqual(sent, {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}})
        self.assertNotIn("REMOVE", desired["production"]["env_vars"])
        self.assertTrue(result["changed"])

    def test_empty_deployment_configs_are_unchanged(self):
        current = {**PROJECT, "deployment_configs": {"production": {"compatibility_date": "2024-01-01"}}}
        for configs in ({}, {"production": {}}):
            with self.subTest(configs=configs):
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(deployment_configs=configs)), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_null_env_vars_match_an_empty_map(self):
        current = {**PROJECT, "deployment_configs": {"production": {"env_vars": None}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"env_vars": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_explicit_null_environment_variables_are_removed(self):
        keep = {"type": "plain_text", "value": "yes"}
        current = {
            **PROJECT,
            "deployment_configs": {
                "production": {"env_vars": {"KEEP": keep, "REMOVE": {"type": "plain_text", "value": "old"}}}
            },
        }
        desired = {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}}
        client, api = client_with(
            [current], edited={**PROJECT, "deployment_configs": {"production": {"env_vars": {"KEEP": keep}}}}
        )

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        sent = api.edit.call_args.kwargs["deployment_configs"]
        self.assertEqual(sent, {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}})
        self.assertTrue(result["changed"])

    def test_rejects_unremoved_environment_variables(self):
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"env_vars": {"REMOVE": {"type": "plain_text", "value": "old"}}}},
        }
        client, _ignored = client_with([current], edited=current)

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"env_vars": {}}})), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Pages project: deployment_configs.production.env_vars.REMOVE "
            'requested null, stored {"type": "plain_text", "value": "old"}',
        )
        self.assertEqual(
            result["differences"],
            [
                {
                    "field": "deployment_configs.production.env_vars.REMOVE",
                    "requested": None,
                    "stored": {"type": "plain_text", "value": "old"},
                }
            ],
        )

    def test_check_mode_does_not_update(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(production_branch="release"), check_mode=True), client)

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_update_response_with_wrong_branch(self):
        client, _ignored = client_with([PROJECT], edited=PROJECT)

        result = self.run_module(FakeModule(params(production_branch="release")), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_not_applied_after_create_reports_the_created_project(self):
        client, _ignored = client_with([None], created=PROJECT)

        result = self.run_module(FakeModule(params(production_branch="release")), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["pages_project"], PROJECT)
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_rejects_project_with_wrong_name(self):
        client, _ignored = client_with([{**PROJECT, "name": "other"}])

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Pages project")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")
        self.assertNotIn("changed", result)

    def test_failed_reread_after_adding_domains_reports_the_written_project(self):
        domain = {"name": "new.example.com"}
        for error in (status_error(500), timeout_error()):
            with self.subTest(error=type(error).__name__):
                client, api = client_with([PROJECT, error], created_domain=domain)

                with self.assertRaises(type(error)) as raised:
                    pages_projects.run(FakeModule(params(domains=[domain])), client)

                api.domains.create.assert_called_once()
                context = raised.exception._cloudflare_context
                self.assertTrue(context["changed"])
                self.assertEqual(context["account_id"], "account")
                self.assertEqual(context["name"], "docs")
                self.assertEqual(context["pages_project"], PROJECT)
                self.assertEqual(context["domains"], [domain])

    def test_adds_only_missing_unique_domains(self):
        domains = [{"name": "docs.example.com"}, {"name": "new.example.com"}, {"name": "new.example.com"}]
        refreshed = {**PROJECT, "domains": ["docs.example.com", "new.example.com"]}
        client, api = client_with(
            [PROJECT, refreshed],
            domains=[{"name": "docs.example.com"}],
            created_domain={"name": "new.example.com"},
        )

        result = self.run_module(FakeModule(params(domains=domains)), client)

        api.domains.list.assert_called_once_with(project_name="docs", account_id="account")
        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertTrue(result["changed"])
        self.assertEqual(result["pages_project"], refreshed)
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_reads_every_page_of_domains(self):
        # Cloudflare returns 20 domains per page, and a project's domains
        # field omits pending custom domains.
        names = [f"d{index}.example.com" for index in range(25)]
        requests = []

        def respond(request):
            requests.append(request)
            path = request.url.path
            if path.endswith("/pages/projects/docs"):
                return httpx.Response(200, json={"success": True, "result": PROJECT})

            if path.endswith("/pages/projects/docs/domains"):
                page = int(request.url.params["page"])
                per_page = int(request.url.params["per_page"])
                result = [{"name": name} for name in names[(page - 1) * per_page : page * per_page]]
                result_info = {"page": page, "per_page": per_page, "total_pages": 2, "total_count": len(names)}
                return httpx.Response(200, json={"success": True, "result": result, "result_info": result_info})

            return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

        with cloudflare.Cloudflare(
            api_token="EXAMPLE-token", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(respond))
        ) as client:
            result = self.run_module(FakeModule(params(domains=[{"name": names[-1]}])), client)

        self.assertNotIn("msg", result)
        self.assertFalse(result["changed"])
        self.assertEqual([request.method for request in requests], ["GET", "GET", "GET"])
        self.assertEqual([request.url.params.get("page") for request in requests], [None, "1", "2"])

    def test_create_recovers_the_project_and_domain_after_lost_responses(self):
        refreshed = {**PROJECT, "domains": ["new.example.com"]}
        client, api = client_with([None, PROJECT, refreshed])
        api.create.side_effect = timeout_error()
        api.domains.create.side_effect = status_error(502)
        api.domains.get.return_value = {"name": "new.example.com"}

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        self.assertEqual(client.with_options.call_args_list, [call(max_retries=0), call(max_retries=0)])
        api.create.assert_called_once()
        api.domains.create.assert_called_once()
        api.domains.get.assert_called_once_with("new.example.com", project_name="docs", account_id="account")
        self.assertEqual(result["message"], "Pages project created")
        self.assertEqual(result["pages_project"], refreshed)
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_failed_lookup_after_a_failed_create_reports_the_create_error(self):
        lookups = (
            httpx.Response(403, json={"success": False, "errors": [{"code": 10000}], "messages": []}),
            httpx.Response(200, json={"success": True, "result": "malformed"}),
            httpx.Response(200, json={"success": True, "result": ["docs"]}),
            httpx.Response(200, json={"success": True, "result": {"production_branch": "main"}}),
            httpx.Response(200, json={"success": True, "result": {**PROJECT, "name": "other"}}),
        )
        for lookup in lookups:
            with self.subTest(lookup=lookup.content):
                result, requests = run_through_client(
                    pages_projects.run,
                    FakeModule({**params(), "api_token": "token"}),
                    failed_create(httpx.Response(404, json={"success": False, "errors": [], "messages": []}), lookup),
                )

                self.assertEqual([method for method, _path in requests], ["GET", "POST", "GET"])
                self.assertEqual(result["msg"], "Cloudflare API request failed while creating the Pages project")
                self.assertEqual(result["status_code"], 500)
                self.assertNotIn("changed", result)

    @skipUnless(URL_LENGTH_LIMITED, "HTTPX builds URLs of any length")
    def test_overlong_name_fails_cleanly(self):
        def respond(request):
            raise AssertionError("no request can be sent")

        result, requests = run_through_client(
            pages_projects.run, FakeModule({**params(name=OVERLONG_VALUE), "api_token": "token"}), respond
        )

        self.assertEqual(requests, [])
        self.assertEqual(result["msg"], "Cloudflare API request failed while gathering the Pages project")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["error"], "InvalidURL: URL too long")
        self.assertNotIn("changed", result)

    def test_failed_domain_lookup_after_a_failed_add_reports_the_add_error(self):
        lookups = (
            httpx.Response(403, json={"success": False, "errors": [{"code": 10000}], "messages": []}),
            httpx.Response(200, json={"success": True, "result": "malformed"}),
            httpx.Response(200, json={"success": True, "result": ["new.example.com"]}),
            httpx.Response(200, json={"success": True, "result": {"name": "other.example.com"}}),
        )
        for lookup in lookups:

            def respond(request, lookup=lookup):
                path = request.url.path
                if request.method == "POST":
                    return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

                if path.endswith("/domains/new.example.com"):
                    return lookup

                if path.endswith("/pages/projects/docs"):
                    return httpx.Response(200, json={"success": True, "result": PROJECT})

                # The account's projects and every domain list are empty.
                return httpx.Response(200, json={"success": True, "result": [], "result_info": {"total_pages": 1}})

            with self.subTest(lookup=lookup.content):
                result, requests = run_through_client(
                    pages_projects.run,
                    FakeModule({**params(domains=[{"name": "new.example.com"}]), "api_token": "token"}),
                    respond,
                )

                self.assertEqual(
                    requests[-2:],
                    [
                        ("POST", "/client/v4/accounts/account/pages/projects/docs/domains"),
                        ("GET", "/client/v4/accounts/account/pages/projects/docs/domains/new.example.com"),
                    ],
                )
                self.assertEqual(result["msg"], "Cloudflare API request failed while adding the Pages project domain")
                self.assertEqual(result["status_code"], 500)
                self.assertNotIn("changed", result)

    def test_domain_names_compare_case_insensitively(self):
        client, api = client_with([PROJECT], domains=[{"name": "docs.example.com"}])

        result = self.run_module(FakeModule(params(domains=[{"name": "Docs.Example.com"}])), client)

        api.list.assert_not_called()
        api.domains.create.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_domain_of_another_project_before_any_write(self):
        account_projects = [{"name": "docs"}, {"name": "active"}, {"name": "other"}]
        other_domains = {
            "active": [{"name": "unrelated.example.com"}],
            "other": [{"name": "Shared.example.com"}],
        }
        for exists, check_mode in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(exists=exists, check_mode=check_mode):
                client, api = client_with(
                    [PROJECT if exists else None],
                    created=PROJECT,
                    edited=PROJECT,
                    account_projects=account_projects,
                    other_domains=other_domains,
                )

                result = self.run_module(
                    FakeModule(
                        params(domains=[{"name": "new.example.com"}, {"name": "Shared.Example.com"}]),
                        check_mode=check_mode,
                    ),
                    client,
                )

                api.list.assert_called_once_with(account_id="account")
                self.assertEqual(
                    [call.kwargs["project_name"] for call in api.domains.list.call_args_list],
                    ["docs", "active", "other"] if exists else ["active", "other"],
                )
                self.assertEqual(result["msg"], "Pages project domain is already attached to another Pages project")
                self.assertEqual(result["domain"], "shared.example.com")
                self.assertEqual(result["project"], "other")
                self.assertEqual(result["name"], "docs")
                api.create.assert_not_called()
                api.edit.assert_not_called()
                api.domains.create.assert_not_called()

    def test_project_deleted_after_listing_owns_no_domains(self):
        refreshed = {**PROJECT, "domains": ["new.example.com"]}
        account_projects = [{"name": "docs"}, {"name": "gone"}, {"name": "other"}]
        client, api = client_with(
            [PROJECT, refreshed],
            created_domain={"name": "new.example.com"},
            account_projects=account_projects,
        )
        other_domains = {"gone": status_error(404), "other": [{"name": "other.example.com"}]}

        def domains_list(project_name, account_id):
            domains = other_domains.get(project_name, [])
            if isinstance(domains, Exception):
                raise domains

            return list(domains)

        api.domains.list.side_effect = domains_list

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        self.assertEqual(
            [call.kwargs["project_name"] for call in api.domains.list.call_args_list], ["docs", "gone", "other"]
        )
        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertTrue(result["changed"])

    def test_dot_segment_name_fails_before_any_request(self):
        for name in (".", ".."):
            for state in ("present", "absent"):
                with self.subTest(name=name, state=state):
                    client, _ignored = client_with()

                    result = self.run_module(FakeModule(params(name=name, state=state)), client)

                    self.assertEqual(result["msg"], "name must not be '.' or '..'")
                    self.assertEqual(client.mock_calls, [])

    def test_pending_domain_of_this_project_skips_the_owner_check(self):
        client, api = client_with([PROJECT], domains=[{"name": "new.example.com"}])

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        api.list.assert_not_called()
        api.domains.list.assert_called_once_with(project_name="docs", account_id="account")
        api.domains.create.assert_not_called()
        self.assertFalse(result["changed"])

    def test_adds_domain_no_other_project_has(self):
        refreshed = {**PROJECT, "domains": ["new.example.com"]}
        account_projects = [{"name": "docs"}, {"name": "other"}]
        client, api = client_with(
            [PROJECT, refreshed],
            created_domain={"name": "new.example.com"},
            account_projects=account_projects,
            other_domains={"other": [{"name": "other.example.com"}]},
        )

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        api.list.assert_called_once_with(account_id="account")
        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertTrue(result["changed"])

    def test_adds_mixed_case_domain_in_lowercase(self):
        refreshed = {**PROJECT, "domains": ["new.example.com"]}
        client, api = client_with([PROJECT, refreshed], created_domain={"name": "new.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "New.Example.com"}])), client)

        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_project_deleted_while_adding_domains_fails_clearly(self):
        client, api = client_with([PROJECT, None], created_domain={"name": "new.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertEqual(result["msg"], "Pages project was deleted while its domains were being added")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_check_mode_does_not_add_domains(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}]), check_mode=True), client)

        api.domains.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_project_domains_field_is_not_read(self):
        # The domain listing holds every custom domain, so the project's domains field is not read.
        project = {**PROJECT, "domains": "invalid"}
        client, api = client_with([project, project], created_domain={"name": "new.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        api.domains.create.assert_called_once()
        self.assertTrue(result["changed"])
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_malformed_domain_listing_names_the_account_and_project(self):
        for page in (None, {"result": "invalid"}):
            with self.subTest(page=page):
                client, _ignored = client_with([PROJECT], domains=[{"name": None}])
                if page is not None:
                    client.get.side_effect = None
                    client.get.return_value = page

                result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

                self.assertEqual(result["msg"], "Cloudflare API returned malformed Pages domain data")
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "docs")

    def test_malformed_project_of_the_account_names_the_owner(self):
        client, _ignored = client_with([PROJECT], account_projects=[{"name": None}])

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed Pages project data")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_malformed_domains_of_another_project_name_it(self):
        client, _ignored = client_with(
            [PROJECT],
            account_projects=[PROJECT, {"name": "other"}],
            other_domains={"other": [{"name": None}]},
        )

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed Pages domain data")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")
        self.assertEqual(result["project"], "other")

    def test_failed_domains_request_of_another_project_names_it(self):
        client, _ignored = client_with([PROJECT], account_projects=[PROJECT, {"name": "other"}])
        get = client.get.side_effect

        def get_or_deny(path, cast_to, options):
            if "/projects/other/" in path:
                raise status_error(403)

            return get(path, cast_to, options)

        client.get.side_effect = get_or_deny

        with self.assertRaises(cloudflare.PermissionDeniedError) as raised:
            pages_projects.run(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        self.assertEqual(
            raised.exception._cloudflare_context,
            {"account_id": "account", "name": "docs", "project": "other"},
        )
        self.assertEqual(
            raised.exception._cloudflare_message,
            "Cloudflare API request failed while gathering Pages project domains",
        )

    def test_absent_project_is_unchanged(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_delete(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(state="absent", domains=[{"name": "a.example.com"}]), True), client)

        api.domains.delete.assert_not_called()
        api.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_deletes_only_the_project(self):
        client, api = client_with([PROJECT], domains=[{"name": "a.example.com"}])

        result = self.run_module(
            FakeModule(params(state="absent", domains=[{"name": "A.Example.com"}, {"name": "b.example.com"}])),
            client,
        )

        api.domains.list.assert_not_called()
        api.domains.delete.assert_not_called()
        api.delete.assert_called_once_with(project_name="docs", account_id="account")
        self.assertEqual(result["message"], "Pages project deleted")
        self.assertTrue(result["changed"])

    def test_lookup_errors_other_than_not_found_propagate(self):
        client = Mock()
        # Retry overrides return the same client so their calls are observable.
        client.with_options.return_value = client
        client.pages.projects.get.side_effect = status_error(403)

        with self.assertRaises(Exception) as raised:
            pages_projects.run(FakeModule(params()), client)

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(
            raised.exception._cloudflare_message,
            "Cloudflare API request failed while gathering the Pages project",
        )

    def test_rejected_domain_after_create_reports_the_created_project(self):
        body = {"success": False, "errors": [{"code": 8000018, "message": "Invalid domain"}], "messages": []}
        client, api = client_with([None], created=PROJECT)
        api.domains.create.side_effect = status_error(400, body)

        with self.assertRaises(cloudflare.BadRequestError) as raised:
            pages_projects.run(FakeModule(params(domains=[{"name": "docs.example.com"}])), client)

        api.create.assert_called_once()
        self.assertEqual(
            raised.exception._cloudflare_context,
            {
                "account_id": "account",
                "name": "docs",
                "changed": True,
                "pages_project": PROJECT,
                "domains": [],
                "domain": "docs.example.com",
            },
        )

    def test_rejected_second_domain_reports_the_first(self):
        first = {"name": "a.example.com"}
        client, api = client_with([PROJECT])
        api.domains.create.side_effect = [first, status_error(400)]

        with self.assertRaises(cloudflare.BadRequestError) as raised:
            pages_projects.run(
                FakeModule(params(domains=[{"name": "a.example.com"}, {"name": "b.example.com"}])), client
            )

        context = raised.exception._cloudflare_context
        self.assertTrue(context["changed"])
        self.assertEqual(context["domains"], [first])
        self.assertEqual(context["domain"], "b.example.com")
        self.assertEqual(context["pages_project"], PROJECT)

    def test_rejected_domain_without_a_write_reports_no_change(self):
        client, api = client_with([PROJECT])
        api.domains.create.side_effect = status_error(400)

        with self.assertRaises(cloudflare.BadRequestError) as raised:
            pages_projects.run(FakeModule(params(domains=[{"name": "a.example.com"}])), client)

        self.assertNotIn("changed", raised.exception._cloudflare_context)

    def test_created_project_with_another_name_reports_the_write(self):
        created = {**PROJECT, "name": "other"}
        client, _api = client_with([None], created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Pages project")
        self.assertTrue(result["changed"])
        self.assertEqual(result["pages_project"], created)
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_wrong_domain_response_reports_the_write(self):
        client, _api = client_with([PROJECT], created_domain={"name": "other.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "a.example.com"}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Pages domain")
        self.assertTrue(result["changed"])
        self.assertEqual(result["domains"], [{"name": "other.example.com"}])
        self.assertEqual(result["pages_project"], PROJECT)

    def test_delete_answered_with_404_counts_as_deleted(self):
        client, api = client_with([PROJECT])
        api.delete.side_effect = status_error(404)

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with(project_name="docs", account_id="account")
        self.assertTrue(result["changed"])
        self.assertEqual(result["message"], "Pages project deleted")
        self.assertEqual(result["pages_project"], PROJECT)

    def test_malformed_deployment_configs_fail_before_any_change(self):
        for deployment_configs in ("production", ["production"]):
            client, api = client_with([{**PROJECT, "deployment_configs": deployment_configs}])
            with self.subTest(deployment_configs=deployment_configs):
                result = self.run_module(FakeModule(params(production_branch="release")), client)

                api.edit.assert_not_called()
                self.assertEqual(
                    result,
                    {
                        "msg": "Cloudflare API returned malformed Pages project data",
                        "account_id": "account",
                        "name": "docs",
                    },
                )

    def test_malformed_written_deployment_configs_report_the_change(self):
        for deployment_configs in ("production", ["production"]):
            written = {**PROJECT, "deployment_configs": deployment_configs}
            for write in ("create", "edit"):
                if write == "create":
                    client, api = client_with([None], created=written)
                else:
                    client, api = client_with([{**PROJECT, "production_branch": "release"}], edited=written)

                with self.subTest(deployment_configs=deployment_configs, write=write):
                    result = self.run_module(FakeModule(params()), client)

                    getattr(api, write).assert_called_once()
                    self.assertEqual(result["msg"], "Cloudflare API returned malformed Pages project data")
                    self.assertTrue(result["changed"])
                    self.assertEqual(result["pages_project"], written)
                    self.assertEqual(result["name"], "docs")

    def test_malformed_deployment_configs_do_not_block_deletion(self):
        for deployment_configs in ("production", ["production"]):
            client, api = client_with([{**PROJECT, "deployment_configs": deployment_configs}])
            with self.subTest(deployment_configs=deployment_configs):
                result = self.run_module(FakeModule(params(state="absent")), client)

                api.delete.assert_called_once()
                self.assertEqual(result["message"], "Pages project deleted")


class MalformedListTests(TestCase):
    def test_falsy_project_page_result_fails_the_domain_owner_check(self):
        for result in FALSY_PAGE_RESULTS:
            requests = []
            with self.subTest(result=result), sdk_client(list_response(result, requests)) as client:
                with self.assertRaises(ModuleFail) as raised:
                    pages_projects.check_domain_owners(FakeModule(params()), client, set(), ["new.example.com"])

                self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed Pages project data")
                self.assertEqual(raised.exception.values["account_id"], "account")
                self.assertEqual([request.method for request in requests], ["GET"])
