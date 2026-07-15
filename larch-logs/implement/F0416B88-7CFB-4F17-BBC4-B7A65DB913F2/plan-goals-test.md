## Goal
Implement issue #7370: [IMPLEMENTING] [BUG] ci-fixer returns FIXER_RESULT=committed instead of pushed when MODE=checks is passed in the ship-pr ci-fix loop, breaking result routing.

## Implementation Plan
## Summary

The `larch:ci-fixer` agent returns `FIXER_RESULT=committed` instead of `FIXER_RESULT=pushed` when the orchestrator accidentally passes `MODE=checks` in the ci-fix loop spawn prompt. Per the agent contract, `MODE=checks` disables the push step and changes the result token to `committed`; only `MODE=ci` (the default when `MODE` is absent) pushes and returns `pushed`. The SKILL.md ci-fix loop says "Its prompt contains only: …" — `MODE` is not in that list — but an easy confusion with the adjacent `checks repair-loop` section (which explicitly passes `MODE=checks`) causes orchestrators to pass the wrong mode. The ci-fix round-loop has no handler for `committed`; the result falls through to the "bail or unparseable" branch and triggers an unnecessary fresh respawn, even though the commit is already present on the remote.

## Original report

`larch:ci-fixer` subagent returns `FIXER_RESULT=committed` instead of `FIXER_RESULT=pushed` after successfully pushing, causing the orchestrator to misroute the result.

## Reproduction scenario

1. Run `/implement --merge` on an issue that requires CI fixes.
2. The ship-pr driver reaches `NEXT_ACTION=ci-fix`.
3. The orchestrator spawns `larch:ci-fixer` with `MODE=checks` (mistakenly copied from the checks-repair-loop spawn pattern).
4. The ci-fixer reads `MODE=checks`, commits the fix locally, and returns `FIXER_RESULT=committed` per its mode contract. It does not push.
5. The orchestrator inspects `git log --oneline origin/<branch>..HEAD` and finds the commit is on the remote (because the operator also instructed the fixer to push via the spawn prompt, overriding the mode contract in an inconsistent way), but the `FIXER_RESULT` token is `committed`.
6. The SKILL.md ci-fix result parser has no branch for `committed`; it falls into the "bail or unparseable" respawn path, triggering an unnecessary second fixer round.

Observed in run `EB717A1C-6FB8-47C5-9C91-D904595043BD`: ci-fix rounds 1 and 2 both returned `committed`; each required a manual git push and salvage after the Bash tool noted the commit was already on the remote.

## Expected behavior

- The SKILL.md ci-fix loop spawn instructions explicitly state that `MODE=ci` must be used (or that `MODE` must be omitted, relying on the default).
- `FIXER_RESULT=pushed` is returned after a successful push.
- The ci-fix loop relaunches `step-8-ship.sh` immediately.

## Observed behavior

- The ci-fixer returns `FIXER_RESULT=committed` (MODE=checks path: no push).
- The ci-fix loop treats `committed` as an unrecognized token and routes to the `bail`/unparseable respawn path.
- The orchestrator has to manually inspect git state to determine whether to push and continue.

## Root cause analysis

Two contributing factors:

1. **Ambiguous SKILL.md spawn instructions**: the SKILL.md ci-fix loop says "Its prompt contains only: the repository root, the working branch, the PR URL, the `CI_ERRORS_FILE` path, the rounds-file path, the round number, and the contract reminders from `agents/ci-fixer.md`." `MODE` is absent from this list. The ci-fixer defaults to `MODE=ci` when MODE is unset, which is correct. However, there is no explicit warning not to add `MODE=checks`. By contrast, the adjacent checks-repair-loop section of SKILL.md says "Spawn `larch:ci-fixer` with only: `REPO_ROOT`, `BRANCH_NAME`, `MODE=checks`, …" — an orchestrator reading both sections in the same turn can easily copy the `MODE=checks` token.

2. **Missing `committed` handler in the ci-fix result parser**: the SKILL.md ci-fix result section lists three branches: `FIXER_RESULT=pushed`, `FIXER_RESULT=no-progress`, and `FIXER_RESULT=bail` (or unparseable). There is no branch for `FIXER_RESULT=committed`, so that token falls through to the `bail`/respawn path even when the commit is fully on the remote and only needs `step-8-ship.sh` to be relaunched.

## Evidence

- `agents/ci-fixer.md:36`: "Treat absent `MODE=` and legacy `MODE=ci-fix` as `MODE=ci`."
- `agents/ci-fixer.md:49–55`: "When `MODE=ci`, push the commit. … When `MODE=checks`, do **not** push."
- `agents/ci-fixer.md:70`: "For `MODE=ci` alone the trailer values are `FIXER_RESULT=pushed|no-progress|bail` (plus `committed` only when `MODE=checks`)."
- `skills/implement/SKILL.md` ci-fix Round 1 instructions: "Its prompt contains only: the repository root, the working branch, the PR URL, the `CI_ERRORS_FILE` path, the rounds-file path, the round number, and the contract reminders from `agents/ci-fixer.md`." — `MODE` is absent.
- `skills/implement/SKILL.md` ci-fix result parser: branches on `pushed`, `no-progress`, and `bail` only; no `committed` branch.
- `skills/implement/references/checks-repair-loop.md` §2: "Spawn `larch:ci-fixer` with only: `REPO_ROOT`, `BRANCH_NAME`, `MODE=checks`, the lint site token…" — the source of the confusion.

## Affected files

- `skills/implement/SKILL.md` — ci-fix Round 1 spawn instructions and the ci-fix result parser need updating.
- `agents/ci-fixer.md` — no change needed to the contract; the agent behavior is correct. Documentation may benefit from an explicit "MODE=ci is the mode for ship-pr CI recovery" callout.

## Suggested fix(es)

**Fix 1 (SKILL.md spawn instructions)**: add an explicit note to the ci-fix Round 1 spawn instructions: "Do not pass `MODE`; the ci-fixer defaults to `MODE=ci`, which commits and pushes the fix. Passing `MODE=checks` produces `committed` instead of `pushed` and breaks the ci-fix round-loop routing."

**Fix 2 (SKILL.md result parser)**: add a `committed` handler to the ci-fix result parser: if `FIXER_RESULT=committed` and `FIXER_COMMIT` is a non-empty SHA, treat it as `pushed` (the fixer committed locally; the orchestrator pushes via `python3 … push branch` and then relaunches `step-8-ship.sh`). This makes the result parser robust against accidental `MODE=checks` usage without breaking the normal path.

## Open questions

- Should the ci-fixer itself detect that `MODE=checks` was passed in a ci-fix context (e.g., when `PR_URL` is in the spawn prompt) and escalate to `pushed` automatically? That would make the agent more self-healing but would blur the mode contract.

## Test plan
(no test plan section in plan-file)
