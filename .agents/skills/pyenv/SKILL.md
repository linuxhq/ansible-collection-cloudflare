---
name: pyenv
description: Install the Python version pinned in .python-version when it is missing.
---

# pyenv

- Run from the collection root before the `tox` skill if the pinned Python is missing.
- On macOS, install `pyenv` with Homebrew if needed:

```sh
brew install pyenv
```

- On other platforms, use the supported pyenv installation method.
- Activate pyenv in the current shell and install the pinned Python:

```sh
eval "$(pyenv init -)"
pyenv install -s "$(cat .python-version)"
```

- With shims active, `.python-version` selects the interpreter automatically.
- Confirm the selected version:

```sh
pyenv version
python --version
```

- Modify shell profiles only when the user requests persistent setup.
