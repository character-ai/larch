# Review Round 5

- Mode: `diff`
- 5 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: Step 5 resume aborts before re-running review after commit failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `step-5-resume.sh` runs under `set -e` and invokes `commit-review-fixes.sh --stage-all` without guarding failures, so an empty index, hook failure, or other non-zero commit path can prevent `run-step5-review.sh` from resuming the review loop and leave handoff fixes unreviewed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: correctness: Step 8 bash opt-in wrapper replays persisted RESUME_PHASE repeatedly
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The bash opt-in Step 8 wrapper can replay persisted `RESUME_PHASE` on every invocation. After OOS persists `RESUME_PHASE=pr-create`, a later retry may re-enter PR prep instead of continuing from persisted `PHASE` because `ship-pr.sh` does not clear the consumed token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: risk-integration: implement structure harness dropped required regression pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-implement-structure.sh` was reduced dramatically and appears to have dropped many regression pins that the plan required re-pointing, allowing future regressions in background fences, ship-pr state keys, removed `--auto` surfaces, and other anchors to pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: correctness: release dry-run sync fence can still mutate local main
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The release sync fence gates `rebase-push.sh` on `$dry_run` but does not set `dry_run` in the Bash block, so `/release --dry-run` can still run a rebase and violate the non-mutating dry-run contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: correctness: release sync rebases unpublished local main commits
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The non-dry-run release sync can rebase local `main` instead of only verifying or fast-forward syncing to `origin/main`, so unpublished local commits can be rewritten before later stale-main checks refuse the release.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


