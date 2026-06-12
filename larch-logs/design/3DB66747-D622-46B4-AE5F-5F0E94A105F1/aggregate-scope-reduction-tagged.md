### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/parse-drafter-output.py:1-49
- **Concern**: [SCOPE-REDUCTION] The plan adds tolerant decontamination for duplicate, reversed, nested, pre-plan, in-summary, and in-plan scout sentinels instead of only extracting one valid post-plan scout block.. Scenario: A drafter that accidentally wraps real plan lines in misplaced scout sentinels could have those lines removed while still producing a diff_lines-valid plan. The extra parser and test matrix is not required to run scout once.
- **Proposed resolution**: Keep parse-drafter-output.py to the minimum contract: extract zero or one LARCH_SCOUT block only after LARCH_PLAN_END, ignore malformed scout after the plan, and reject any scout sentinel found inside the plan or summary instead of sanitizing spans.

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/parse-drafter-output.py:27-48
- **Concern**: [SCOPE-REDUCTION] Plan adds scout-sentinel decontamination and scout-shaped JSON scrubbing inside the plan parser. Scenario: Minimum-change feature only needs an optional scout block after LARCH_PLAN_END; accepting and rewriting malformed plan envelopes creates a new parser recovery path and can hide drafter format bugs while changing the extracted plan body
- **Proposed resolution**: Keep plan parsing strict; parse at most one optional LARCH_SCOUT block only after LARCH_PLAN_END; if scout markers or scout JSON appear before or inside the plan or summary block, ignore the scout candidate or fail the drafter output under the existing strict plan rules rather than sanitizing plan.txt

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/parse-drafter-output.py:37-49; plan lines 68-73
- **Concern**: [SCOPE-REDUCTION] Proposed scout decontamination rewrites plan bodies and rejects legitimate scout JSON examples. Scenario: A valid plan can include a code fence showing {"archetypes":[]} or an accidental in-plan scout sentinel span; the proposed parser can reject that valid plan or delete real plan lines while still emitting plan.txt with diff_lines
- **Proposed resolution**: Accept scout only from one balanced block after LARCH_PLAN_END; remove in-plan scout span removal and scout-shaped JSON scanning; treat whole-line scout sentinels inside the plan as delimiter errors instead of repairing the plan

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/parse-drafter-output.py (plan.txt:68-73)
- **Concern**: [SCOPE-REDUCTION] Parser decontamination silently rewrites malformed plan envelopes. Scenario: The feature only needs an optional scout block after LARCH_PLAN_END; accepting scout sentinels inside LARCH_PLAN_BEGIN/END by deleting spans weakens the existing strict plan extraction contract and can silently drop plan-body content from the artifact under review.
- **Proposed resolution**: Remove in-plan scout-span sanitization; require scout sentinels only after LARCH_PLAN_END, and treat any scout sentinel or scout-shaped JSON inside the plan envelope as a fatal drafter parse error while leaving out-of-plan malformed scout output fail-open.
