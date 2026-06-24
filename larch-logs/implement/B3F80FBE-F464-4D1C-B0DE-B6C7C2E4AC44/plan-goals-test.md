## Goal
Implement issue #5341: [IMPLEMENTING] [BUG] Orchestrator edits main before Step 0 bootstrap — issue not renamed to [IMPLEMENTING].

## Implementation Plan
## Summary

When `/implement --emergency` is invoked, the orchestrator (main Claude agent) can proceed past the Preflight semantic-materiality check into full code investigation and implementation **before** running Step 0 bootstrap. This leaves the repository in a broken state: uncommitted edits on `main`, no feature branch, no session tmpdir (`$IMPLEMENT_TMPDIR`), and the tracking issue title never renamed to `[IMPLEMENTING]`.

## Original report

User noticed that after `/im --emergency --self-review 5329` was invoked and the implementation changes were made, the tracking issue #5329 still had no `[IMPLEMENTING]` prefix in its title.

## Reproduction scenario

1. Run `/im --emergency --self-review <issue-N>` on a new issue (no `[DESIGNED]` prefix).
2. Preflight bypasses the `missing-designed-prefix` admission block (expected under `--emergency`).
3. Semantic materiality check (Preflight item 6) reads code to verify the issue is still actual.
4. Orchestrator continues reading code, understands what to change, and begins implementing inline (Edit/Write tool calls).
5. Lint/test runs fire against the edits.
6. Step 0 bootstrap (`step-0-bootstrap.sh`) is never invoked.

Observed: edits sit on `main`, issue title unchanged, no feature branch, no `$IMPLEMENT_TMPDIR`.

## Expected behavior

Step 0 bootstrap must run before any code mutations. The bootstrap creates the feature branch, sets up `$IMPLEMENT_TMPDIR` and `larch-run.sh`, adopts the tracking issue, and renames it to `[IMPLEMENTING] <title>`. All edits must land on the feature branch, not `main`.

## Observed behavior

- `git branch --show-current` → `main`
- `git status --short` → three modified files on `main`
- `gh issue view <N> --json title` → title still has no `[IMPLEMENTING]` prefix
- `$IMPLEMENT_TMPDIR` never set; `step-0-bootstrap.sh` never invoked

## Root cause analysis

The Preflight item 6 semantic-materiality check is specified as "one batched Bash probe block over plan-cited paths and symbols." The orchestrator overran this scope: instead of a bounded read-only probe followed by `continue to Step 0`, it performed a full code investigation and transitioned directly into Step 2 (implementation), bypassing Step 0 entirely.

The NEVER list in `skills/implement/SKILL.md` does not include an explicit rule against code mutations before Step 0. The skill relies on the orchestrator following the numbered step order, but offers no guard or warning that would surface the mistake when item 6 bleeds into implementation work.

A contributing factor is that item 6 and Step 2 both involve reading code to understand what to change. The boundary between "bounded materiality probe" and "implementation investigation" is easy to cross silently, especially under `--emergency` where the audit skip makes the path from preflight to code shorter.

## Evidence

- `git status --short` output: `M python/bootstrap.py`, `M python/test_bootstrap.py`, `M skills/implement/SKILL.md` (all on `main`)
- `git branch --show-current`: `main`
- `gh issue view 5329 --json title,state`: title unchanged, no `[IMPLEMENTING]` prefix
- `_perform_tracking_side_effects` in `python/bootstrap.py` (line 534) is where `tracking-issue rename --state implementing` fires — this was never reached because `step-0-bootstrap.sh` was never invoked

## Affected files

- `skills/implement/SKILL.md` — NEVER list and Preflight item 6 prose; could add an explicit guard
- `python/bootstrap.py` — tracking rename (`_perform_tracking_side_effects`) is the function whose invocation was skipped
- `skills/implement/scripts/step-0-bootstrap.sh` — the wrapper never invoked

## Suggested fix(es)

1. **Add a NEVER rule**: add `NEVER make Edit/Write/repo-mutating Bash calls between Preflight item 6 and Step 0 bootstrap completion` to the NEVER list. Distinguish "bounded read-only probe" (grep, test -f) from "full investigation leading to edits."
2. **Tighten item 6 prose**: specify explicitly that item 6 is a read-only probe only; if the probe triggers more investigation, that investigation must still precede Step 0, not replace it.
3. **Step 0 mandatory gate**: consider making the bootstrap a hard pre-condition with an explicit sentence: "Do not call Edit, Write, or any repo-mutating Bash before this fence returns."

Recovery for the current broken run: stash `main` edits, run `step-0-bootstrap.sh --mode initial` to set up the branch and rename the issue, cherry-pick or re-apply the stashed edits on the feature branch, then continue the run normally.

## Open questions

- Should the skill add a dirty-tree check at Preflight item 6 exit to catch pre-Step-0 mutations before they accumulate?
- Is there a mechanical way (e.g., a hook) to deny Edit/Write tool calls until `$IMPLEMENT_TMPDIR/larch-run.sh` exists?

## Test plan
(no test plan section in plan-file)
