### OOS_1: [OUT_OF_SCOPE] assess-plan-round still falls back to IMPLEMENT_TMPDIR feature file
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` can fall back to `$IMPLEMENT_TMPDIR/feature-description.txt`, conflicting with the design-session source precedence rule applied elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Round summary SCOPE_ANCHOR_FILE write bypasses env writer
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: nit
- **Concern**: `_write_round_summary` writes `SCOPE_ANCHOR_FILE` via raw `printf` instead of the CR/LF-rejecting phase env writer; reviewer judged practical risk low because the path is currently constant under `$DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_11: [OUT_OF_SCOPE] MainAgent renderer lacks dead-script/lint registration and harness
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: latent
- **Concern**: The MainAgent renderer is not registered in `agent-lint.toml` dead-script exclusions and has no dedicated harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] Dedup Python identity-based merge is a maintainability smell
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: The embedded dedup Python calls `choose_tagged_body(kb, blk)` twice and uses `is blk` identity to choose operands; reviewer marked this outside Bash portability scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_13: [OUT_OF_SCOPE] Positive Bash portability assessment
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted most touched shell follows existing repo conventions and avoids Bash 4-only constructs in runtime paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_14: [OUT_OF_SCOPE] compute-pr-line-counts coerces nonnumeric API fields to zero
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: nit
- **Concern**: Awk summation treats nonnumeric `additions`/`deletions` as zero while still emitting `LINES_STATUS=ok`; reviewer judged this unlikely with GitHub’s schema.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_15: [OUT_OF_SCOPE] PR-files test fixtures are duplicated
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: nit
- **Concern**: The `gh` PR-files shim/fixture is duplicated across line-count and final-report harnesses, creating fixture drift risk but no runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] decompose-panel-dispatch remains unanchored
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: `decompose-panel-dispatch.sh` still binds `--feature-file` to raw `feature-description.txt` without stripping plan blocks or using staged scope anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] brainstorm feature-context file is written but unused
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is created for brainstorm runs, but no downstream production script reads it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] lib-vote-tally helper path/block mismatch
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: nit
- **Concern**: `is_scope_reduction_block` is documented as taking a block but actually passes its argument as a file path; production does not call it today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] aggregate-findings fallback marker-loss test missing
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: latent
- **Concern**: Existing plan-mode happy-path coverage does not test validation-failure fallback preserving tagged `[SCOPE-REDUCTION]` blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] collect-findings TSV marker regression missing
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: latent
- **Concern**: `test-collect-findings.sh` lacks a lower-risk regression for TSV `what: [SCOPE-REDUCTION]` folding into severity-prefixed Concern bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Positive prompt-boundary hardening noted
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted positive branch behavior: several prompt renderers share redaction/HTML-escape patterns with delimiter-breakout harness coverage, and non-Read-tools context files are redacted/escaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Voter ballot file remains raw path-loaded
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: latent
- **Concern**: Voters still load `ballot.txt` by filesystem path without inline escaping; this predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] READ_TOOLS branch still reads staged files raw
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh`’s `READ_TOOLS=true` branch continues to rely on models reading staged files without inline escaping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

