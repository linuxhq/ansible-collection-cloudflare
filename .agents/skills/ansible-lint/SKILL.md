---
name: ansible-lint
description: Lint roles and playbooks with ansible-lint.
---

# ansible-lint

Match CI's pre-commit hook.

```sh
tox run -e ansible-lint -- roles/{{ role }}
tox run -e ansible-lint -- --fix roles/{{ role }}
tox run -m lint
```

- Fix findings by hand, or with `--fix` where a rule offers it; re-read rewritten files.

## Dependencies

- `tox` skill
