# `extract-closes-issue-from-pr.sh`

## Purpose

Extract the first `Closes #<N>` issue number from the body of the PR
associated with the current git branch. Wraps the multi-pipe `gh pr view |
grep | head | grep` invocation that previously lived inline in
`skills/implement/SKILL.md` **Step 0** (PR-body recovery branch inside the folded tracking-adoption block), so the
SKILL.md prose owns intent and the shell pipeline lives in a single
testable location (per `.claude/rules/script-md-siblings.md`).

## Inputs

None. The script reads PR state from `gh` against the current branch. It first resolves the current repo with `scripts/resolve-repo.sh` and passes `--repo` to `gh pr view` when resolution succeeds; if resolution fails, it preserves the prior ambient-repo fallback.

## Outputs

- **stdout**: the matched issue number (digits only), or empty when no PR
  exists on the current branch or the PR body has no `Closes #<N>` line.
- **stderr**: silenced (`gh pr view` errors are swallowed by `2>/dev/null`
  to keep "no PR on this branch" indistinguishable from "no `Closes` line",
  matching the pre-extraction inline behavior).
- **Exit code**: always `0`. The empty-stdout case is normal (no PR, or no
  match) and must not be treated as an error by callers.

`set -e` is in force: hard failures in the pipeline (other than the
expected `grep` no-match) propagate via `pipefail`, but the trailing
`|| true` neutralizes the no-match exit so the script always exits `0`.

## Caller

Single caller: `skills/implement/SKILL.md` **Step 0** PR-body recovery branch ("PR on
current branch with `Closes #<N>`"). The caller assigns the captured
stdout to `RECOVERED_N` and treats an empty value as "fall through to
the next adopt-by-number branch".

## Edit-in-sync rules

If the recovery grammar in that branch changes (e.g. accepts `Fixes #<N>` in
addition to `Closes #<N>`), update both this script's pipeline and the
prose in `skills/implement/SKILL.md` **Step 0** (PR-body recovery) in the same PR.
