---
name: ansible-lint
description: Lint roles and playbooks with ansible-lint from the project virtualenv. Run after every change under roles/.
---

# ansible-lint

Lint Ansible content with the venv's `ansible-lint` (matches CI's pre-commit hook), after every
change under `roles/`.

## Single role

```sh
venv/bin/ansible-lint roles/{{ role }}
venv/bin/ansible-lint --fix roles/{{ role }}
```

## Entire collection

```sh
venv/bin/ansible-lint
```

- Fix findings by hand, or with `--fix` where a rule offers it; re-read rewritten files.

## Dependencies

- `virtualenv` skill
