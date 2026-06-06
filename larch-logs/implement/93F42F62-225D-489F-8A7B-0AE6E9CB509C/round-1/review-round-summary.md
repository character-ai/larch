# Review Round 1

- Mode: `diff`
- 8 accepted, 4 rejected (3 exonerated)

## Accepted Findings

### FINDING_12: Python `open-pr` resume skips pending OOS disposition gate
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` can resume at `open-pr` and proceed to PR/CI/merge while persisted `OOS_PENDING=true` or accepted/security OOS artifacts remain unresolved, unlike the Bash ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: On any resume path where `OOS_PENDING=true` (or accepted-OOS / security-OOS artifacts are present), run the same disposition gate as the fresh `pr-create` path before `ensure_pr`; if disposition is incomplete, return `NEEDS_USER_INPUT` with `NEEDS_USER_OOS_FILING` instead of proceeding.


### FINDING_13: Python fresh-resume fallback resets persisted counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `_fresh_resume_plan` zeroes iteration/rebase/fix/transient counters when resume classification falls back to fresh, allowing a flaky or failed resume check to restore merge-loop budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Either stall with a structured resume error when classification fails but counters are non-zero, or carry forward persisted counters on “degrade to fresh” paths instead of unconditionally resetting them in `_fresh_resume_plan`.
  - From dyn-ci-loop-output.txt: If parity with bash resume is required, preserve `read_resume_counters` on gh-failure fallbacks that still have a valid `PR_NUMBER` in state (route to `blocked` / retry rather than `fresh`), or at minimum preserve `iteration` when re-entering the merge loop for an existing PR.


### FINDING_14: Python `gh_skipped` resume can trust stale PR identity
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: In `gh_skipped` mode, `_resume_plan` can classify `open-pr` using persisted `PR_NUMBER` and branch checkout without the `gh pr view` head-ref validation used in normal mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: In `gh_skipped` mode, require an additional local anchor (e.g., persisted `PR_URL` match, `manifest.json` / `parent-issue.md` cross-check, or explicit operator `--pr-number` override) before classifying `open-pr`, or fail closed to `NEEDS_USER_INPUT` when PR identity cannot be corroborated.


### FINDING_15: Python `gh_skipped` resume can treat local manifest `done` as merged
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: In `gh_skipped` mode, manifest status `done` plus a PR number can route to post-merge finalization without remote merge confirmation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: In `gh_skipped` mode, require at least two independent merge signals (e.g., `PR_CLOSED=true` **and** `MERGE_RESULT` in post-merge set, or manifest `done` plus `post-merge-sentinel`) before selecting `merged`; otherwise stay on `open-pr` or stall.


### FINDING_19: Restored `.pause-requested` can trigger an immediate pause/save loop
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: important
- **Concern**: Successful pause-load restore copies `.pause-requested` from the snapshot into `DESIGN_TMPDIR`; later pause checkpoints can interpret it as a fresh pause request and re-save instead of continuing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: After a successful install (and before or after marker delete), unconditionally `rm -f "$DESIGN_TMPDIR/.pause-requested"` in `design-pause-load.sh`, or exclude `.pause-requested` from pause publishes in `design-log-publish.sh` even when `--reason pause`; add a harness case that seeds `.pause-requested` in the snapshot and asserts it is absent post-load.


### FINDING_4: Stale `archive_ref` variable name after archive removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.sh` still uses `archive_ref` after replacing `git archive` restore, which can mislead future edits into assuming archive semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: Marker retention is not tested for all load-failure tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests assert marker retention for some restore failures, but not for `snapshot-not-found` or restored issue/run/repo mismatch failures, so selective marker deletion could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Non-fatal marker-delete failure can leave resume marker stuck
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: After successful load, `clear_pause_marker` failure only emits a warning while leaving `LOAD_OK=true`. The stale `larch:design-pause` marker can cause later `/design` runs to keep attempting resume or require manual cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Retry delete in design-route after successful load, skip resume when [DESIGNED]+larch:plan exists, or treat WARN=marker-delete-failed as operator-blocking.
  - From dyn-resume-state-output.txt: Treat marker-delete failure as a distinct orchestrator-facing outcome (e.g., `LOAD_OK=true` plus a dedicated `MARKER_CLEARED=false` KV, or escalate to a loud operator halt) so resume success is not conflated with pointer cleanup.


