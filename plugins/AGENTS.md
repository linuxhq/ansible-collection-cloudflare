# AGENTS.md

## Model

gpt-5.5 high

## Workflow

* Read this entire file before making changes
* Apply every section relevant to the requested change
* Use existing collection patterns and helpers before introducing new implementations
* Complete the requested implementation before stopping
* Run the required validation steps after plugin changes
* Do not commit changes to git

## Standards

### Module behavior

* Keep present and absent flows explicit and easy to follow

* Ensure modules remain idempotent and avoid unnecessary cloudflare api calls

* Support check mode: never make mutating cloudflare api calls in check mode; set
  `supports_check_mode=True` and return `changed=False` in info modules;
  return the predicted result shape when practical

* Long-running operations: keep modules synchronous unless an existing module
  intentionally does otherwise; let roles handle async execution, polling,
  delay, retry, and batching

### Arguments

* Accept module parameters in snake_case and transform to cloudflare sdk request
  formats using existing helpers

* Use base `AnsibleModule` validation arguments such as `required_by`,
  `required_if`, `required_one_of`, `required_together`, and `mutually_exclusive`
  over manual parameter validation when they express the rule clearly

* Mark secret parameters with `no_log=True` and exclude their values from
  examples, return values, and error messages

* When writing info modules, expose singular lookup parameters (`name`, `id`,
  `zone_id`) only when the underlying api accepts a singular identifier. Do not
  substitute plural list parameters (`names`, `ids`) for the api's
  native parameter shape

### Documentation

* Keep `DOCUMENTATION`, `EXAMPLES`, `RETURN`, and `argument_spec` aligned when
  adding or changing module parameters, return fields, aliases, choices, or
  defaults

* Include the relevant `cloudflare` python sdk requirements

* For list options and list return values, include `elements` in
  `DOCUMENTATION` and `RETURN`

* Use the collection fqcn in `EXAMPLES`, such as `linuxhq.cloudflare.<plugin_name>`

* When an option is conditionally required through `required_if`, document
  the condition in the description instead of marking the option `required: true`

### Operations

* Create cloudflare clients with the existing `cloudflare_client(module)` helper
  unless an existing pattern in the module requires a different helper

* Use the official `cloudflare` python sdk for cloudflare api calls

* When cloudflare apis or request parameters may be missing from older
  `cloudflare` sdk versions, validate sdk support in `main()` before dispatching
  to state handlers; fail with `module.fail_json()` naming the unsupported
  api or parameter

* Scrub unset optional parameters before passing request dictionaries to
  cloudflare operations

* Use existing collection helpers for common request, response, lookup,
  serialization, and comparison behavior instead of hand-rolled logic

* Wrap cloudflare api failures through the existing `cloudflare_client` and
  `fail_from_cloudflare_error` helpers, including the resource name or
  identifier in the message when one is available

### Result data

* Return ansible-facing data in snake_case; preserve cloudflare api field names
  for raw cloudflare resources unless the existing module normalizes them

* Normalize cloudflare sdk responses with `serialize_resource` before including
  them in `exit_json`

### Implementation style

* Cache a `module.params[...]` value in a local variable only when it is
  accessed two or more times, requires normalization, or its name meaningfully
  clarifies request construction; use `module.params[...]` directly otherwise

* Pass only `module` to helpers that need `module.params` values; read them
  inside the helper rather than extracting and passing them at the call site,
  and do not add `name=None`-style fallback parameters for values owned by
  `module.params`

* If a helper also needs returned values, pass those as required explicit
  arguments rather than mixing explicit and `module.params` fallback parameters

* Never mutate `module.params` after module initialization

* Dispatch on `state` with an explicit `if`/`elif`/`else` chain; always close
  with `module.fail_json(msg=f"Unsupported state: {state}")` in the final
  branch, even when `choices` validation makes it unreachable

* Use explicit loops over nested comprehensions when the loop performs
  cloudflare api calls or filters missing cloudflare resources

* Inline a helper into its one call site when it is called from exactly one
  place and is not passed as a callback reference; if the helper catches a
  specific exception and returns `None` with the caller checking for `None`,
  replace that pattern with `continue` when inlining

* Separate logical phases with a single blank line at every level of nesting.
  Apply a blank line before each of the following transitions, unless the
  statement is the very first line in its enclosing block:
  * Before every `try:` statement
  * After the last `except` clause before the next statement at the same level
  * After a guard `continue` or `break` before the next statement in the loop
  * Between any result assignment and subsequent processing of that result

* Do not extract shared module_utils helpers unless several modules genuinely
  need the same stable behavior and the abstraction clearly reduces complexity;
  keep module_utils helpers generic across modules, resource-specific helpers in
  the module that owns the resource, and inline single-use wrappers into their
  only caller

### Lookup plugins

* Validate unsupported positional terms and required keyword arguments
  explicitly, and raise `AnsibleLookupError` with actionable messages

## Helper reference

Use existing helpers before implementing custom logic.

* `ansible.module_utils`:
  * **basic**:
    * get_all_subclasses
    * get_module_path
    * get_platform
    * heuristic_log_sanitize
    * load_platform_subclass
    * missing_required_lib
  * **common.collections**:
    * count
    * is_iterable
    * is_sequence
    * is_string
  * **common.dict_transformations**:
    * camel_dict_to_snake_dict
    * dict_merge
    * recursive_diff
    * snake_dict_to_camel_dict
  * **common.json**:
    * get_decoder
    * get_encoder
    * get_module_decoder
    * get_module_encoder
  * **common.parameters**:
    * env_fallback
    * remove_values
    * sanitize_keys
    * set_fallbacks
  * **common.text.converters**:
    * container_to_bytes
    * container_to_text
    * jsonify
    * to_bytes
    * to_text
  * **common.text.formatters**:
    * bytes_to_human
    * human_to_bytes
    * lenient_lowercase
  * **common.validation**:
    * check_missing_parameters
    * check_mutually_exclusive
    * check_required_arguments
    * check_required_by
    * check_required_if
    * check_required_one_of
    * check_required_together
    * check_type_bits
    * check_type_bool
    * check_type_bytes
    * check_type_dict
    * check_type_float
    * check_type_int
    * check_type_jsonarg
    * check_type_list
    * check_type_path
    * check_type_raw
    * check_type_str
    * count_terms

## Validation

After plugin changes, run:

* **ansible-test**
  * Use the collection path `venv/ansible_collections/linuxhq/cloudflare`
  * Use a real git worktree or real directory; symlinks are not sufficient
    because `ansible-test` resolves the physical path
  * If the worktree does not exist, create it:
    ```
    mkdir -p venv/ansible_collections/linuxhq
    git worktree add --detach venv/ansible_collections/linuxhq/cloudflare HEAD
    ```
  * Overlay uncommitted changes from the root checkout before running:
    ```
    rsync -a --delete --exclude='.git' --exclude='venv' ./ venv/ansible_collections/linuxhq/cloudflare/
    ```
  * Run from the worktree, using the Python version from the active venv if
    local shim discovery fails:
    ```
    ../../../bin/ansible-test sanity --color no --python 3.12
    ```
* **black**: `venv/bin/black --check plugins`
* **git**: `git diff --check`
* **python**: `venv/bin/python -m compileall -q plugins`
