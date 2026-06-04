### FINDING_13: [OUT_OF_SCOPE] Stale DESIGN_TMPDIR can hide design-export OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-evidence-logging-output.txt
- **Severity**: latent
- **Concern**: When `DESIGN_TMPDIR` is set but stale or missing the accepted-design file, resolvers can prefer it over `design-export/oos-accepted-design.md`, making design-export OOS invisible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-evidence-logging-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Python tool-failure logging bypasses canonical helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: Python `_append_execution_tool_failure` hand-writes `execution-issues.md` instead of using `append-tool-failure.sh`, weakening parity with bash logging, stderr capture, and redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-shell-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] NEVER #5 awk extraction is fragile
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structure harness’s NEVER #5 awk block extraction can silently become empty after list renumbering, weakening run-statistics negative checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] Security-marked OOS lacks explicit private routing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The disposition gate excludes security-marked blocks from filing counts, but pre-existing flows may not ensure those blocks are routed through `SECURITY.md` or private disclosure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] New materialize harness lacks agent-lint exclusions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: New `test-materialize-manifest-oos` harness files may need `agent-lint.toml` exclusions consistent with sibling implement harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Duplicated design OOS path resolvers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bash and Python duplicate accepted-design OOS path resolution, increasing the chance that future design-export path changes are applied to one path but not another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] Known degraded OOS paths remain
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: latent
- **Concern**: Known in-plan degraded paths remain, including file-conflict TSV loss on `/issue` Step-5-skip paths and LLM-judged combine pass Rule A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] Title-only idempotency leaves stale text on changed descriptions
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: nit
- **Concern**: Re-materializing an observation with the same title but changed description intentionally leaves stale accepted markdown due to the documented title-idempotency contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-bridge-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] Materialize harness omits edge cases
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: latent
- **Concern**: The materialize harness does not cover multiple empty-title observations, shell-metacharacter descriptions, or Python’s empty-array failed-materialize branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-bridge-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] Bash pre-OOS_PENDING gate also omits strict filed-URL file
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: A pre-existing bash helper path omits `--filed-urls-strict-file`, matching Python’s looser inlined gate rather than the stricter checkpoint helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] Disposition URL count is not per-block
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: `disposition_ok` uses `filed > 0` instead of requiring per-block coverage, which can amplify skip-Step-9a.1 risks when a lone sentinel URL exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

