---
name: molecule
description: Run a role's molecule scenario from the project virtualenv. Scenarios hit real Cloudflare and double as the role's example playbook; run from the role directory.
---

# molecule

Test a role with its `molecule/default/` scenario, run from the role's own directory.

```sh
cd roles/{{ role }}
../../venv/bin/molecule test -s default
../../venv/bin/molecule converge -s default
```

- `test` runs the full create / converge / verify / destroy cycle.
- `converge` runs only the present path, no teardown.
- Scenarios hit **real Cloudflare**.
- The scenario doubles as the role's example playbook.

## Dependencies

- `virtualenv` skill
