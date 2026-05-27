### FINDING_1: Step 18 marks final summary emitted before orchestrator emit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 18 Bash touches `.step17-emitted` before the orchestrator performs the verbatim top-chat emit. This can make the orchestrator treat the summary as already emitted and skip the visible full-body summary, recreating invisible final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Step 18 emit intent is not reliably visible to orchestrator
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 18 computes `_wfr_emit_body` inside Bash, but the orchestrator does not have a separate reliable signal for whether it must emit a refreshed body after token refresh or body changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Test pins premature Bash mutation of `.step17-emitted`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` currently allows or pins the Bash-side `.step17-emitted` touch instead of enforcing that only orchestrator prose writes the sentinel after a successful verbatim emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Changelog bundles #2970 with unrelated 42.6.1 work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The #2970 summary-visibility fix is grouped with unrelated parser and telemetry changes, making review and revert boundaries unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Design summary prose misstates the visibility contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still says `render-final-summary.sh` prints the summary to chat, which can lead an agent to treat collapsed Bash output as sufficient and skip the required orchestrator verbatim emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: #2970 changelog entry is under Changed instead of Fixed
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The #2970 entry is described as a fix but is categorized under `### Changed`, weakening the semver signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: No test verifies orchestrator verbatim top-chat emission
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Existing checks rely on prose greps and do not verify that the orchestrator actually emits the full final-summary body verbatim to top chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Step 18 structure test does not require emitted-sentinel guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh` does not require the `.step17-emitted` guard around `--print-stdout`, so future edits could make summary printing unconditional without failing lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Design test does not pin non-empty final-summary gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The design post-publish callsite could regress from checking `[ -s "$DESIGN_TMPDIR/final-summary.md" ]` to weaker cost-line-only gating without failing `test-render-cost-line-callsites`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Step 18 body-diff test checks only Cost substring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-write-final-report.sh` could pass even if the refreshed summary loses required structure, because the changed-body path asserts only a `Cost` substring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Design has no emission sentinel
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Design summary visibility depends only on prose. If the orchestrator halts after `render-final-summary.sh`, the file may exist on disk and in a GitHub comment while the operator never sees the top-chat block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Design Step 5c traceability relies on shared-rule indirection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 5c item 10 does not include the plan’s exact verbatim-emit literal, making plan-to-code drift harder to catch with existing pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] #2970 changelog section hygiene
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: #2970 appears under `[42.6.1] Changed` despite fix wording. The reviewer marked this as pre-existing changelog section hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Same-user tmpdir content can influence top-chat output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Verbatim reads of `$DESIGN_TMPDIR/final-summary.md` and `$IMPLEMENT_TMPDIR/summary-final.md` rely on the existing same-user session-artifact trust model. A same-UID writer could swap or craft a file before orchestrator read, and full-body emit exposes more bytes, though the trust boundary is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Final summary is not redacted before orchestrator emit
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `summary-final.md` is not redacted in place before orchestrator emit. This is pre-existing and only matters if summaries embed tool stderr excerpts or other sensitive content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Argv validation hardening observation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` argv validation hardening for `--issue` and `--repo` is unrelated to summary visibility and was identified as a positive drive-by observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
