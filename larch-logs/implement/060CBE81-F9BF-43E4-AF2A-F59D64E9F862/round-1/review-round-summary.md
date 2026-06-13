# Review Round 1

- Mode: `diff`
- 4 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Gate C full-plan docs contradict `--variant full` helper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still tells the executor to print `**⚠ plan.txt missing or empty; nothing to show.**` on the structured `See full plan` / `Other` path when `plan.txt` is missing, while `SKILL.md` and `emit-design-plan-preview.sh --variant full` use a different `4b:` warning contract. An operator following the normative gate doc can emit the wrong message or skip the helper path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align `approval-gates.md` with helper-only full-plan display; remove legacy nothing-to-show text or make helper warnings byte-identical.


### FINDING_2: Gate C Presentation still mandates re-running tail wrapper at Step 4b
- **Reviewer(s)**: dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` Presentation still says to run the `SKILL.md` tail-wrapper fence immediately before the Gate C prompt, but `SKILL.md` now runs `design-step3b-tail.sh` at Step 4 and Step 4b only consumes `SKIP_APPROVE_REQUESTED_GATEC=` from that output. An orchestrator treating `approval-gates.md` as normative at Step 4b can invoke the tail wrapper twice, duplicating the Gate C preview, re-reading skip-approve, and rewriting `.completed/step-4`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt: Update the Presentation block to state that Step 4's `design-step3b-tail.sh` fence already emitted the Gate C preview and skip-approve KV; Step 4b must consume that output and must not re-run the tail wrapper on the normal path (only on an explicit Step 4 resume/repair boundary).


### FINDING_3: No behavioral tests for `--variant full` plan preview
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: The plan adds `--variant full` for Gate C "See full plan" / `Other`, but `test-emit-design-plan-preview.sh` has no behavioral cases for it; only structural string pins exist. A regression could restore summary/truncated output while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add harness cases for full variant: header present full body for large plan no summary note.
  - From cursor-specialist-testing-output.txt: Add large-plan full-variant test asserting body lines past summary window, no summary markers; add friendly warning cases for empty/disallowed tmpdir.
  - From dyn-design-flow-output.txt: Add harness cases for `full` on small and over-threshold plans (assert full body present, assert no `**Section outline:**` / large-plan note), mirroring existing `step3`/`gatec` coverage.


### FINDING_8: Sanitizer success inferred via substring grep on captured output
- **Reviewer(s)**: dyn-shell-contracts-output.txt
- **Severity**: important
- **Concern**: Success requires `_sanitizer_rc -eq 0` plus absence of the literal substring `STATUS=rejected` anywhere in captured output. Incidental `STATUS=rejected` text in a warning, path, or quoted example can route to the rejection path, delete the candidate, and skip promotion even when the CLI exited 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-contracts-output.txt: Parse a structured status line (for example `^STATUS=rejected` or the CLI's documented KV grammar) instead of `grep -Fq 'STATUS=rejected'` over the full capture.


