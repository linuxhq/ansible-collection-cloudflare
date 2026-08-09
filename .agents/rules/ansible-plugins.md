# Ansible Plugins

Standards for Python modules, lookup plugins, and filter plugins under
`plugins/`. SDK-specific requirements are defined separately.

## Python

### YAGNI

- Implement only behavior required by the current plugin contract.
- Add an option, abstraction, or extension point only for a concrete use.
- Generalize only when a second concrete use requires the same behavior.
- Remove obsolete code rather than retaining dormant branches or comments.
- Optimize only after measurement identifies a relevant bottleneck.
- Preserve required validation, security, compatibility, and error handling.

### KISS

- Choose the smallest implementation that is clear and correct.
- Reuse the nearest established pattern before introducing a new one.
- Prefer the standard library, Ansible features, and collection helpers.
- Keep one evident control flow for each operation.
- Minimize mutable state, nesting, indirection, and exceptional cases.
- Use explicit names and transformations instead of implicit machinery.
- Add a dependency only when existing capabilities cannot meet the need.

### SOLID

- Single responsibility: give each plugin and helper one reason to change.
- Open/closed: extend stable behavior without rewriting unrelated paths.
- Liskov substitution: preserve input, result, check-mode, and failure
  contracts across interchangeable implementations.
- Interface segregation: pass only the data and dependencies a helper uses.
- Dependency inversion: isolate transport and provider details behind focused
  helpers with stable local contracts.
- Apply SOLID to demonstrated complexity; it does not justify speculative
  abstraction.

### Standards

- Support the Python versions for the plugin's execution context.
- Modules and `module_utils` support managed-node Python versions.
- Lookup and filter plugins support control-node Python versions.
- Treat Black and Ruff as the formatting and linting authorities.
- Use descriptive snake_case names and direct control flow.
- Keep each function focused on a meaningful unit of work.
- Use explicit imports; never use wildcard imports.
- Avoid side effects during import.
- Follow the collection's established pattern for optional imports.
- Catch the narrowest expected exception and preserve diagnostic context.
- Place executable entry points behind `if __name__ == "__main__":`.

## Ansible

### Modules

#### Scope and interface

- Give each module one concise, well-defined task.
- Use state modules for declarative resource management.
- Isolate imperative operations in purpose-specific action modules.
- Document when an action module is inherently non-idempotent.
- Use `name` for the primary resource identifier when practical.
- Use Ansible types, such as `type="bool"`, instead of parsing values.
- Do not add `get`, `list`, or `info` states to manager modules.
- Do not execute other modules; use a role to orchestrate multiple modules.
- Keep each module self-contained and place shared code in `module_utils`.
- Name module files with underscores, never hyphens or spaces.

#### Format and structure

- Begin Python modules with `#!/usr/bin/python` so Ansible can select the
  managed-node interpreter.
- Do not use `#!/usr/bin/env`, pass arguments in the shebang, or add a source
  encoding declaration.
- Follow the shebang with the approved copyright statement and the
  one-line GPLv3-or-later license declaration.
- Do not add copyright years or alter an existing copyright holder without
  permission.
- Order files as the shebang, copyright, license, documentation blocks,
  imports, constants, helpers, `main()`, and the executable guard.
- Keep `DOCUMENTATION`, `EXAMPLES`, and `RETURN` before imports.
- Match the nearest existing module before introducing a new pattern.
- Create manager/info pairs only when both operations provide value.
- Use `ensure_present` and `ensure_absent` for state transitions.
- Name query and action helpers for the operation they perform.
- In paired modules, keep `main()` focused on setup, validation, and dispatch.
- In single-operation modules, keep linear work in `main()` when extraction
  would not improve clarity.
- Move reusable or independently meaningful work into focused helpers.

#### Arguments and validation

- Accept parameters and return fields in snake_case.
- Define types, defaults, choices, aliases, and list `elements` in
  `argument_spec`.
- Define nested schemas under the option's `options` entry.
- Keep nested relationship constraints beside the nested schema.
- Use `mutually_exclusive`, `required_by`, `required_if`,
  `required_one_of`, and `required_together` for static relationships.
- Use explicit validation for semantic, range, state-dependent, or
  provider-dependent constraints.
- Validate inputs before external operations whenever possible.
- Model each valid alternate identifier with relationship validators.
- Mark secrets with `no_log=True`.
- Never expose secrets in results, failures, examples, or logs.

#### State and check mode

- Keep `present` and `absent` flows explicit in state modules.
- Read current state before mutation and change only the identified delta.
- Re-read externally managed state after mutation when the provider can
  assign defaults or normalize values.
- Set `supports_check_mode=True` for every module.
- Guard every mutating operation in check mode.
- Return the predicted `changed` value and safely derivable result data.
- Avoid mutation-only dependencies in check mode when prediction is reliable.
- Report `changed=True` for an action that would execute in check mode.

#### Requests, results, and failures

- Convert provider request and response shapes with collection helpers when
  available.
- Omit unset values from provider requests.
- Validate external response structure before relying on required fields.
- Return a top-level dictionary containing JSON-serializable UTF-8 data.
- Keep result keys and value types stable across execution paths.
- Return useful state when `changed=False`.
- Return through `module.exit_json` and fail through the module's failure
  helper.
- Never print module output, write to stderr, or call `sys.exit`.
- Catch expected failures at the boundary that can explain them.
- Include the operation and resource identifier in external failure messages.
- Document dependencies and report missing libraries through the module or a
  shared collection helper.
- Use atomic replacement rather than overwriting files in place.
- Do not add module-local caches.

#### Info and facts modules

- Use a singular `_info` name for general information.
- Use a singular `_facts` name only for host-specific `ansible_facts`.
- Do not model information retrieval as a manager-module state.
- Return info data in the standard result dictionary.
- Return host facts under `ansible_facts`.
- Support check mode and never mutate state.
- Always return `changed=False`.
- Offer a singular lookup only when the upstream interface supports one.
- Keep singular lookup options mutually exclusive with list filters when they
  invoke different operations.

### Lookup plugins

- Implement `LookupModule` as a `LookupBase` subclass.
- Keep `run(terms, variables=None, **kwargs)` focused and return a list.
- Define options in `DOCUMENTATION`.
- Use `set_options` and `get_option` when Ansible configuration applies.
- Validate terms and options before performing work.
- Raise `AnsibleLookupError` with actionable context for expected failures.
- Never include secret values in failures or display output.

### Filter plugins

- Keep filter functions pure and deterministic.
- Do not mutate caller input.
- Return native values suitable for Jinja expressions.
- Raise `AnsibleFilterError` for expected input and dependency failures.
- Catch only exceptions the filter can explain or recover from.
- Expose filters through `FilterModule.filters()` with stable public names.

### Documentation

- Keep `DOCUMENTATION`, `EXAMPLES`, and `RETURN` synchronized with
  behavior.
- Keep `DOCUMENTATION` valid YAML.
- Match the documented module name to the Python filename.
- Keep module `argument_spec` synchronized with its documentation.
- Use lower-case documentation field names.
- Write descriptions as complete sentences with initial capitals and periods.
- Do not end `short_description` with a period.
- Quote `version_added` and use the introducing release series.
- Set its patch component to zero; Ansible accepts only major or minor releases.
- Include minimum versions in `requirements` when a dependency has one.
- Omit `required` unless its value is `true`.
- Document Boolean values as `true` and `false`.
- Document check-mode and diff support under `attributes`, not `notes`.
- Use the fully qualified collection name in examples.
- Declare `elements` for list options and list returns.
- Use `contains` to document nested return fields.
- Document each return with `description`, `returned`, and `type`.
- Document conditional requirements on every affected option.
- Describe conditional requirements instead of marking an option required.
- End each mutually exclusive option with the exclusion statement.
- For singular info lookups, document list filters as mutually exclusive.
- Mark options used only by a singular lookup with `Requires O(name)`.
- Reference nested options with paths such as `O(parent[].child)`.
- Provide copy-ready examples for representative supported inputs.
- Give each example a capitalized task name without a trailing period.
- Use variables or `EXAMPLE`-prefixed placeholders for secret values.
- Use a documentation fragment only when the full shared interface matches.

### Verification

- Run Black and Ruff for Python changes.
- Run `ansible-test sanity` for modules and plugins.
- Validate module documentation before committing it.
- Exercise each new module through Ansible with representative arguments.
- Add integration coverage for every new module or plugin.
- Add focused regression coverage for behavior changes.
- Extend the existing unit suite when the affected plugin has one.
