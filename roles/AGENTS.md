# AGENTS.md

## Model

gpt-5.5 high

## Standards

### Role behavior

* Keep roles list-driven unless the existing role intentionally manages a
  single resource

* Support check mode
  * Do not start async jobs in check mode
  * Use the established `changed_when` check-mode pattern when the underlying
    module can predict changes
  * Skip follow-up cloudflare reads or validation tasks in check mode when the
    data will not exist yet

* Support `state: present` and `state: absent` for resource-management roles
  when the underlying module supports both states

* Keep roles idempotent and avoid unnecessary cloudflare api calls

* Long-running operations
  * Use the established role defaults for `*_async`, `*_poll`, `*_delay`,
    `*_retries`, and `*_batch`
  * Batch resource lists through `tasks/main.yml` and process each batch in
    `tasks/include.yml` when the role follows that pattern
  * Pair async module calls with `ansible.builtin.async_status` tasks that only
    run for results containing `ansible_job_id`

### Variables

* Keep role variables prefixed with the role name

* Default resource lists to `[]` and info-role filter or id inputs to `{}` or
  `[]`, matching nearby roles

* Pass optional per-item values with `| d(omit)` unless the role has an
  established default for that option

* Keep required per-item values explicit in `when` guards instead of relying on
  undefined-variable failures

* Do not introduce unprefixed facts except for the established role outputs that
  begin with a single underscore, such as `_zones_info_list`

### Documentation

* Keep `README.md`, `defaults/main.yml`, and `meta/main.yml` aligned when
  adding, removing, or changing role variables, defaults, dependencies, return
  facts, examples, or role descriptions

* Keep README sections consistent with existing roles
  * Requirements
  * Role Variables
  * Return Values
  * Dependencies
  * Example Playbook

* Use the collection fqcn in role examples, such as
  `linuxhq.cloudflare.<role_name>`

* Document generated info-role facts in Return Values

### Tasks

* Use fully qualified collection names for modules and roles

* Prefer ansible builtin modules over `ansible.builtin.command` or
  `ansible.builtin.shell`

* Keep task names consistent across roles; majority convention wins
  * `Ensure cloudflare <resources> information is gathered`
  * `Ensure list of cloudflare <resources> information is generated`
  * `Ensure dict of cloudflare <resources> information is generated`
  * `Ensure cloudflare <resources> are batched`
  * `Ensure cloudflare <resources> are managed`
  * `Ensure managed cloudflare <resource> jobs are complete`

* Apply the role tag to every task, including included task files and async
  status tasks

* In `include_tasks`, use `apply.tags` so tagged runs include the child tasks

* Do not pass unsupported common module options to cloudflare module calls
  unless an existing role deliberately exposes a variable for them

* Do not mutate caller-provided resource items; derive transformed values in
  task arguments or temporary registered data

### Info roles

* Gather data with the matching info module and publish ansible-facing facts in
  snake_case

* For named resources, generate both list and dict facts when the source data
  has a stable name key

* Build dict facts from generated list facts so list and dict outputs remain
  consistent

* Keep info role outputs named `_role_name_info_list` and
  `_role_name_info_dict` unless the existing role uses a more specific
  established output

### Implementation style

* Keep changes focused on measurable behavior, consistency, or documentation
  correctness; avoid broad style churn

* Keep implementations simple, idempotent, and consistent across roles

* Use direct item access for required values and `| d(...)` defaults for
  optional values, matching nearby roles

* Prefer explicit loops and facts over dense Jinja expressions when the logic
  filters or reshapes cloudflare resources in multiple steps

* Do not add shared role abstractions unless several roles genuinely need the
  same stable behavior and the abstraction clearly reduces complexity

* Preserve existing file layout unless the role already uses a more specific
  task split, such as `present.yml`, `absent.yml`, or service-specific includes

### Molecule

* Keep molecule tests consistent across roles; majority convention wins

* Use `converge.yml` to exercise the role's present path and `verify.yml` to
  clean up or validate the absent path when that is the local pattern

* Keep molecule playbooks usable as README examples where practical

* Avoid adding destructive cleanup beyond resources created by the scenario

## Validation

* After role changes, run relevant checks
  * molecule
    * `../../venv/bin/molecule test -s default`
    * Run from the changed role directory
    * If a full molecule run is too expensive, run the narrow converge or
      verify step that exercises the changed behavior and state what was not run
  * ansible-lint
    * `venv/bin/ansible-lint roles/<role_name>`
  * yamllint
    * `venv/bin/yamllint roles/<role_name>`
  * git
    * `git diff --check`

## Workflow

* Complete the requested implementation before stopping

* Do not commit changes
