### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Extract duplicated plan-review-loop dedup/parity/renumber Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` embeds multiple inline Python heredocs and duplicate ballot-renumber logic, making marker/dedup/parity behavior difficult to test and maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a committed findings dedup/parity/renumber module; invoke once from plan-review-loop.sh; delete duplicate ballot-renumber heredoc.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Factor duplicated larch:plan marker-count validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan-block-strip-body.sh` duplicates malformed marker-counting logic from `plan-block-read.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optionally factor shared marker-count helper used by read and strip.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_14: Add revise prompt untrusted scope-evidence regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The revise harness does not assert the new untrusted scope-evidence preamble before the feature block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: grep revise prompt for untrusted scope evidence only line added in compose_prompt.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Harden raw plan/findings bodies in revise prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.sh` hardens feature scope text but still leaves plan and findings bodies raw in the same prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply redact_untrusted_stream to plan/findings sections or wrap them in escaped literal-redacted blocks


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Add revise staged-anchor argv assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The planned loop test does not assert revise receives the staged `plan-review-scope-anchor.txt` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Log revise argv in loop stub and assert plan-review-scope-anchor.txt is passed


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Remove or sanitize stale brainstorm feature-context sidecar
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: Brainstorm handling writes a sidecar feature-context file from unstripped original feature content, creating a latent alternate scope surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Either stop writing the sidecar until something actually consumes it, or build it from the same stripped anchor body (and keep brainstorm clearly non-binding) so no parallel feature narrative can become the accidental binding input.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: Preserve strip-helper stderr for debuggability
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Scope-anchor materialization suppresses `plan-block-strip-body.sh` stderr, hiding useful diagnostics behind a generic failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Drop the stderr redirect (or tee stderr into `$DESIGN_TMPDIR/plan-strip.stderr` and append it to the `larch_err` message) while keeping stdout KV parsing unchanged.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_35: Route strip-helper line-number failures through structured MALFORMED output
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `plan-block-strip-body.sh` can abort under `pipefail` while resolving malformed marker line numbers instead of emitting a structured `MALFORMED=` token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Guard the pipeline with `set +e`, verify `start_line`/`end_line` are non-empty integers, and route empty/invalid results through `emit_malformed` (e.g. a dedicated token) instead of dying in the pipeline.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: Avoid orphaned marker-detector temp files
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Marker detector temp files are created under the default temp directory with `delete=False`, so crashes can leave orphan files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Create temp files under `$DESIGN_TMPDIR` (or pass `dir=os.environ["DESIGN_TMPDIR"]` when set), and/or register an `atexit` cleanup list so marker-detector temp files cannot accumulate across long multi-round runs.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Extract aggregate-findings tagged-block helper logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation scatters marker preservation logic across multiple inline Python blocks using subprocess/tempfile detector calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared Python helper for split/append/renumber/validate tagged blocks.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

