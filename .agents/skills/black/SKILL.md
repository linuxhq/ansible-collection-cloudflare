---
name: black
description: Format Python plugin code with black from the project virtualenv. Run after every edit to a file under plugins/ so it matches the black version CI enforces.
---

# black

Format Python with the venv's `black` (matches CI's pre-commit hook), after every edit to a
`plugins/**/*.py` file.

```sh
venv/bin/black plugins/modules/{{ file }}.py
venv/bin/black plugins
venv/bin/black --check plugins
```

- Re-read a file if black rewrote it.
- black only formats — lint with `ruff`.

## Dependencies

- `virtualenv` skill
