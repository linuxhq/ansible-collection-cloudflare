---
name: ruff
description: Lint Python plugin code with ruff through Tox. Run after every edit under plugins/.
---

# ruff

```sh
tox run -e ruff-lint -- plugins/modules/{{ file }}.py
tox run -e ruff -- plugins/modules/{{ file }}.py
tox run -m lint
tox run -m format
```

- Clean run: `All checks passed!`.
- Fix by hand what `--fix` can't; re-read rewritten files.
- ruff only lints — format with `black`.

## Dependencies

- `tox` skill
