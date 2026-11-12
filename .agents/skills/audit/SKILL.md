---
name: audit
description: Audit plugins in passes with fresh read-only reviewers, fix every confirmed finding in a pull request reviewed by a second agent, and repeat until two passes in a row find nothing.
---

# audit

Audit a group of modules, or every file under `plugins/`, until two review
passes in a row find nothing. The repository's rules win over this skill.

Work without asking. Ask the user only when a finding has two valid paths;
name the one you recommend. Make breaking changes only with explicit approval.

The second agent is the other coding agent: Codex when Claude is primary,
Claude when Codex is primary. It reviews committed changes only; never start
it for reviews, triage, or probes.

## 1. Set up

- Enable the second agent's stop-time review gate:

| Agent  | Command                              |
| ------ | ------------------------------------ |
| Claude | `/codex:setup --enable-review-gate`  |
| Codex  | `$claude:setup --enable-review-gate` |

- Split the files into groups of related modules with their helpers and
  tests.
- Write a brief: the repository rules, the checklist below, the scope rule,
  and the decisions ledger.
- The ledger lists settled items with where each was decided: user
  decisions, dropped findings, and out-of-scope classes.

## 2. Review

- Start one new read-only subagent per group, all at once.
- Give each one its group, the brief, and the ledger, never earlier findings.
- Each reads every file in full: docs, examples, returns, helpers, and tests.
- Each checks the checklist, the provider's API reference and guides, and the
  pinned client library.
- Each writes its findings with evidence, marking anything unverified.
- No edits, git changes, live calls, or second agent during review.

## 3. Triage

- Verify every finding yourself or with a read-only subagent.
- Classify it: previously decided, out of scope, wrong, confirmed, or needs a
  live check.
- Out of scope: a value the provider rejects on the run's first write with
  nothing changed.
- In scope: a rejection after an earlier write in the same run, or a check
  the module already makes that disagrees with the provider.
- Settle "needs a live check" with a probe:
  - use only the user's authorized credentials and environment;
  - name resources with a unique prefix;
  - delete everything, even after a failure, and verify it;
  - report anything that could not be undone;
  - never touch resources the probe did not create.

## 4. Fix

- Start one fix subagent in its own worktree for all confirmed findings.
- It branches from an up-to-date default branch and fixes each finding at
  its source, checking siblings for the same pattern.
- It adds a regression test and a changelog entry for each fix.
- It runs formatting, lint, sanity, and unit tests.
- It verifies behavior changes live, against the default branch and the fix.
- It runs affected Molecule scenarios on the final commit, one at a time.
- It has the second agent review the branch diff, fixes what it confirms, and
  reviews again on the final commit.
- It opens a pull request describing only what was verified, and never
  merges.
- Its title is a conventional commit: the type that fits each change (a
  bug fix, docs, tests, refactoring, and so on), the affected modules as the
  scope, and a summary of what changed. When the pull request mixes types,
  the title names each. It never refers to the pass or audit.

## 5. Merge

- Report the pull request: changes, tests, live results, and the second
  agent's verdict.
- Merge only when the user says so, after every CI check has finished and
  passed; rerun infrastructure failures first.
- Remove the merged branch and worktree.
- Record the pass's outcome and any new decisions in the ledger.

## 6. Repeat

- Go back to step 2 with new reviewers on the updated default branch.
- A pass is clean when no finding is confirmed.
- Stop after two clean passes in a row; any merged fix restarts the count.

## Checklist

### Rules

- Follows every imported rule.
- Matches upstream projects the rules reference.
- Matches sibling modules.

### Inputs

- Options behave like their API parameters.
- Omitted options leave resources unchanged.
- Comparison-only values are never sent.
- Inputs keep the API's naming and accepted values.
- No options for unsupported parameters.

### State

- A second run reports no change.
- Outside changes converge or fail clearly.
- Unchangeable attributes fail before any modification.
- Every status is handled, including failed and deleting.
- Waits end on terminal states within their timeout.
- Reused names and tokens work after a delete.
- Comparisons do not treat Booleans and numbers as equal.
- Inherited settings carry the settings they depend on.

### Lookups

- Name lookups handle duplicates, foreign owners, and mid-run deletes.
- Info modules return empty results when nothing matches.
- Manager modules fail on missing required resources.
- Manager modules report no change for already-absent resources.
- Batched queries drop duplicates when one item can match several batches.

### Check mode and failures

- Check mode predicts the real result and changes nothing.
- The next run converges after a partial failure.
- Failures name the operation, resource, and blocker.
- Version and capability checks run before any write.

### Results and docs

- Result keys follow the naming convention; values are unchanged.
- User-defined keys keep their case at every level.
- Binary values are returned as valid UTF-8.
- Docs match options, defaults, and return values.
- Version requirements are checked and documented.
- Existing version checks stay, even for old versions.

### Maintenance

- No redundant API calls or duplicated code.
- No dead options, unused imports, or split strings.
- Shared helpers change only after every caller is checked.

### Roles

- Role behavior is unchanged unless a module fix requires it.
- Existing conditions, defaults, and skips stay as they are.
- Other role changes are proposed, not made.
- Optional inputs pass through without forced values.
- Role docs follow the repository's rules.
- Role READMEs change only variables, defaults, and examples.

### Tests

- Unit tests cover each behavior change.
- Each regression test fails without its fix.
- Changelog entries match the change; breaking changes are marked.

### Molecule

- Scenarios run every stage to completion.
- Scenarios run one at a time, never alongside others.
- No branch switches or edits while a scenario runs.
- Verify asserts changed behavior, including absent and empty cases.
- Dependent scenarios rerun when a shared role changes.
- Teardown polls for deletion instead of pausing.
- Non-reusable names are unique per run.
- Scenarios do not depend on earlier runs.
- Test edits keep the facts later steps rely on.
- No test resources remain, even after a failed or stopped run.
- Tasks that handle secrets use task-level `no_log`.
