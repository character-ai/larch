# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Plan docs-only contract violated by bundled skill/script changes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-guideline-parser-output.txt
- **Severity**: important
- **Concern**: Issue #5338’s plan requires a docs-only change (“Touch no code”; only `ARCHITECTURAL_GUIDELINES.md`), but the branch still ships #5365 skill/script edits (`skills/implement/SKILL.md`, `step-architectural-guidelines-read.md`, `step-architectural-guidelines-read.sh`) alongside the new guidelines. Acceptance against #5338 therefore depends on files the plan forbids, plan traceability breaks, and selective rollback of guidelines vs Phase A cleanup is harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split #5365 skill alignment into a separate PR, or update the #5338 plan/issue to explicitly document the bundled skill changes before merge.
  - From codex-specialist-correctness-output.txt: move the helper change to its own PR, or revert it here so this branch only carries the guidelines file update.
  - From cursor-specialist-edge-cases-output.txt: Split PRs or update #5338 plan/acceptance to explicitly include the Phase A artifact-clearing script/SKILL changes.
  - From codex-specialist-edge-cases-output.txt: Move the skills/implement edits to a separate PR or revert them from this branch so only ARCHITECTURAL_GUIDELINES.md changes remain here.
  - From cursor-specialist-testing-output.txt: Split into separate PRs or amend #5338 plan/acceptance to explicitly include the bundled #5365 skill changes.
  - From dyn-dyn-guideline-parser-output.txt: Split the work: land the guidelines-only diff on its own branch/PR, or amend the #5338 plan/acceptance to explicitly include the Phase A cleanup routing before merging the combined branch.


### FINDING_2: invalidate_implement_note swallows OSError and may leave stale Phase A artifacts
- **Reviewer(s)**: dyn-dyn-guideline-parser-output.txt
- **Severity**: important
- **Concern**: Round 1 moved Phase A clearing to `architectural-guidelines invalidate` as the sole entry path, but `invalidate_implement_note()` swallows all `OSError` during deletion. If an artifact is a directory, permission-denied, or otherwise undeletable, `read` still returns `ARCHITECTURAL_GUIDELINES_STATUS=present` and Phase A can proceed with stale `architectural-guideline-staged-assessment.*`, `architectural-guideline-note.*`, or `architectural-guideline-materialized-diff.txt` from a prior run. The prior orchestrator `rm -f` loop would have aborted under `set -e` instead of continuing silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guideline-parser-output.txt: Fail closed from `invalidate_main` when any listed artifact survives deletion (non-zero exit and/or a warning KV), or stop swallowing non-`FileNotFoundError` `OSError` now that invalidate is authoritative; keep directory cleanup via `shutil.rmtree` rather than bare `rm -f`.


