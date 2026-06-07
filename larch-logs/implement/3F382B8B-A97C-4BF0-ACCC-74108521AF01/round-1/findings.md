### FINDING_1: [OUT_OF_SCOPE] Security OOS blocks may not route as security
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `is_security_block` does not recognize the emitted `Focus area` field spelling, so accepted security OOS blocks may be published instead of held locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] One Important security finding does not force another review
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The continuation heuristic stops below two Important findings, so a single accepted security finding can proceed without a mandatory second review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Missing optional OOS artifact can zero plan-review counts
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` may feed a missing `oos-accepted-design.md` path to awk, causing failure and a fallback to `0 findings` even when in-scope accepted findings exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Automatic re-entry leaves stale sentinels and pause/resume state
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The automatic continuation path does not use the same Step 3 re-entry/state cleanup as manual reruns, leaving `.completed/step-3`, Gate B post-apply markers, and pause/resume fingerprints that can skip the intended follow-up review or reuse stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt: Address the concern above.

### FINDING_5: Continuation predicate is narrower than planned `/implement` parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The design loop continues only on `IMPORTANT_ACCEPTED_COUNT >= 2`, omitting non-nit accepted-count, degraded-panel, structural/large-change, and small-clean convergence predicates required to mirror `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Multi-round loop is prompt-only and insufficiently pinned
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The new continuation behavior lacks script-level enforcement and structural/integration harness pins, so future edits can drop or break the loop while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.

### FINDING_7: Final summary underreports accepted findings across automatic rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-awk-output.txt
- **Severity**: important
- **Concern**: `accepted-plan-findings.md` is overwritten per Step 3 round while OOS accumulates, so the final Plan review line can report only the final round’s in-scope findings instead of all accepted/applied review work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-awk-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Single-pass documentation remains stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `SKILL.md`, `plan-review.md`, `flags.md`, `plan-review-loop.md`, and approval-gate invariants still describe Step 3 as single-pass, conflicting with the new outer heuristic loop and misleading operators/contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.

### FINDING_9: `--approve` interaction with automatic continuation is ambiguous
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The heuristic can run after explicit `--approve` Gate B handling, causing repeated prompts or silent automatic reruns despite operator expectations for manual review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt: Address the concern above.

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

### FINDING_13: Missing-Focus-area summary fallback lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-awk-output.txt
- **Severity**: nit
- **Concern**: Tests do not cover accepted finding blocks that omit `- **Focus area**:`, so regressions in fallback counting/bucketing could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-shell-awk-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Bash 3.2 summary fixture still uses legacy grammar
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Bash 3.2 fixture still uses the legacy `focus-area =` format and does not assert the Plan review line, leaving a platform-specific counting gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Automatic continuation deletes prior round forensic directories
- **Reviewer(s)**: dyn-state-flow-output.txt
- **Severity**: latent
- **Concern**: `run-step3-review.sh` removes `plan-review/round-*` directories on each re-entry, so automatic multi-round runs can lose earlier-round audit artifacts before Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-flow-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Summary header regex is misaligned with canonical finding grammar
- **Reviewer(s)**: dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: The awk block matcher is looser than canonical `FINDING_[0-9]+:` / `OOS_[0-9]+:` grammar and may mishandle malformed or multi-digit headers, causing summary totals to diverge from other tallies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Legacy focus-area regex removal is not pinned
- **Reviewer(s)**: dyn-shell-awk-output.txt
- **Severity**: nit
- **Concern**: The updated summary harness proves the new bold `Focus area` format works but no longer proves the old `focus-area =` grammar stays dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-awk-output.txt: Address the concern above.

### FINDING_18: Stale per-tier cap wording remains
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: Some Gate C and approval-gates prose still refers to tier-specific caps even though the intended cap is flattened to 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Positive Part B observation
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: Part B’s core direction—counting finding/OOS headers and parsing bold `Focus area` fields—was called out as sound with useful regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Plan review line still depends on `voting-tally.md`
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` still gates the Plan review line on `voting-tally.md` existence, so accepted findings can render as `0 findings` if the tally file is absent on failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.
