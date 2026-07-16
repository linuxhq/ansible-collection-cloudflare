---
name: pyenv
description: Install pyenv and the project's pinned Python. Use before the virtualenv skill when the .python-version interpreter is missing.
---

# pyenv

Install `pyenv` via Homebrew, install the Python pinned in `.python-version`, and activate it so
the `virtualenv` skill builds `venv/` against the right interpreter.

```sh
brew install pyenv
pyenv install "$(cat .python-version)"
eval "$(pyenv init -)"
```

`.python-version` already pins the version, so pyenv selects it automatically once the shims are
active. Confirm:

```sh
pyenv version
python --version
```

- Run once, before the `virtualenv` skill, if the pinned Python isn't installed.
- To persist activation across sessions, add `eval "$(pyenv init -)"` to your shell profile
  (e.g. `~/.zshrc`).

## Dependencies

- Homebrew (`brew`)
