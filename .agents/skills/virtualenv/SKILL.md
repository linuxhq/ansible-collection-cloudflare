---
name: virtualenv
description: Set up and use the project's virtualenv. Run make to bootstrap venv/ from pinned requirements; every other skill's tooling lives here.
---

# virtualenv

All tooling runs from a local `venv/` pinned by `requirements.txt`. Every other skill calls
`venv/bin/{{ tool }}`, so set this up first.

```sh
make
source venv/bin/activate
```

Activating is optional.

Sub-targets:

- `make venv` — create the venv.
- `make python` — install/repin Python deps.
- `make galaxy` — install collection deps.
- `make pre-commit` — install the pre-commit hook.
- `make clean` — remove the venv.

Re-run `make` (or `make python`) if a `venv/bin/{{ tool }}` is missing or the wrong version.
`venv/` is git-ignored.

## Dependencies

- `pyenv` skill (provides the pinned Python)
