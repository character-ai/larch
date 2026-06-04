### [Plan Review] FINDING_2

### FINDING_2: Structural test for scrub-only ordering is brittle for multiline shell calls
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The proposed structural grep requires `design-log-publish.sh` and `--scrub-only` on the same line, but existing shell style may split command paths and flags across lines. A correct multiline implementation could fail the test or be forced into unnecessary formatting churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Derive scrub and flush positions with awk over each command block, or locate the --scrub-only flag line and associate it with the nearest design-log-publish.sh invocation instead of requiring both tokens on one line.


### [Plan Review] FINDING_4

### FINDING_4: `--scrub-only` stdout and side-effect contract is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan says scrub-only should emit `SCRUB_OK` and exit without `gh`, but existing validation/staging paths emit `PUBLISH_OK=false`, and the post-scrub path can continue into porcelain/git/PR behavior. `design-publish.sh` could misinterpret scrub-only as a publish result or allow publish side effects in scrub-only mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After argv sets scrub mode, branch all early failures to `emit_kv SCRUB_OK false` + exit 0; on scrub success emit `SCRUB_OK=true` (+ optional `SECRET_SCRUB_VIOLATIONS=`) and return before porcelain/commit/push/PR (worktree cleanup via existing trap).


### [Plan Review] FINDING_11

### FINDING_11: Tests do not cover malformed scrub-only output
- **Reviewer(s)**: Codex-dyn-scrub-boundary
- **Severity**: latent
- **Concern**: Planned tests cover `SCRUB_OK=false` but not scrub-only nonzero exit or exit 0 without `SCRUB_OK=...`. A malformed scrub-only result could leave admission reason unset or be misclassified as a publish/rename failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-scrub-boundary: Add one minimal scrub-only malformed-output case that asserts no rename, ADMISSION_READY=false, ADMISSION_BLOCK_REASON=scrub-failed, and no publish/rename-failure guidance


