# AGENTS.md

## Model

gpt-5.5 high

## Standards

### Module behavior

* Keep present and absent flows explicit and easy to follow

* Ensure modules remain idempotent and avoid unnecessary cloudflare api calls

* Support check mode
  * Do not make mutating cloudflare api calls in check mode
  * Info modules
    * Set `supports_check_mode=True`
    * Return `changed=False`
  * Return the predicted result shape when practical

* Long-running operations
  * Keep modules synchronous unless an existing module intentionally does
    otherwise
  * Let roles handle async execution, polling, delay, retry, and batching

### Arguments

* Accept module parameters in snake_case and transform to cloudflare sdk request
  formats using existing helpers

* Prefer base `AnsibleModule` validation arguments such as `required_if`,
  `required_one_of`, `required_together`, and `mutually_exclusive` over manual
  parameter validation when they express the rule clearly

* Secret module parameters
  * Mark parameters with `no_log=True`
  * Do not include secret values in examples, return values, or error messages

### Documentation

* Keep `DOCUMENTATION`, `EXAMPLES`, `RETURN`, and `argument_spec` aligned when
  adding or changing module parameters, return fields, aliases, choices, or
  defaults

* For cloudflare modules, include the relevant `cloudflare` python sdk
  requirements

* For list options and list return values, include `elements` in
  `DOCUMENTATION` and `RETURN`

* Use the collection fqcn in `EXAMPLES`, such as
  `linuxhq.cloudflare.<plugin_name>`

* When an option is conditionally required through `required_if`, document
  the condition in the description instead of marking the option `required: true`

### Operations

* Create cloudflare clients with the existing `cloudflare_client(module)` helper
  unless an existing pattern in the module requires a different helper

* Use the official `cloudflare` python sdk for cloudflare api calls

* When using cloudflare apis that may be missing from older `cloudflare` sdk
  versions, fail with a clear module error

* Scrub unset optional parameters before passing request dictionaries to
  cloudflare operations

* Use existing collection helpers for common request, response, lookup,
  serialization, and comparison behavior instead of hand-rolled logic

* Wrap cloudflare api failures through the existing `cloudflare_client` and
  `fail_from_cloudflare_error` helpers, including the resource name or
  identifier in the message when one is available

### Result data

* Return ansible-facing data in snake_case when the module owns the result
  shape; preserve cloudflare api field names for raw cloudflare resources unless
  the existing module normalizes them

* Normalize cloudflare sdk responses with `serialize_resource` before including
  them in `exit_json`

### Implementation style

* Keep changes focused on measurable behavior, consistency, or documentation
  correctness; avoid broad style churn

* Keep implementations consistent with existing cloudflare module patterns
  * Use direct `module.params[...]` access for simple or one-off values
  * Introduce local variables only when the value is reused, normalized,
    or clarifies request construction
  * Do not pass `module` and `module.params[...]` to the same function call;
    when the value is only forwarded from `module.params`, read it inside the
    callee
  * Do not add optional fallback parameters such as `name=None` for values that
    are owned by `module.params`; make the callee read `module.params[...]`
    directly
  * If a helper must also handle non-parameter values returned by cloudflare,
    keep that value as a required explicit argument or use a separate helper
    instead of mixing explicit arguments with `module.params` fallbacks
  * Never mutate `module.params` after module initialization

* Prefer explicit loops over nested comprehensions when the loop performs
  cloudflare api calls or filters missing cloudflare resources

* Do not extract shared module_utils helpers unless several modules genuinely
  need the same stable behavior and the abstraction clearly reduces complexity
  * Keep cloudflare module_utils helpers generic across modules
  * Keep resource-specific lookup and endpoint helpers in the module that owns
    the resource
  * Inline single-use wrappers, iterator adapters, and guard helpers into their
    only caller
  * Prefer composing small shared primitives such as `select_fields` and
    `values_differ` over adding thin convenience wrappers

### Lookup plugins

* Validate unsupported positional terms and required keyword arguments
  explicitly, and raise `AnsibleLookupError` with actionable messages

## Helper reference

* Prefer existing ansible helpers before implementing custom logic

* Use existing ansible helpers, including
  * ansible.module_utils.basic.get_all_subclasses
  * ansible.module_utils.basic.get_module_path
  * ansible.module_utils.basic.get_platform
  * ansible.module_utils.basic.heuristic_log_sanitize
  * ansible.module_utils.basic.load_platform_subclass
  * ansible.module_utils.basic.missing_required_lib
  * ansible.module_utils.common.collections.count
  * ansible.module_utils.common.collections.is_iterable
  * ansible.module_utils.common.collections.is_sequence
  * ansible.module_utils.common.collections.is_string
  * ansible.module_utils.common.dict_transformations.camel_dict_to_snake_dict
  * ansible.module_utils.common.dict_transformations.dict_merge
  * ansible.module_utils.common.dict_transformations.recursive_diff
  * ansible.module_utils.common.dict_transformations.snake_dict_to_camel_dict
  * ansible.module_utils.common.json.get_decoder
  * ansible.module_utils.common.json.get_encoder
  * ansible.module_utils.common.json.get_module_decoder
  * ansible.module_utils.common.json.get_module_encoder
  * ansible.module_utils.common.parameters.env_fallback
  * ansible.module_utils.common.parameters.remove_values
  * ansible.module_utils.common.parameters.sanitize_keys
  * ansible.module_utils.common.parameters.set_fallbacks
  * ansible.module_utils.common.text.converters.container_to_bytes
  * ansible.module_utils.common.text.converters.container_to_text
  * ansible.module_utils.common.text.converters.jsonify
  * ansible.module_utils.common.text.converters.to_bytes
  * ansible.module_utils.common.text.converters.to_text
  * ansible.module_utils.common.text.formatters.bytes_to_human
  * ansible.module_utils.common.text.formatters.human_to_bytes
  * ansible.module_utils.common.text.formatters.lenient_lowercase
  * ansible.module_utils.common.validation.check_missing_parameters
  * ansible.module_utils.common.validation.check_mutually_exclusive
  * ansible.module_utils.common.validation.check_required_arguments
  * ansible.module_utils.common.validation.check_required_by
  * ansible.module_utils.common.validation.check_required_if
  * ansible.module_utils.common.validation.check_required_one_of
  * ansible.module_utils.common.validation.check_required_together
  * ansible.module_utils.common.validation.check_type_bits
  * ansible.module_utils.common.validation.check_type_bool
  * ansible.module_utils.common.validation.check_type_bytes
  * ansible.module_utils.common.validation.check_type_dict
  * ansible.module_utils.common.validation.check_type_float
  * ansible.module_utils.common.validation.check_type_int
  * ansible.module_utils.common.validation.check_type_jsonarg
  * ansible.module_utils.common.validation.check_type_list
  * ansible.module_utils.common.validation.check_type_path
  * ansible.module_utils.common.validation.check_type_raw
  * ansible.module_utils.common.validation.check_type_str
  * ansible.module_utils.common.validation.count_terms

## Validation

* After plugin changes, run
  * ansible-test
    * Use the collection path `venv/ansible_collections/linuxhq/cloudflare`
    * Use a real git worktree or real directory for that collection path;
      symlinks are not sufficient because `ansible-test` resolves the physical
      path
    * If the worktree does not exist, create it
      * `mkdir -p venv/ansible_collections/linuxhq`
      * `git worktree add --detach venv/ansible_collections/linuxhq/cloudflare HEAD`
    * To test uncommitted changes from the root checkout, overlay the current
      tree into the worktree
      * `rsync -a --delete --exclude='.git' --exclude='venv' ./ venv/ansible_collections/linuxhq/cloudflare/`
    * If the default python discovery fails because local shims are unavailable,
      run sanity from the worktree with the python version from the active venv
      * `../../../bin/ansible-test sanity --color no --python 3.12`
  * black
    * `venv/bin/black --check plugins`
  * git
    * `git diff --check`
  * python
    * `venv/bin/python -m compileall -q plugins`

## Workflow

* Complete the requested implementation before stopping

* Do not commit changes
