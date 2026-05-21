Here is the normalized finding list. N/A confirmations (original FINDING_3–5) are omitted as non-actionable. Original FINDING_2 and FINDING_8 are merged; original FINDING_10 and FINDING_11 are merged. IDs follow first appearance of each cluster in the supplied input.

```text
### FINDING_1: [OUT_OF_SCOPE] ship-pr.md Exit 5 CALLER_KIND documentation gap
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Operators relying on [scripts/ship-pr.md](scripts/ship-pr.md) may see Exit 5 documentation that mentions `step8b_rebase` but not `step8_apply_bump_same_version`, so they may miss the second Exit 5 `CALLER_KIND` token after runtime alignment.
- **Suggested revision**: Add a concise bullet beside the existing Exit 5 description that documents both Exit 5 caller-kind values (`step8b_rebase` vs `step8_apply_bump_same_version`).

### FINDING_2: Cross-version resume and legacy `CALLER_KIND` passthrough vs canonical contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Exact `CALLER_KIND` passthrough from `ship-pr` state can preserve a legacy token (e.g. `step8b_same_version`) after upgrading mid-run or when resuming from an older `ship-pr.sh`, while the sub-procedure / Step text emphasizes `step8_apply_bump_same_version`. That mismatch can confuse operators, invite unnecessary token rewriting, or leave ambiguous orchestrator handling if cross-version resume is a real scenario (otherwise fresh tmpdirs may suffice).
- **Suggested revision**: Prefer one minimal direction: document cross-version resume behavior explicitly, or add a one-line legacy-alias note under Exit 5 (or equivalent) so exact passthrough from old state stays unambiguous; only add a short-lived alias in the sub-procedure if cross-version resume must keep working mechanically.

### FINDING_3: [OUT_OF_SCOPE] Garbled pasted plan bullet
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A pasted implementation-plan bullet does not describe an actual token change; it is noise for diff judgment.
- **Suggested revision**: Ignore for code review; rely on `feature_description` and the code.

### FINDING_4: [OUT_OF_SCOPE] Run log plan narrative uses legacy token name
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A committed run-log plan file still uses the legacy token in narrative; it is not runtime behavior.
- **Suggested revision**: None required; optional editorial cleanup only if desired.

### FINDING_5: [OUT_OF_SCOPE] Feature / issue narrative may under-describe branch surface
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Narrow `feature_description` text may not mention ship-pr, harness, or run-log edits present on the branch, so PR/issue narrative keyed only to a short feature tag may under-describe delivered surface.
- **Suggested revision**: Reconcile issue/PR description with the full diff when publishing; not a functional code defect.

### FINDING_6: User implementation plan contradicts shipped diff and has a defective Occurrences row
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The plan asserts SKILL-only scope and no script changes while the diff edits `scripts/ship-pr.sh` and ship-pr test files, which breaks traceability for consumers comparing plan to diff. Separately, an Occurrences item is self-contradictory (identical before/after) and omits the explicit canonical token on the “after” side, blocking mechanical reconciliation against `SKILL.md`.
- **Suggested revision**: Update the planning source of truth so “Files to modify” and “Approach” match shipped files (or explicitly cite the flushed plan artifact if that is authoritative). Correct the Occurrences line to show an explicit rename from `step8b_same_version` to `step8_apply_bump_same_version` (or equivalent unambiguous before/after).
```
