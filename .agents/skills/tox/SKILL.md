---
name: tox
description: Set up and recreate the collection's Tox development and test environments.
---

# tox

- Run from the collection root using the externally installed Tox launcher.
- Use the `pyenv` skill first if the Python pinned in `.python-version` is missing.
- Each tool uses its named disposable `.tox/<environment>`; do not activate a shared virtualenv.
- Tool versions are pinned in `requirements.txt`.
- Install the pre-commit hook during local setup:

```sh
tox run -e pre-commit
```

- Run grouped environments by label:

```sh
tox run -m format
tox run -m lint
tox run -m unit
```

- `format` runs formatters and automatic fixes; `lint` runs checks; `unit` runs unit tests.
- Use `tox recreate -e <environment>` to rebuild a named environment.
