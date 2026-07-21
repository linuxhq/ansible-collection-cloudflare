================================
linuxhq.cloudflare Release Notes
================================

.. contents:: Topics

v2.1.5
======

Release Summary
---------------

Maintenance release. The resource and info modules were refactored to the
documented house layout: resource modules now dispatch state through
``ensure_present`` and ``ensure_absent`` helpers, and info modules through
``list``/``info`` helpers. This is an internal restructure only; no options,
return values, or behavior changed.

v2.1.4
======

Release Summary
---------------

Dependency release. The collection now requires the cloudflare Python SDK 5.x (``cloudflare >= 5.5.0, < 6``); support for the 4.x SDK has been dropped. Review the breaking change before upgrading.

Breaking Changes / Porting Guide
--------------------------------

- all modules - the collection now requires ``cloudflare >= 5.5.0, < 6``; support for the 4.x SDK has been dropped (https://github.com/linuxhq/ansible-collection-cloudflare/pull/32).

v2.1.3
======

Release Summary
---------------

Pagination release. ``zones_info`` follows API pagination and returns all zones; the ``page`` and ``per_page`` options were removed. Review the breaking change before upgrading.

Breaking Changes / Porting Guide
--------------------------------

- zones_info - removed the ``page`` and ``per_page`` options; the module now follows API pagination and returns all zones.

v2.1.2
======

Release Summary
---------------

Maintenance release. Listing and name lookups follow API pagination everywhere, and the collection now requires ansible-core 2.18 and community.general 12.

Breaking Changes / Porting Guide
--------------------------------

- Raised the minimum supported ansible-core version to 2.18.0 and the community.general dependency to ``>=12.0.0,<14.0.0``.

Bugfixes
--------

- access_groups - paginate the name lookup so groups beyond the first page of name-filter matches are found instead of recreated.
- access_service_tokens - paginate the name lookup so tokens beyond the first page of name-filter matches are found instead of recreated.
- pages_projects_info - paginate the Pages projects listing so accounts with more projects than one API page return complete results.

v2.1.1
======

Release Summary
---------------

Bugfix release that restores support for all Cloudflare Access application types.

Bugfixes
--------

- access_apps - the ``type`` option is no longer restricted to a subset of application types; ``warp`` and other valid Cloudflare Access application types are accepted again.

v2.1.0
======

Release Summary
---------------

Hardening release. Modules follow API pagination, converge more reliably, and handle Cloudflare errors and long-running operations predictably. Review the breaking changes before upgrading.

Minor Changes
-------------

- all - resource lookups use server-side filters and follow API pagination where supported.
- cfd_tunnel, pages_projects, warp_connector - added ``rotate_secrets`` to apply write-only secrets to existing resources.
- galaxy.yml - constrained ``community.general`` to ``<11.0.0`` for ansible-core 2.15 compatibility.
- rules_lists - added ``operation_timeout`` to bound bulk item operations.

Breaking Changes / Porting Guide
--------------------------------

- access_apps - the ``type`` option is restricted to ``self_hosted``, ``ssh``, and ``vnc``.
- access_policies - removed the ``precedence`` option; the account-level Access policy API does not accept it.
- zones - removed the ``internal`` zone type.

Security Fixes
--------------

- access_apps, access_apps_info, access_identity_providers_info - secret fields in SCIM and identity provider responses are redacted.
- examples, cfd_tunnel - removed a hardcoded tunnel secret; provide ``CLOUDFLARE_TUNNEL_SECRET`` via the environment instead.
- pages_projects - ``deployment_configs`` is not logged; it can contain ``secret_text`` values.

Bugfixes
--------

- all - numerous idempotency and convergence fixes, including complete pagination in lookups and info modules, write-only secret comparison, preserved omitted fields on update, and stricter bulk-operation handling.

v2.0.9
======

Release Summary
---------------

Maintenance release that refreshes the plugin development guidelines and refactors all modules to follow them. No functional changes.

Minor Changes
-------------

- all - refactored every module to follow the updated development guidelines.
- all - updated the plugin development guidelines.

v2.0.8
======

Release Summary
---------------

Adds agent workflow support and applies general module cleanup.

Minor Changes
-------------

- all - added support for agent workflows.
- all - general module cleanup.

v2.0.7
======

Release Summary
---------------

Fixes access service token lookups by no longer passing the unsupported ``per_page`` parameter.

Minor Changes
-------------

- access_service_tokens - no longer passes the unsupported ``per_page`` parameter when looking up service tokens.

v2.0.6
======

Release Summary
---------------

Replaces the ``uri``-based API wrappers with custom Ansible modules built on the official ``cloudflare`` Python SDK, and adds async support to the applicable roles. Review the breaking changes before upgrading.

Minor Changes
-------------

- all - added async support to the applicable roles.
- all - migrated every role from ``uri`` wrappers to custom Ansible modules.

Breaking Changes / Porting Guide
--------------------------------

- devices_policy - defaults have been broken out into individual role variables.
- pages_projects - DNS record management has been removed; use the ``dns`` role instead.

v2.0.5
======

Release Summary
---------------

Adds support for Cloudflare-managed tunnels, including new roles for managing and inspecting tunnel configurations.

Minor Changes
-------------

- all - removed ``box_architecture`` from the molecule configuration.
- all - removed tags from the molecule verify plays.
- cfd_tunnel - added support for Cloudflare-managed tunnels.
- cfd_tunnel_configurations - new role for managing tunnel configurations.
- cfd_tunnel_configurations_info - new role for gathering tunnel configurations.

Breaking Changes / Porting Guide
--------------------------------

- cfd_tunnel - ``config_src`` must now be defined for each tunnel in inventory.

v2.0.4
======

Release Summary
---------------

Introduces the ``access_identity_providers_info`` role.

Minor Changes
-------------

- access_identity_providers_info - new role for gathering Access identity providers.
- access_policies - added a meta dependency on ``access_identity_providers_info``.

v2.0.3
======

Release Summary
---------------

Introduces the ``dnssec`` and ``dnssec_info`` roles.

Minor Changes
-------------

- dnssec - new role for managing zone DNSSEC settings.
- dnssec_info - new role for gathering zone DNSSEC settings.

v2.0.2
======

Release Summary
---------------

Introduces eight new roles for Cloudflare WARP and Zero Trust device management.

Minor Changes
-------------

- devices_policy - new role for managing device policies.
- devices_policy_info - new role for gathering device policies.
- devices_settings - new role for managing device settings.
- devices_settings_info - new role for gathering device settings.
- warp_connector - new role for managing WARP connectors.
- warp_connector_info - new role for gathering WARP connectors.
- zerotrust_connectivity_settings - new role for managing Zero Trust connectivity settings.
- zerotrust_connectivity_settings_info - new role for gathering Zero Trust connectivity settings.

v2.0.1
======

Release Summary
---------------

Adds support for the ``destinations`` option in the ``access_apps`` role, allowing multiple domains to be associated with a single application.

Minor Changes
-------------

- access_apps - added support for the ``destinations`` option.

v2.0.0
======

Release Summary
---------------

Restructures the entire collection. Most roles have been renamed and several deprecated roles were removed, so all inventory and playbooks must be updated when upgrading from 1.x. See the provided examples.

Minor Changes
-------------

- all - added ``check_mode`` support to avoid failures.
- all - added ``state`` support to all applicable roles.
- all - added example inventory and playbooks.
- all - added molecule tests to every role.
- all - the ansible-lint configuration no longer carries any exclusions.
- purge_cache - new role for purging the Cloudflare cache.

Breaking Changes / Porting Guide
--------------------------------

- access_apps - renamed from ``access_app``.
- access_apps_info - renamed from ``access_app_info``.
- access_groups - renamed from ``access_group``.
- access_groups_info - renamed from ``access_group_info``.
- access_policies - renamed from ``access_policy``.
- access_policies_info - renamed from ``access_policy_info``.
- access_service_tokens - renamed from ``access_service_token``.
- access_service_tokens_info - renamed from ``access_service_token_info``.
- accounts_info - renamed from ``account_info``.
- cfd_tunnel - renamed from ``tunnel``.
- cfd_tunnel_info - renamed from ``tunnel_info``.
- network - removed.
- pagerules - renamed from ``page_rule``.
- pagerules_info - renamed from ``page_rule_info``.
- pages_projects - merged the ``pages_domain`` and ``pages_projects`` roles.
- pages_projects_info - renamed from ``pages_project_info``.
- rules_lists - renamed from ``rule_list``.
- rules_lists_info - renamed from ``rule_list_info``.
- rulesets - renamed from ``ruleset_entrypoint``.
- rulesets_info - renamed from ``ruleset_entrypoint_info``.
- scrape_shield - removed.
- security - removed.
- ssl - removed.
- zones - renamed from ``zone``.
- zones_info - renamed from ``zone_info``.

v1.2.0
======

Release Summary
---------------

Final 1.x release. All 1.x releases are deprecated and no longer receive updates; please upgrade to 2.0.0 or later.
