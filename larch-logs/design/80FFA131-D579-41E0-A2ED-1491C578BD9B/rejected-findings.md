### [Plan Review] FINDING_3

### FINDING_3: Lint-fix migration must walk `tool_order("implement.lint_fix_coder")`, not keep a fixed tier if-chain
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Lint-fix migration must iterate `tool_order("implement.lint_fix_coder")`, not keep a fixed tier if-chain. Live `run_lint_fix` uses a fixed `if claude_present` / `if codex_present` / `if cursor_present` chain and never reads `FIXER_TIER_ORDER`. Swapping only the registry constant leaves runtime order frozen even when `implement.lint_fix_coder` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: The centralization goal for lint-fix is incomplete: registry edits do not move live dispatch, so collateral default flips remain possible. Refactor `run_lint_fix` to walk `external_defaults.tool_order("implement.lint_fix_coder")` in order with existing availability gates and `main-agent-required` tail behavior. Add a focused behavioral pin in `python/test_checks.py` (firm if feasible).


### [Plan Review] FINDING_5

### FINDING_5: Loaded prompt/reference surfaces still hardcode old role matrices
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Loaded `/review` and `/design` prompt surfaces still hardcode fixed panel and voter matrices. The plan updates `python/config.py` and runtime dispatch modules, but skill and reference prose (`skills/review/SKILL.md`, `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, `skills/implement/SKILL.md`, `skills/shared/voting-protocol.md`) still restate the old slot orders, fallback wording, and voter composition. Those files are injected into orchestrator context, so the registry would have a second source of truth and later role-default changes can drift silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the review skill and voting-protocol surfaces to the prose update, and replace the inline matrix text with registry-backed references or a generated table.
  - From Codex-Innovation: Add the design skill and plan-review reference surfaces to the prose update, and point them at the registry-backed role table instead of restating the matrix inline.
  - From Codex-Requirements: Add the loaded prompt/reference files that restate fixed slot orders to UPDATED, and replace the hardcoded tables with registry-backed references or CLI lookups.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35
- **Concern**: [SCOPE-REDUCTION] Approach promises broad prompt-prose resync beyond firm file list. Scenario: Approach says to update prompt prose that hardcodes role defaults, but firm `Files to modify/create` only updates `skills/design/references/brainstorm.md` and `docs/external-reviewers.md`. Prior review rejected sweeping `skills/design/SKILL.md` / `plan-review.md` / `voting-protocol.md` edits as unnecessary scope.
- **Proposed resolution**: The plan can pull a large markdown resync into scope without a consumer or CI pin, increasing diff size without advancing the registry goal. Narrow Approach item 35 to the two documented surfaces (brainstorm reference + docs table), or add explicit `MAY_UPDATE` rows for any additional prose files before claiming full prompt sync.


