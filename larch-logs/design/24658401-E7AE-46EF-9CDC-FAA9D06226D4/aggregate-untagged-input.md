### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/brainstorm.md:25-30
- **Concern**: `brainstorm.md` Entry guard still re-implements skip/run after the fold moves ownership to `step1d5 --mode entry`. Scenario: The plan updates `skills/design/SKILL.md` to gate on `STEP1D5_ACTION`, but `brainstorm.md` is not in Files to modify/create. On `STEP1D5_ACTION=run`, SKILL still loads `brainstorm.md`, whose Entry guard re-reads `run-params.json` and can direct skip to Step 1d.7 with different precedence than the wrapper (`.brainstorm-done` is checked after `brainstorm_requested`, not first). That revives a second control point the fold is meant to remove.
- **Proposed resolution**: Add `### UPDATED: skills/design/references/brainstorm.md`: replace the Entry guard with a short note that skip/run was decided by `STEP1D5_ACTION` in the entry fence; on the run path start at the brainstorm banner / prompts read without re-reading `run-params.json` or re-skipping.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:2829-2836
- **Concern**: Step 1d.5 entry must use the same strict `brainstorm_requested` predicate as `step2a_main`. Scenario: The plan says `brainstorm_requested is not true` in prose but does not pin the Python check to `data.get("brainstorm_requested") is True` (as `step2a_main` already does). A loose truthiness read can disagree with Step 2a repair and emit `STEP1D5_ACTION=run` when Step 2a still treats brainstorm as off.
- **Proposed resolution**: In the `step1d5_main --mode entry` implementation bullet, require `brainstorm_requested = (json.loads(...) or {}).get("brainstorm_requested") is True` and branch skip only when that is false; mirror the missing-file default (`False`) explicitly.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/brainstorm.md:25-30
- **Concern**: brainstorm.md Entry guard still re-decides skip/run after wrapper fold. Scenario: The plan moves skip/run ownership to step1d5 --mode entry and STEP1D5_ACTION, but on STEP1D5_ACTION=run it still mandates loading brainstorm.md, whose Entry guard re-reads run-params.json and can skip to Step 1d.7 independently (checking brainstorm_requested before .brainstorm-done, unlike wrapper precedence). That revives dual control and can skip the brainstorm body after the wrapper emitted run, or pick the wrong skip breadcrumb on resume/re-run.
- **Proposed resolution**: Add ### UPDATED: skills/design/references/brainstorm.md: replace Entry guard steps 1-3 with wrapper-trust prose (only load on STEP1D5_ACTION=run; no independent skip/run; print the Step 1d.5 banner and continue to prompts). Update the Consumer line to reference STEP1D5_ACTION instead of direct run-params reads.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:2824-2865
- **Concern**: Step 1d.5 entry read must use step2a strict is True predicate. Scenario: The plan says brainstorm_requested is not true but does not pin the JSON predicate step2a_main uses (data.get("brainstorm_requested") is True). A loose truthiness check can disagree with Step 2a repair and the wrapper skip/run decision on edge-case run-params values.
- **Proposed resolution**: In the step1d5 --mode entry fold, load run-params with the same strict contract as step2a_main: missing or malformed JSON defaults false; enabled only when value is True; disabled when is not True; .brainstorm-done checked before brainstorm_requested.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/brainstorm.md:25-30
- **Concern**: Brainstorm panel entry guard still keys on `run-params.json` and `.brainstorm-done`. Scenario: `skills/design/SKILL.md` is being changed to hand Step 1d.5 selection to the wrapper-emitted `STEP1D5_ACTION`, but the loaded `brainstorm.md` body still re-reads `run-params.json` and decides skip/run for itself. That reintroduces a second source of truth on the run path, so the wrapper can say “run” while the loaded panel file silently skips or replays the step. Add `### UPDATED: skills/design/references/brainstorm.md`, rewrite the entry guard to trust the wrapper contract, and pin the new behavior in `scripts/test-design-structure.sh`.
- **Proposed resolution**:
