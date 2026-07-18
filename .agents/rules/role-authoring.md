# Role authoring

Conventions for the roles in `roles/` that `ansible-lint` and `yamllint` don't enforce on their
own. As with modules, match the nearest existing role.

Roles come in two kinds:

- **Manager** roles call Cloudflare modules to create and update resources.
- **Info** roles gather facts and publish them.

Both share the same layout:

- `defaults/`
- `meta/`
- `molecule/default/` scenario
- `README.md`
- `tasks/`

## Layout and variables

- Prefix a role's input variables with the role name.
- Default variables by type:
  - string: `null`
  - list: `[]`
  - dict: `{}`
- Keep these in sync when you change variables, defaults, dependencies, or published facts:
  - `README.md`
  - `defaults/main.yml`
  - `meta/main.yml`
- Tag every task with the role name.

## Manager roles

Most manager roles are list-driven: the caller passes a `{{ role }}_list`, and `tasks/main.yml`
loops over it. (A few manage a single fixed resource with plain scalar variables instead.) The
exact shape varies, so match the nearest role, but the list-driven pattern works like this.

### Dispatch

- Send each item through `include_tasks`, with `apply.tags` set to the role-name tag so tagged
  runs still reach the child tasks.
- The included file holds the module call, either:
  - a single `include.yml`, or
  - files split by operation (`present.yml`, `absent.yml`, `info.yml`).

### Default state

- Default each item's `state` to `present` when unset, via one of:
  - `| d('present')`
  - a `product`/`combine` merge into an internal `__{{ role }}_list`
  - a `when` guard

### Loop

- Loop with a per-item `loop_var` named `_{{ singular }}` and a `label`.
- Batched roles loop over `{{ role }}_list | batch(...)` with a `__{{ role }}_list` loop var instead.
- Guard the loop with a `when` on the item's identifier.

### Module call

- Default optional values with `| d(omit)`.
- Pin `purge_*` booleans with `| d(true)` or `| d(false)` — never `| d(omit)`.
- Set `validate_certs: true`.
- Register `__{{ role }}_result` if a later task needs it.

### Single-resource roles

- Skip the list; call the module once in `main.yml`.
- Use scalar variables:
  - `{{ role }}_name`
  - `{{ role }}_state`
- Set `validate_certs: true`.

## Info roles

- An info role's public output is its `_` prefixed facts.
- Call the matching info module and register the result as `__{{ role }}_query`.
- Use `set_fact` to publish snake_case facts, defaulting the source with `| d([])` or `| d({})`:
  - `_{{ role }}_info_list`
  - `_{{ role }}_info_dict` (when the data has a stable key)

## Naming

| Prefix            | For              | Examples                                                         |
| ----------------- | ---------------- | ---------------------------------------------------------------- |
| `_{{ role }}_`    | Published facts  | `_{{ role }}_info_list`, `_{{ role }}_info_dict`                 |
| `_{{ singular }}` | `loop_var`       | `_topic` (batched loops reuse `__{{ role }}_list`)               |
| `__{{ role }}_`   | Internal scratch | `__{{ role }}_list`, `__{{ role }}_result`, `__{{ role }}_query` |
