## Decision 1: Scope of fixes to apply
- **Question**: Which of the 4 proposed fixes should be implemented?
- **Resolution**: All four — Fix 1 (anti-halt enumeration), Fix 2 (Step 5c banner), Fix 3 (test pin), Fix 4 (orchestrator-never.md NEVER entry).
- **Source**: user

## Decision 2: Scope of the new NEVER rule in orchestrator-never.md
- **Question**: Should the banner/anti-pattern be Step-5b-specific only, or a generic sub-skill terminal-output rule?
- **Resolution**: Both — Step-5b-specific `Continue to Step 5c IMMEDIATELY` banner stays surgical, AND a generic NEVER entry is added to `skills/shared/orchestrator-never.md` so the rule applies to all Skill-tool sub-skill calls across larch skills.
- **Source**: user

## Decision 3: Must Step 5 mechanics change?
- **Question**: Do we modify the actual order/behavior of Step 5 (OOS filing, plan compose, plan-block-write, publish, rename)?
- **Resolution**: No — per the issue's own Acceptance: "No change to actual Step 5 mechanics (the order of OOS filing, plan composition, plan-block-write, publish, and rename remains the same — only the continuation discipline is tightened)."
- **Source**: codebase (issue body Acceptance bullet)
