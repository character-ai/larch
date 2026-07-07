# Review Round 2

- Mode: `diff`
- 4 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Validation zero-externals branch uses empty COLLECT_ARGS too early
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `COLLECT_ARGS` is initialized empty before bgjob waits, but the validation zero-externals branch still treats emptiness as proof that no externals exist. That can skip Cursor/Codex waits even after those lanes were launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Gate on cursor_binary_available and codex_binary_available flags; move or rephrase the empty-COLLECT_ARGS check to after the wait loop.
  - From codex-specialist-edge-cases: Replace the parenthetical array check with explicit launched flags, such as `VALIDATION_CURSOR_STARTED` and `VALIDATION_CODEX_STARTED`, and reserve `COLLECT_ARGS` emptiness for the post-wait “no surviving externals” branch.


### FINDING_2: Research/validation post-wait empty COLLECT_ARGS branch is missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: After bgjob waits/fallback routing, `COLLECT_ARGS` can still be empty, but collect-results is still invoked instead of skipping to fallback-only completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add post-wait branch to skip collect-results when COLLECT_ARGS is empty after fallbacks.
  - From codex-specialist-correctness: Add a post-wait empty-COLLECT_ARGS branch in both phases that skips collect-results, merges fallback outputs, and proceeds.
  - From cursor-specialist-edge-cases: Skip collect-results when COLLECT_ARGS is empty after waits; continue to Step 1.5 on fallback outputs
  - From codex-specialist-edge-cases: Skip collect-results when COLLECT_ARGS is empty after waits; finalize on Claude-only findings
  - From dyn-dyn-bgjob-contract: After bgjob waits finish, add an explicit `COLLECT_ARGS` empty guard. If no external output path passed the bgjob gate, skip `collect-results` and continue with the fallback outputs; otherwise collect only the passed paths.


### FINDING_4: Fallback runtime status tokens are never rewritten
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: Lanes that fail the bgjob gate are routed through Claude fallback before collection, but the status rewrite still only uses collector output, so failed lanes can keep their Step 0 `ok` status and report the wrong attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: When a lane fails the bgjob start/wait gate, surgically set the matching `RESEARCH_<SLOT>_STATUS` / `_REASON` to the appropriate `fallback_runtime_*` token before synthesis, using the same vocabulary as the collector table.
  - From dyn-dyn-bgjob-contract: Mirror the collector status table for bgjob-gate failures: when `bgjob wait` returns `DEAD`, non-zero `BGJOB_RC`, or missing required KVs, update the corresponding `VALIDATION_*` slice to `fallback_runtime_timeout` or `fallback_runtime_failed` before merging findings.


### FINDING_5: bgjob wait can trust stale result envs from a prior run
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: The wait contract never requires a `bgjob start` success marker, so a failed start can leave a stale result env that makes `bgjob wait` report `DONE` for a lane that never launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: State explicitly that `bgjob wait` is forbidden unless the matching start printed `BGJOB_STATUS=STARTED STEP=<slug>`; on any other start outcome, route straight to the lane failure/fallback branch without waiting. Apply the same rule in `validation-phase.md` for `validation-cursor` / `validation-codex`.


