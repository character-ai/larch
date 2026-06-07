### FINDING_10: Auto-continue can exceed the review cap and clear artifacts
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The continuation branch does not check the unified round cap before invoking Step 3 again, so a cap-edge round can enter cap-reached mode and clear current review artifacts before Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Heuristic counts can be stale, unset, or inconsistent with effective severity
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-state-flow-output.txt
- **Severity**: important
- **Concern**: The heuristic relies on in-memory or structured `IMPORTANT_ACCEPTED_COUNT` values that may be stale after re-tally/resume or miss Gate B “High” fallback severity, causing substantial rounds to stop incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-state-flow-output.txt: Address the concern above.


### FINDING_12: Approval-gates contract still routes post-apply directly to Step 3b/Gate C
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` remains a normative single-path Gate B contract and does not document the heuristic continuation branch, cap sharing, sentinel hygiene, or Gate C deferral.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt: Address the concern above.


### FINDING_18: Stale per-tier cap wording remains
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: Some Gate C and approval-gates prose still refers to tier-specific caps even though the intended cap is flattened to 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_3: Missing optional OOS artifact can zero plan-review counts
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` may feed a missing `oos-accepted-design.md` path to awk, causing failure and a fallback to `0 findings` even when in-scope accepted findings exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_5: Continuation predicate is narrower than planned `/implement` parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The design loop continues only on `IMPORTANT_ACCEPTED_COUNT >= 2`, omitting non-nit accepted-count, degraded-panel, structural/large-change, and small-clean convergence predicates required to mirror `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.


### FINDING_7: Final summary underreports accepted findings across automatic rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-awk-output.txt
- **Severity**: important
- **Concern**: `accepted-plan-findings.md` is overwritten per Step 3 round while OOS accumulates, so the final Plan review line can report only the final round’s in-scope findings instead of all accepted/applied review work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-awk-output.txt: Address the concern above.


### FINDING_9: `--approve` interaction with automatic continuation is ambiguous
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The heuristic can run after explicit `--approve` Gate B handling, causing repeated prompts or silent automatic reruns despite operator expectations for manual review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt: Address the concern above.


