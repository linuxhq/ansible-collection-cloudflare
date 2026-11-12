---
name: audit
description: Review modules with fresh reviewers from the primary agent, fix approved findings, have a second agent review each change, and open pull requests until two full passes find nothing.
---

# audit

Audit one group of related modules, or the whole collection, chosen by the
user. The repository's rules win over this checklist.

## Modes

- Group audit: one group the user names; one review pass, then fixes.
- Full audit: every file under `plugins/`, split into groups, reviewed in
  passes until two consecutive passes find nothing.

## Second agent

- The second agent is the other coding agent: Codex when Claude is primary,
  Claude when Codex is primary.
- It runs only through the stop-time review gate and the change review in
  Fixes, after a change is committed.
- Never start the second agent for review passes, triage, or live probes.
- Before the first review, enable its stop-time review gate:

| Agent  | Command                              |
| ------ | ------------------------------------ |
| Claude | `/codex:setup --enable-review-gate`  |
| Codex  | `$claude:setup --enable-review-gate` |

## Review passes

- Only the primary agent's own subagents review files.
- Each pass uses new reviewers; never reuse a reviewer from an earlier pass.
- Give each reviewer one group, the brief, and the decisions ledger, not
  earlier findings or conclusions.
- Reviewers read the agent instructions and every imported rule first.
- Reviewers read every assigned file in full, including docs, examples,
  returns, helpers they call, and unit tests.
- Reviewers find what outside the group depends on it.
- Reviewers check docs and examples against the provider's API reference and
  guides, and client library behavior against the pinned library version.
- Reviewers are read-only: no edits, no git changes, no live calls.
- Reviewers report findings with evidence and mark breaking changes, open
  decisions, and anything unverified.
- A pass is clean when no reviewer reports a confirmed finding.
- Done means two consecutive clean passes after the last merged change.
- Any merged fix, however small, restarts the count.

## Decisions ledger

- Keep a ledger of settled items: user decisions, dropped findings, and
  out-of-scope classes, each with where it was decided.
- Give the ledger to every reviewer; settled items are not reported again.
- Record every pass's outcome and every new decision in the ledger.
- Only the user reopens a settled item.

## Scope

- A value the provider rejects on the run's first write, with nothing
  changed, is out of scope.
- A rejection is in scope when an earlier write in the same run has already
  happened, or when the module already validates that constraint and
  disagrees with the provider.
- Check-mode predictions are in scope when the value follows from the inputs.

## Triage

- Classify every finding before fixing it: previously decided, out of scope,
  wrong, confirmed, or needs a live check.
- Cite the ledger entry, rule, code, or reproduction behind each class.
- Settle "needs a live check" with a probe, not reasoning.
- Bring behavior or contract choices to the user before fixing.

## Live probes

- Run probes only with the user's authorized credentials and environment.
- Name probe resources with a unique, recognizable prefix.
- Delete everything a probe creates, even after a failure, and verify it.
- Report side effects a probe could not undo, such as resources the provider
  creates on first use.
- Never touch resources the probe did not create.

## Fixes

- Branch from an up-to-date default branch.
- Fix only confirmed findings the user approves.
- Make breaking changes only with explicit approval.
- Fix each bug at its source and check siblings for the same pattern.
- Add a regression test and changelog entry for each fix.
- Run formatting, lint, sanity, and unit tests.
- Verify behavior changes live, against the default branch and the fix.
- Run affected Molecule scenarios on the final commit, one at a time.
- Wait for running tests instead of working around them.
- Have a second, different agent review only the change, on its final
  commit; fix what it confirms and have it review again.
- Commit, push, and open a pull request; do not merge.
- Keep pull request descriptions in sync with the final commits.
- State only what was verified.

## Merging

- Merge only when the user says so.
- Merge only after every CI check has finished and passed; rerun
  infrastructure failures first.
- Remove merged branches and worktrees.

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
