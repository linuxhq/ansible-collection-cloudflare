---
name: molecule
description: Run a role's Molecule scenario through Tox. Scenarios hit real Cloudflare and require explicit authorization.
---

# molecule

Confirm the intended credentials and target account with the user before creating resources,
then run from the collection root:

```sh
MOLECULE_ROLE={{ role }} tox run -e molecule -- syntax -s default
MOLECULE_ROLE={{ role }} tox run -e molecule -- test -s default
```

- `test` runs the full create / converge / verify / destroy cycle.
- `converge` runs the scenario's converge playbook without teardown.
- `destroy` removes resources created by the scenario.
- Scenarios provision **real Cloudflare resources**, can incur cost, and require explicit user authorization.
- The scenario doubles as the role's example playbook.
- Credential-bearing preparation tasks must use `no_log: true` and `diff: false`; a scenario-level
  `diff: true` must never print credentials.
- If `test` is interrupted or fails before cleanup, run `molecule destroy -s default` unless the
  user asks to preserve resources for diagnosis.

## Dependencies

- `tox` skill
