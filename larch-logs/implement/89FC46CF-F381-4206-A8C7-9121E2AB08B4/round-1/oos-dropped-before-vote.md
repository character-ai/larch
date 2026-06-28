### OOS_1: [OUT_OF_SCOPE] `design-step5c.md` invariant still describes marker-body emission
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Wrapper contract at `skills/design/scripts/design-step5c.md:22` still documents marker-body streaming though Python now emits empty readiness markers only. `skills/design/SKILL.md` cites this file as the Step 5c contract, so maintainers debugging handoff may look at the wrong surface, debug marker truncation, or reintroduce marker-body extraction in orchestrator prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update invariant line 22 to path plus empty readiness markers; note orchestrator must Read FINAL_SUMMARY_PATH.
  - From cursor-specialist-testing: Update that invariant to path KV + empty readiness markers (not in the approved plan file list).

### OOS_2: [OUT_OF_SCOPE] Companion harness doc drifts from updated `.sh` pins
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-summary-contract
- **Severity**: nit
- **Concern**: `scripts/test-render-cost-line-callsites.md:17-18` still describes the `/design` marker-first row cite while the `.sh` harness was retargeted to Read-always wording in this branch. CI does not run the `.md`, so this is doc drift that can mislead future harness edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Align the companion doc with Read-always wording when touching that harness next.

### OOS_3: [OUT_OF_SCOPE] Anti-halt “verbatim emit” phrasing easy to misread
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-summary-contract
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:29` anti-halt prose still says “shared verbatim final-summary emit” (or similar) while also pointing at the Read-always profile. Step 5c/5d wording is clearer; leftover phrasing increases the chance an orchestrator tries marker-body extraction on empty markers. Low risk because the profile reference is explicit on the same line.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a concrete fix direction beyond the concern; omitted per aggregator rules.)

### OOS_4: [OUT_OF_SCOPE] File-only cancel profile is a second emission contract
- **Reviewer(s)**: dyn-dyn-summary-contract
- **Severity**: nit
- **Concern**: The file-only profile in `skills/shared/final-summary-emit.md:60-66` (Step 0b cancel routes) still Read-falls back to `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` without parsing stdout. That is intentional for routes with no task notification, but it is a second emission contract alongside Read-always and worth keeping documented as operators touch cancel paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a concrete fix direction beyond the concern; omitted per aggregator rules.)

---

**Merge notes (diagnostic, not part of validator output):**
- Testing findings 7–10, 12–13 were positive coverage observations with no distinct fix ask; subsumed into FINDING_1 context or treated as non-actionable attestations.
- FINDING_14 (identical duplicate rows on production paths) folded into FINDING_1 concern as mitigating context; testing slot retained on FINDING_1 and FINDING_3.
- In-scope `design-step5c.md` correctness (dyn FINDING_18 + testing FINDING_11) merged as FINDING_3; OOS variants (correctness FINDING_3, testing FINDING_15) merged as FINDING_4.
- All four inventory slots appear in at least one `- **Reviewer(s)**:` line; exclusively-OOS reviewer citations appear only in `[OUT_OF_SCOPE]` blocks.

