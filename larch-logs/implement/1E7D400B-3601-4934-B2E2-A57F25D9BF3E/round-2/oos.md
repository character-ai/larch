### FINDING_1: [OUT_OF_SCOPE] normalize-issue-env path-containment harness gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Case 21 path-containment tests cover other stall-recovery outputs but not `normalize-issue-env --issue-stdout-file` / `--output-file`; runtime guards exist, so this is a harness-only gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] unrelated run-log commit present
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: nit
- **Concern**: The branch includes a `larch-logs/implement/…` run-log commit unrelated to the stall-recovery fix surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: worth confirming it is intentional before merge.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] dry-run stdout is not explicitly rejected
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: `normalize-issue-env` does not explicitly reject filtered `ISSUE_1_DRY_RUN=true`; current grammar fails closed, but future stdout drift could make this unsafe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: an explicit `ISSUE_1_DRY_RUN` guard would harden the protocol against future stdout drift.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] sanitizer fixture does not isolate old prefix-glob behavior
- **Reviewer(s)**: dyn-issue-batch-output.txt
- **Severity**: nit
- **Concern**: The `8a<script>` unsafe-step fixture and added exact-only loop do not distinguish the new sanitizer regex from the old prefix `case` glob; production-token preservation remains the meaningful regression pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] pre-existing Step 18a classification gaps remain
- **Reviewer(s)**: dyn-issue-batch-output.txt
- **Severity**: latent
- **Concern**: Pre-existing Step 18a gaps around seeding in-memory `STALL_STEP`/`PHASE` before classification remain outside this diff and can affect classification/resume independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] test-stall-recovery-report.md omits normalize-issue-env case docs
- **Reviewer(s)**: dyn-prompt-protocol-output.txt
- **Severity**: nit
- **Concern**: The sibling `.md` contract text does not enumerate the `normalize-issue-env` harness cases, a doc-sync gap rather than a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-protocol-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] ISSUE_URL origin is not pinned to GitHub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `issue_value_is_url` accepts any `http(s)://` origin. Current consumers rely on numeric `ISSUE_NUMBER`, but surfacing `ISSUE_URL` later could make this a trust-boundary issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] resume_hint_for still uses raw permissive step patterns
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: latent
- **Concern**: `safe_step_value` now rejects non-canonical public title tokens, but `resume_hint_for` and related signature logic still consume raw `STALL_STEP` with prefix globs, so internal recovery routing can diverge from sanitized public issue metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align resume_hint_for with safe_step_value if internal/public parity is desired (separate change)
  - From dyn-issue-batch-output.txt: Route `resume_hint_for` (and signature hashing if step is meant to be canonical) through `safe_step_value` output, or share one allowlist function used by both resume routing and `issue-input-file` title synthesis.
  - From dyn-prompt-protocol-output.txt: worth tracking separately if internal dispatch ever needs the same grammar as public titles.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

