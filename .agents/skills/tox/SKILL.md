---
name: tox
description: Use Tox to prepare this project's named disposable development and test environments. Use for local tooling setup, environment recreation, or before invoking another repository skill.
---

# tox

Use the externally installed Tox launcher to install the pre-commit hook:

```sh
tox run -e pre-commit
```

Run grouped environments by label:

```sh
tox run -m format
tox run -m lint
tox run -m unit
```

Do not activate a shared virtualenv. Each repository skill invokes its named, disposable
`.tox/<environment>` directly. Tool versions are pinned in `requirements.txt`; use
`tox recreate -e <environment>` to rebuild one.

## Dependencies

- `pyenv` skill (provides the pinned Python)
