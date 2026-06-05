### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: MainAgent scope-anchor renderer is missing/unregistered and untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-flow-output.txt, dyn-prompt-boundaries-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` invokes `skills/design/scripts/render-main-agent-scope-anchor.sh` for the MainAgent 0-judge fallback path, but reviewers report the helper is absent from HEAD and/or not wired into harnesses/lint. A clean checkout can fail before ballot adjudication, and the degraded path can lose the same redacted/escaped scope-anchor guarantees as reviewers/voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-flow-output.txt, dyn-prompt-boundaries-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Global context escaping may alter non-plan-review code samples
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-claude-subprocess.sh` now escapes all context-file contents, which may alter `<`/`>` in non-plan-review code samples and cause unrelated review paths to inspect changed text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: Marker detector strips only a narrow severity vocabulary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `check-scope-reduction-marker.sh` strips only `important`, `nit`, and `latent` before matching `[SCOPE-REDUCTION]`; other severity prefixes such as `[blocking]` would false-negative unless reviewer vocabulary is constrained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: redact-secrets failure aborts context prompt construction without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh` pipes context embedding through `redact-secrets.sh` under `pipefail`; redact failure aborts dispatch prompt construction rather than warning and degrading or surfacing a targeted retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Tagged tally neutral-threshold regression is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-tally-plan-review.sh` lacks the planned tagged `YES=1 NO=1` neutral threshold case, so tagged scope-reduction findings could be promoted or demoted incorrectly versus normal quorum behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: Tagged dedup merge can drop reviewer attribution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: In `skills/design/scripts/plan-review-loop.sh`, when both overlapping blocks are `[SCOPE-REDUCTION]` tagged and the first block is kept, `merge_reviewers(kb, kb)` can lose the second block’s `Reviewer(s)` attribution before tally/aggregation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Voter prompt still leads with finding-anchored proportionality
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: With `--scope-anchor-file`, `render-voter-prompt.sh` still gives generic finding-anchored EXONERATE guidance before the later issue-scope override, risking the same voter bias the branch aims to fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: Tagged dedup may retain a body the detector no longer classifies as tagged
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: important
- **Concern**: `choose_tagged_body` prefers token count, not detector-confirmed leading marker preservation. It can keep a merged body whose `[SCOPE-REDUCTION]` appears only in a detector-ignored field, risking ballot output without a recognized tagged scope-cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: Function-scoped RETURN trap is not cleared
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `_materialize_scope_anchor()` installs a `RETURN` trap but never clears it, so later function returns in the long-lived Bash driver can re-run cleanup unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: Marker helper lacks python3 preflight
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `check-scope-reduction-marker.sh` depends on `python3` but has no `command -v python3` guard, producing generic nested failures instead of actionable interpreter diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: aggregate-findings collapses distinct marker-split failures
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `aggregate-findings.sh` treats any non-zero from the plan-mode Python split the same, obscuring missing interpreter, syntax, unreadable helper, and helper rc 2 failures behind one generic warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: compute-pr-line-counts cleanup trap pattern is fragile
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `compute-pr-line-counts.sh` registers an `EXIT` trap, disables it, manually removes the temp file, and exits, creating an avoidable future cleanup hazard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: gh API failures for PR line counts lose diagnostics
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: latent
- **Concern**: `compute-pr-line-counts.sh` redirects `gh api` stderr to `/dev/null` and collapses all failures to `gh-failed`, leaving operators with `N/A` line counts but no actionable auth/rate-limit/repo/network breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_35: Missing/empty line-count helper output is silently treated as N/A
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` does not warn when the line-count helper is missing, non-executable, or emits no `LINES_STATUS`, masking packaging or permission regressions as ordinary unavailable line data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Scope-marker detection logic is duplicated inside plan-review-loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple inline Python blocks in `plan-review-loop.sh` duplicate tagged-detection subprocess logic already centralized in `check-scope-reduction-marker.sh`, creating drift risk across dedup, aggregation, and ballot renumber paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: check-scope-reduction-marker duplicates stdin/file implementations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/check-scope-reduction-marker.sh` has near-identical Python heredocs for `--file` and stdin paths, so marker-rule edits must be applied twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Scope-anchor materialization failure can proceed implicitly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `_materialize_scope_anchor` is called without an explicit failure gate. If strip/path/empty-body handling fails or future refactors bypass `errexit`, plan review can continue with a missing or stale `plan-review-scope-anchor.txt`, defeating the fail-loud scope-anchor contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-env-handoff-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

