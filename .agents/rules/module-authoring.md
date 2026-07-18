# Module authoring

Conventions for the resource and info modules in `plugins/modules/` (built on
`AnsibleModule`; lookup plugins are out of scope). This is house style, not a strict spec:

- When in doubt, match the nearest existing module.
- Prefer the shared `module_utils` helpers (see `helpers.md`) over writing your own logic.

## Structure

Modules usually come as a manager/info pair — `{{ module }}.py` and `{{ module }}_info.py` — though not
every resource has both. Lay each file out in this order:

- `DOCUMENTATION`, `EXAMPLES`, and `RETURN` docstrings.
- Imports.
- Helpers, by module type:
  - Manager → `ensure_present`, `ensure_absent`.
  - Info → `list`, `info`.
- `main()` — builds the `AnsibleModule`, dispatches on `state`, and calls the helpers.

When starting a new module, copy the structure of an existing pair.

### Spacing

- Separate a function into steps with single blank lines: read inputs, build
  the request, call Cloudflare, shape the result, exit.
- Put a blank line between a computation and the branch or loop that consumes
  it, and after a multi-line block before whatever follows it.
- One blank line at most inside a function; don't pad short helpers.

## Behavior

### State

- Keep the `present` and `absent` flows explicit and easy to follow.
- Stay idempotent: read the current state first, and skip API calls that aren't needed.

### Check mode

- Set `supports_check_mode=True`.
- Guard every mutating API call so that none run while `module.check_mode` is set.
- Still predict the change: compute and return the same `changed` value and result shape you
  would produce outside check mode.
- Info modules always report `changed=False`.

### Waiters

- For long-running operations, expose the same wait controls as nearby modules.
- Use the waiter helpers instead of writing your own polling loop.

## Arguments

### Types

- Accept parameters and return data in snake_case.

### Validation

- Prefer the argument-spec validators over hand-written checks — for every module:
  - `mutually_exclusive`
  - `required_by`
  - `required_if`
  - `required_one_of`
  - `required_together`
- For "one of several forms" cases — such as `id`, or `name` plus `parent_id` — use several
  `required_one_of` entries that each pair with the standalone identifier.
- Put constraints on a nested dict option inside that option's own `argument_spec`.

### Secrets

- Mark secrets with `no_log=True`, and keep their values out of examples, return data, and error
  messages.

### Info lookups

- If the singular lookup and the list/filter options drive different API calls, make the two
  modes mutually exclusive.
