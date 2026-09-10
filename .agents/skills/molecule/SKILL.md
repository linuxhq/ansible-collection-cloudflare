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
- Use `no_log: true` and `diff: false` on tasks that handle credentials, even when
  scenario-level `diff: true` is enabled.
- If a test fails or is interrupted before cleanup, run the command below unless
  the user asks to preserve resources for diagnosis.

```sh
MOLECULE_ROLE={{ role }} tox run -e molecule -- destroy -s default
```
