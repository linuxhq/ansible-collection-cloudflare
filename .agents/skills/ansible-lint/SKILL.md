---
name: ansible-lint
description: Lint roles and playbooks with ansible-lint through Tox.
---

# ansible-lint

- Use the `tox` skill for environment setup and run from the collection root.
- Replace `{{ role }}` with the role name.
- Fix findings by hand or use `--fix`; review rewritten files.

```sh
tox run -e ansible-lint -- roles/{{ role }}
tox run -e ansible-lint -- --fix roles/{{ role }}
```

- Run `tox run -m lint` for the full lint suite.
