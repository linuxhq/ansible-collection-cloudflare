---
name: ruff
description: Lint Python plugin code with ruff from the project virtualenv. Run after every edit to a file under plugins/.
---

# ruff

Lint Python with the venv's `ruff`, after every edit to a `plugins/**/*.py` file.

```sh
venv/bin/ruff check plugins/modules/{{ file }}.py
venv/bin/ruff check plugins
venv/bin/ruff check --fix plugins/modules/{{ file }}.py
```

- Clean run: `All checks passed!`.
- Fix by hand what `--fix` can't; re-read rewritten files.
- ruff only lints — format with `black`.

## Dependencies

- `virtualenv` skill
