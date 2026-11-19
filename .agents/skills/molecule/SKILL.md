---
name: molecule
description: Run a role's Molecule scenario through Tox.
---

# molecule

- Use the `tox` skill for environment setup.
- Run from the collection root; replace `{{ role }}` with the role name.
- Scenarios create real infrastructure and may incur costs. Before creating resources,
  ensure the user has authorized the run and confirmed the credentials and target environment.
- The scenario also serves as the role's example playbook.

```sh
MOLECULE_ROLE={{ role }} tox run -e molecule -- syntax -s default
MOLECULE_ROLE={{ role }} tox run -e molecule -- test -s default
```

- `syntax` checks playbook syntax.
- `test` runs the full create / converge / verify / destroy cycle.
- `converge` applies the converge playbook without teardown.
- `destroy` removes resources created by the scenario.
- If a test fails or is interrupted before cleanup, run the command below unless
  the user asks to preserve resources for diagnosis.

```sh
MOLECULE_ROLE={{ role }} tox run -e molecule -- destroy -s default
```

## Writing scenarios

Every role has one `default` scenario. Use only the playbooks Molecule
provides; do not add other playbooks or included task files.

Set this test sequence in `molecule.yml`:

```yaml
scenario:
  test_sequence:
    - dependency
    - cleanup
    - destroy
    - syntax
    - create
    - prepare
    - check
    - converge
    - check
    - idempotence
    - verify
    - cleanup
    - destroy
```

| File            | Purpose                                                                 |
| --------------- | ----------------------------------------------------------------------- |
| `molecule.yml`  | Inventory shared by more than one playbook, such as the role's inputs.  |
| `prepare.yml`   | Only when needed: install or create what the role depends on.           |
| `converge.yml`  | Run the role with its defaults, then with the scenario's inputs.        |
| `verify.yml`    | Assert the result, then change it and assert each change.               |
| `cleanup.yml`   | Re-run the role with `state: absent`; no assertions.                    |

- `converge.yml` first runs the role with its defaults, which must pass or
  skip cleanly, then runs it with the inputs from `molecule.yml` to do the
  initial provisioning. Both runs must be idempotent.
- `verify.yml` asserts the initial provisioning. It may then apply further
  changes, one task per change, and assert each one.
- `cleanup.yml` tears the provisioning down by re-running the role with
  `state: absent`, and puts back account-level settings the scenario changed
  by re-running the role with hardcoded values. It contains no assertions: if the role did its job,
  the resources are gone. Molecule runs it before `destroy` at the start and end of the
  sequence and after a failed step, so it must succeed whether or not the
  resources exist. Keep teardown out of `verify.yml`.
