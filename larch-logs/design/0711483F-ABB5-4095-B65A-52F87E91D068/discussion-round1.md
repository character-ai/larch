## Decision 1: Validator-extension parity depth
- **Question**: How much of the #6746 guideline completeness surface should the invariant extension mirror?
- **Resolution**: Full parity. Mirror an invariant analog at every enforcement point #6746 added for guidelines: the publish-time refusal in `design_publish.py` (+ `design_step5c.py` KV plumbing and refuse-reason), the run-log required-artifact in `run_log_manifest.py` (`verify_completeness`), the log-publish flow check in `design_log_publish_flow.py`, and the missing-assessment warning in `design_summary.py`. Publish-only enforcement would not solve the issue's stated "Measured effect" (0 of 29 runs committed the invariant artifact), which is about the committed-run-log audit trail.
- **Source**: codebase (issue #6747 items 1-4 + companion PR #6746 file surface)

## Decision 2: Present-but-empty invariants file
- **Question**: Does a present `ARCHITECTURAL_INVARIANTS.md` with no parsed `I-*` entries require the assessment artifact?
- **Resolution**: No. Require the artifact only when `read_invariants().status == "present"` AND `content.strip()` is non-empty, matching `invariants_persist_design_assessment_main`'s `requires_assessment` guard and the acceptance criterion "empty invariants file passes with no artifact." This differs from the guideline completeness check, which keys on `status` alone.
- **Source**: codebase (`architectural_guidelines.py` persist verb; issue acceptance criteria)

## Decision 3: Do not modify the existing guideline enforcement path
- **Question**: Should the guideline completeness check be refactored/shared with the new invariant check?
- **Resolution**: No. Add a parallel invariant analog and leave the guideline path untouched (surgical change). Any pre-existing guideline/invariant inconsistency (e.g., the guideline check keying on status without the non-emptiness guard) is out of scope for #6747; note it, do not fix it.
- **Source**: codebase (surgical-change principle)

## Decision 4: Persist ordering in Gate C
- **Question**: In what order should the invariant vs guideline persist run?
- **Resolution**: Invariant persist before guideline persist, matching the existing `present-note` order (`approval-gates.md`).
- **Source**: issue #6747 item 1
