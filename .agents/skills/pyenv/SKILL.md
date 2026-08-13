---
name: pyenv
description: Install pyenv and the project's pinned Python. Use before the tox skill when the .python-version interpreter is missing.
---

# pyenv

Install `pyenv` via Homebrew, install the Python pinned in `.python-version`, and activate it so
Tox builds disposable environments against the right interpreter.

```sh
brew install pyenv
eval "$(pyenv init -)"
pyenv install -s "$(cat .python-version)"
```

`.python-version` already pins the version, so pyenv selects it automatically once the shims are
active. Confirm:

```sh
pyenv version
python --version
```

- Run once, before the `tox` skill, if the pinned Python isn't installed.
- Do not modify a shell profile unless the user explicitly requests a persistent setup.
- On other platforms, use the platform's supported pyenv installation method rather than
  Homebrew.

## Dependencies

- `pyenv`; Homebrew is required only for the macOS installation command above.
