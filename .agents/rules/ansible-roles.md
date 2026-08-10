# Ansible Roles

Standards for designing, implementing, documenting, and testing content under
`roles/`. Provider-specific requirements are defined separately.

## Design

### YAGNI

- Create a role only for behavior that callers need to reuse or compose.
- Implement only the current role contract and supported lifecycle states.
- Add inputs, outputs, dependencies, and entry points only for concrete uses.
- Add task files, handlers, templates, or platform branches only when needed.
- Add role argument validation only when it improves a real input boundary.
- Batch or run work asynchronously only for measured concurrency or API needs.
- Remove obsolete tasks and variables instead of retaining dormant behavior.
- Preserve required validation, security, compatibility, and cleanup behavior.

### KISS

- Choose the smallest role structure that is clear, correct, and reusable.
- Reuse the nearest established role pattern before introducing a new one.
- Prefer one direct task over an include and one module over several commands.
- Prefer Ansible modules, filters, lookups, and facts over custom machinery.
- Keep task flow linear and keep includes shallow and purpose-specific.
- Expose one clear input model instead of aliases for the same behavior.
- Keep transformations close to the task that consumes their result.
- Add a dependency only when the role cannot meet its contract without it.

### SOLID

- Single responsibility: make a role own one resource, service, fact set, or
  reusable workflow.
- Open/closed: extend item data without rewriting unrelated task paths.
- Liskov substitution: preserve shared state, result, check-mode, and failure
  contracts across roles that implement the same pattern.
- Interface segregation: expose only inputs and outputs the role actually uses.
- Dependency inversion: orchestrate through modules and stable facts instead
  of provider CLIs, raw APIs, or another role's internal variables.
- Apply SOLID to demonstrated complexity; it does not justify abstractions.

## Role contract

### Scope and layout

- Use lowercase snake_case for role names.
- Give each role one concise, well-defined responsibility.
- Keep simple orchestration in `tasks/main.yml`.
- Split tasks only for a distinct operation, state, or reusable task sequence.
- Use the standard role layout:
  - `defaults/main.yml`
  - `meta/main.yml`
  - `molecule/default/`
  - `README.md`
  - `tasks/main.yml`
- Add `handlers/`, `templates/`, `files/`, or `vars/` only when used.
- Keep public inputs, outputs, metadata, documentation, and tests synchronized.

### Variables

- Prefix every public input with the role name.
- Define public, caller-overridable inputs in `defaults/main.yml`.
- Reserve `vars/` for internal or platform data that callers must not override.
- Choose defaults by behavior, not type alone.
- Use `[]` when an empty collection means no work.
- Use `{}` when an empty mapping is valid role input.
- Use `null` only when unset or disabled is a documented behavior.
- Use native YAML Boolean and numeric values instead of string equivalents.
- Do not read an unprefixed global variable as an implicit role input.
- Keep nested list and dictionary shapes consistent across all callers.
- Pass required module inputs directly.
- Pass optional module inputs with `| d(omit)` when omission is meaningful.
- Preserve valid false, zero, empty-list, and empty-dictionary values.
- Pin destructive, purge, and replacement behavior to documented defaults.
- Guard an unset input only when the documented contract defines a no-op.
- Fail clearly for invalid required input instead of silently skipping it.
- Use `meta/argument_specs.yml` when early role-level validation adds value.
- Keep argument specifications synchronized with defaults and documentation.

### Naming and visibility

| Name               | Purpose                        | Example                  |
| ------------------ | ------------------------------ | ------------------------ |
| `{{ role }}_`      | Public inputs                  | `role_name_list`         |
| `_{{ role }}_`     | Published facts                | `_role_name_info_list`   |
| `__{{ role }}_`    | Internal data                  | `__role_name_result`     |
| `_{{ resource }}`  | Managed resource loop variable | `_{{ resource }}`        |

- Do not expose internal `__{{ role }}_` variables as part of the contract.
- Register results only when a later task, handler, or verifier consumes them.
- Use descriptive suffixes such as `_query`, `_result`, `_status`, and `_dict`.
- Name each loop variable after the resource it manages.
- Keep loop labels useful and free of credentials or other sensitive values.

## Ansible tasks

### Task structure

- Give every task a concise, outcome-oriented name.
- Use the fully qualified collection name for every module and action plugin.
- Tag every task and handler with the role name.
- Use `apply.tags` when an included task file must inherit the role tag.
- Declare the intended module state instead of relying on a module default.
- Keep conditions explicit and based on documented inputs or Ansible facts.
- Use `ansible_facts` values for platform decisions.
- Apply `become` only to tasks that require privilege escalation.
- Keep delegation, environment changes, and check-mode overrides local.
- Add comments only when the reason cannot be expressed by the task name.

### Idempotency and check mode

- Use declarative modules and converge only the identified difference.
- Preserve a module's native `changed` result whenever possible.
- Add `changed_when` only to correct a known module or wrapper contract.
- Add `failed_when` only to define a documented success or failure contract.
- Do not use `ignore_errors` as ordinary control flow.
- Support check mode throughout the role when the called modules support it.
- Guard unavoidable side effects and non-check-mode operations explicitly.
- Do not disable check mode merely to make a scenario pass.
- Ensure a second converge reports no changes.

### Commands and failures

- Prefer a purpose-built module over `command` or `shell`.
- Use `ansible.builtin.command` when no suitable module exists.
- Use `shell` only when shell syntax is required.
- Define accurate change behavior for command-based tasks.
- Validate command results when a zero exit code is not the full contract.
- Quote or pass untrusted values as arguments; never build executable shell
  text from untrusted role input.
- Fail at the boundary that can identify the operation and affected resource.
- Keep retry loops bounded and limited to transient or eventual consistency.

## Manager roles

### Input model

- Use a list-driven role when callers manage multiple instances of a resource.
- Name the public collection `{{ role }}_list`.
- Use scalar variables when the role manages one fixed resource or service.
- Model parent-child resources with a documented nested list when that shape
  prevents repeated parent data.
- Default an omitted item state to `present` when that is the role contract.
- Keep `present` and `absent` behavior explicit and test both paths.

### Dispatch and loops

- Loop directly on the module when each item requires one task.
- Use `include_tasks` when one item requires multiple dynamic tasks.
- Use `import_tasks` for static decomposition that does not need a loop.
- Split `present.yml` and `absent.yml` only when their sequences differ.
- Use `ansible.builtin.subelements` for genuine parent-child collections.
- Use a singular loop variable and a stable, non-sensitive label.
- Guard a list item only when omission is valid and documented.

### Batching and asynchronous work

- Batch only to control real asynchronous work or an external service limit.
- Keep synchronous loops unbatched.
- Make batch size, timeout, poll interval, delay, and retries configurable only
  when callers have a concrete reason to tune them.
- Set asynchronous execution to zero in check mode.
- Poll submitted jobs with `ansible.builtin.async_status` and a bounded retry.
- Let completed job results report the operation's final change and failure.
- Keep secret protection on both submission and status tasks.

## Info roles

- Call the matching information module when one exists.
- Register its result as `__{{ role }}_query`.
- Publish stable, snake_case facts with the `_{{ role }}_` prefix.
- Publish `_{{ role }}_list` when the provider returns a collection.
- Publish `_{{ role }}_dict` only when items have a stable, unique key.
- Publish named scalar facts when list or dictionary output is not meaningful.
- Default missing provider collections to `[]` and mappings to `{}`.
- Never publish credentials, secret values, or unfiltered sensitive results.
- Document every published fact under `Return Values`.
- Set `allow_duplicates: true` when the info role must run repeatedly as a
  dependency or with distinct parameters.

## Action and workflow roles

- Use an action role only for a reusable imperative operation or task sequence.
- Keep one clear outcome, such as opening a session or purging a cache.
- State when the operation is inherently non-idempotent.
- Predict the action in check mode without performing external side effects.
- Publish only outputs that callers need to continue the workflow.
- Avoid interactive input unless interaction is the role's explicit purpose.
- Remove temporary files, sessions, and resources created by the workflow.

## Host configuration roles

### Platforms and packages

- Support only platforms declared in `meta/main.yml` and exercised in tests.
- Branch on `ansible_facts.os_family` or another stable Ansible fact.
- Use a common module when it preserves required behavior across platforms.
- Use platform modules when their contracts materially differ.
- Load platform variable files only for real data differences.
- Do not install packages or repositories unrelated to the role contract.
- Declare package, repository, and service states explicitly.

### Files and templates

- Use `copy` for static content and `template` only for rendered content.
- Keep templates deterministic and limited to role inputs and stable facts.
- Set destination ownership and permissions when they are part of the
  resource or security contract.
- Quote permission modes so YAML cannot reinterpret them.
- Give directories traversal permissions required by their intended users.
- Give files execute permissions only when the file is intended to execute.
- Restrict credentials, tokens, keys, and private configuration to the least
  permissive useful owner, group, and mode.
- Notify a handler only when a changed file requires a service action.

### Services and handlers

- Use handlers for reloads, restarts, and other change-triggered actions.
- Name handlers with the action and affected service.
- Notify handlers by their exact, stable name.
- Prefer reload over restart when reload fully applies the change.
- Apply the role tag, privilege requirements, and safety conditions to
  handlers as well as ordinary tasks.
- Guard handlers that cannot run safely in check mode.
- Keep service enablement and runtime state explicit.

## Dependencies

- Declare only true prerequisites in `meta/main.yml`.
- Treat a dependency as a role that runs first, not as a child scope.
- Declare an info role as a dependency when a manager consumes its facts.
- Pass the manager role's tag through each dependency.
- Add dependency conditions only for supported platform or feature branches.
- Consume a dependency's public facts, never its internal variables.
- Avoid dependency cycles and hidden ordering between unrelated roles.
- Keep dependency inputs and the README dependency list synchronized.

## Security

- Keep credentials and secret material out of defaults, examples, labels,
  debug output, registered public facts, and failure messages.
- Apply `no_log` to every task and async status path that can expose a secret.
- Do not disable TLS certificate validation by default.
- Pass certificate validation as `true` when a module exposes the option, or
  use a public override whose default remains `true`.
- Use HTTPS and provider-supported integrity checks for downloaded artifacts.
- Do not make sensitive files readable by users that do not require access.
- Avoid logging complete provider results when they may contain secret data.

## Metadata and documentation

### Metadata

- Keep `meta/main.yml` valid and complete.
- Set `role_name`, `author`, `description`, `license`,
  `min_ansible_version`, `namespace`, `platforms`, and `galaxy_tags`.
- Match `role_name` to the role directory.
- Declare only platforms and Ansible versions the role supports.
- Keep Galaxy tags concise, lowercase, and relevant.

### README

- Include `Requirements`, `Role Variables`, `Dependencies`, and
  `Example Playbook` sections.
- Include `Return Values` when the role publishes facts.
- Document every public variable, its default, and its purpose.
- Document nested list and dictionary schemas callers must supply.
- State when `null`, an empty collection, or an omitted value disables work.
- List every role and collection dependency.
- Use the role's fully qualified collection name in examples.
- Use environment lookups or placeholders for credentials in examples.
- Keep examples minimal, representative, and ready to copy.

## Molecule

- Give every role a `molecule/default` scenario.
- Follow the repository's `molecule` skill for execution and cleanup.
- Exercise an empty or disabled invocation when it is part of the contract.
- Exercise check mode, converge, a second check, idempotence, and verification.
- For manager roles, verify create, stable state, and cleanup or absence.
- For info roles, create representative fixtures and assert published facts.
- Verify sensitive fields are absent from public facts and displayed output.
- For host roles, verify files, permissions, rendered content, and services.
- Keep prerequisite fixture roles out of the role's idempotence measurement.
- Read credentials from the environment and never commit live values.
- Ensure verification removes external fixtures and destroys test instances.
- Do not depend on state left by another scenario or an earlier run.

## Verification

- Run `yamllint` and `ansible-lint` for every role change.
- Run the affected Molecule scenario through its complete test sequence.
- Run every dependent role scenario when a public fact contract changes.
- Confirm documentation, defaults, metadata, and tests describe one contract.
- Add focused regression coverage for every corrected role behavior.
