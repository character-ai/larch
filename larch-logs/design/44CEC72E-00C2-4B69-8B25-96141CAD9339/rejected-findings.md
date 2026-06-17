### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:93-130
- **Concern**: [SCOPE-REDUCTION] Step 3b-tail ownership is split across wrapper shrink and native verb without a single commit owner. Scenario: The plan tells the wrapper to shrink around `plan-review step3b-tail` while also saying Step 4 tail work may stay wrapper-owned "unless fully ported." Today the live script performs FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC=`, and `.completed/step-4` inline before Gate C preview. A thin wrapper that only delegates preview drops those side effects and breaks Gate C.
- **Proposed resolution**: Pick one owner for this slice: either `plan-review step3b-tail` implements every tail side effect listed in the plan before the wrapper delegates, or keep the current bash body in the wrapper and defer wrapper shrink until that verb exists. Do not land a preview-only wrapper.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:93-130
- **Concern**: [SCOPE-REDUCTION] Step 4 tail authority is split between wrapper and `plan-review step3b-tail`. Scenario: Plan says shrink `design-step3b-tail.sh` to delegate to `plan-review step3b-tail` but also allows retaining FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC`, and `.completed/step-4` in the wrapper unless fully ported. An implementer can delegate to a preview-only native verb and drop Gate C prerequisites.
- **Proposed resolution**: Gate C can run without FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC`, or `.completed/step-4`. Pin one authority: `plan-review step3b-tail` must implement all current tail side effects before merge; `design-step3b-tail.sh` only sources env, pause-checks, and delegates. Remove the unless fully ported escape hatch.

