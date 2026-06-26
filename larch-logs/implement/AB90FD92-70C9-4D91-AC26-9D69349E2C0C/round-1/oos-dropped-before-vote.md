### OOS_1: [OUT_OF_SCOPE] Verdict gate stderr `ERROR=` contract only partially tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The stderr `ERROR=` contract is only partially tested for verdict gate failures. Targeted-fetch and incentive-gate paths assert stdout `gate_reason` but not stderr `ERROR=`, so automation keyed on stderr can drift from the rendered report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert ERROR=ground_truth_verdict_failed reason=<gate_reason> in targeted-fetch and incentive-gate verdict tests.

### OOS_2: [OUT_OF_SCOPE] Evidence Summary wording mismatches incentive-gate `gate_reason`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-verdict-docs-output.txt
- **Severity**: nit
- **Concern**: `docs/ground-truth-verdict.md:48-50` Evidence Summary opens with “because GitHub issue enrichment failed,” but the recorded `gate_reason` is `calibration_incentive_check_unavailable`, which `_ground_truth_apply_gate` evaluates before enrichment/corpus gates. The Corpus Gate Result block quotes the correct `gate_reason`, so this is a narrative mismatch, not a CLI bug; human readers can misread which precondition blocked GO.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword the lead sentence to cite `calibration_incentive_check_unavailable` as the mechanical blocker and treat `bulk_fetch_failed` / `targeted_fetch_degraded` as parallel degraded-evidence context.
  - From cursor-specialist-testing-output.txt: Reword Evidence Summary to match incentive-gate priority and recorded gate_reason.

### OOS_3: [OUT_OF_SCOPE] Verdict mode undercounts gc-slimmed-only directories
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Verdict mode does not run `_ground_truth_gc_slimmed_fallback` (`python/analyze_issues.py:3005-3010`), so `gc-slimmed` directories with no classifier TSV never increment `excluded_gc_slimmed_runs` (diagnostic mode still counts them). `excluded_gc_slimmed_runs` undercounts slimmed-only directories in the verdict corpus block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: If the verdict corpus block must report that bucket completely, add a verdict-only slimmed-dir scan or document that the counter covers slimmed runs discovered via classifier paths only.
  - From cursor-specialist-testing-output.txt: Optionally mirror diagnostic fallback counting or document the limitation explicitly.

### OOS_4: [OUT_OF_SCOPE] README `/analyze-issues` row omits default diagnostic report
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `/analyze-issues` feature-matrix blurb in `README.md:134-135` (and related rows) now emphasizes verdict mode and no longer mentions that default mode still prints the full backlog/diagnostic report. Operators may think the skill always runs verdict mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Split into two sentences: default diagnostic output first, then verdict-mode behavior and gates.
  - From cursor-specialist-testing-output.txt: Restore a short clause that default mode still prints the full diagnostic report.

