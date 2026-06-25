### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/decompose.py:445-455
- **Concern**: `design.decompose_panel` migration must preserve per-vendor presence gating inside the archetype loop. Scenario: Live `dispatch_panel` adds a Cursor row only when `cursor_present` and a Codex row only when `codex_present`; one-vendor-down runs are not parallel dual-vendor manifests. The plan pins `parallel_tools=("cursor","codex")` and says to expand rows from that tuple, which can be read as always emitting both tools whenever any external is present.
- **Proposed resolution**: In Codex-only or Cursor-only sessions, manifest rows for the absent vendor get created and `dispatch-waterfall` behavior changes versus today. In `python/decompose.py`, keep the `for arch in DECOMPOSE_ARCHETYPES` loop and gate each tool row on the matching presence flag; treat registry `parallel_tools` as the allowed tool set, not an unconditional pair. Pin one-vendor-down manifest shape in `python/test_decompose.py`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:900-910
- **Concern**: `review.panel` static migration must preserve cursor-always / codex-when-present gating. Scenario: The plan pins asymmetric gating for `design.plan_review_panel` but not for code review. Live `_append_static_specialist_rows` always appends Cursor specialist rows and adds Codex rows only when `codex_slots_available`. Building static rows from flat `slot_defaults("review.panel")` without the same asymmetry changes manifest shape and waterfall fallback when Cursor is down.
- **Proposed resolution**: Registry-driven code-review dispatch can drop always-on Cursor static slots or gate Cursor on `cursor_available`, breaking the current degraded panel contract. Mirror the plan-review rule in `review_pipeline.py`: always emit Cursor static specialist rows; emit Codex static rows only when `codex_available == "true"`. Add a pin in `python/test_review_pipeline.py`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py:2080-2124
- **Concern**: Lint-fix migration must iterate `tool_order("implement.lint_fix_coder")`, not keep a fixed tier if-chain. Scenario: The plan says to replace hardcoded lint-fix order, but live `run_lint_fix` uses a fixed `if claude_present` / `if codex_present` / `if cursor_present` chain and never reads `FIXER_TIER_ORDER`. Swapping only the registry constant leaves runtime order frozen even when `implement.lint_fix_coder` changes.
- **Proposed resolution**: The centralization goal for lint-fix is incomplete: registry edits do not move live dispatch, so collateral default flips remain possible. Refactor `run_lint_fix` to walk `external_defaults.tool_order("implement.lint_fix_coder")` in order with existing availability gates and `main-agent-required` tail behavior. Add a focused behavioral pin in `python/test_checks.py` (firm if feasible).



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_scout.py:570-577
- **Concern**: `SCOUT_PLAN_ARCHETYPES_SCOUT_SH` override must keep forwarding `--role-id` on the inner argv. Scenario: Tests stub the inner scout via `SCOUT_PLAN_ARCHETYPES_SCOUT_SH`. The plan requires `--role-id` on nested `scout dynamic-archetypes`, but it does not state that the override path still appends the full argv tail (including `--role-id`) when `scout_cmd` is replaced.
- **Proposed resolution**: A harness stub that replaces the inner command but not the args list can miss `--role-id` and fail once the CLI enforces it. State explicitly that `scout_plan_archetypes` always appends the same `args` tail (including `--role-id`) after `SCOUT_PLAN_ARCHETYPES_SCOUT_SH`, and update `python/test_plan_scout.py` stubs to accept or require `--role-id`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35
- **Concern**: [SCOPE-REDUCTION] Approach promises broad prompt-prose resync beyond firm file list. Scenario: Approach says to update prompt prose that hardcodes role defaults, but firm `Files to modify/create` only updates `skills/design/references/brainstorm.md` and `docs/external-reviewers.md`. Prior review rejected sweeping `skills/design/SKILL.md` / `plan-review.md` / `voting-protocol.md` edits as unnecessary scope.
- **Proposed resolution**: The plan can pull a large markdown resync into scope without a consumer or CI pin, increasing diff size without advancing the registry goal. Narrow Approach item 35 to the two documented surfaces (brainstorm reference + docs table), or add explicit `MAY_UPDATE` rows for any additional prose files before claiming full prompt sync.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:41-46
- **Concern**: Loaded review prompt surfaces still hardcode the code-review voter matrix. Scenario: The plan updates `python/config.py` and `python/agent_voters.py`, but `skills/review/SKILL.md` and `skills/shared/voting-protocol.md` still describe fixed Cursor/Claude voter composition and launch order. Those files are injected into `/review` and `/implement` contexts, so the new registry would still have a second source of truth unless the prose is rewritten.
- **Proposed resolution**: Add the review skill and voting-protocol surfaces to the prose update, and replace the inline matrix text with registry-backed references or a generated table.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:575-577
- **Concern**: Loaded design prompt surfaces still hardcode the plan-review panel matrix. Scenario: The plan updates `python/config.py` and `python/plan_review_panel.py`, but `skills/design/SKILL.md` and `skills/design/references/plan-review.md` still spell out the static Arch/Innovation/Pragmatic/Requirements panel, the generic Codex row, and the old fallback wording. Step 3 will keep reading that stale matrix unless the design prose is updated too.
- **Proposed resolution**: Add the design skill and plan-review reference surfaces to the prose update, and point them at the registry-backed role table instead of restating the matrix inline.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_panel.py:711-721
- **Concern**: `design.plan_voters` migration omits per-slot availability gating for voter-2/voter-3 manifest rows. Scenario: Live `dispatch_voters` adds voter-2 only when `codex_available=="true"` and voter-3 only when `cursor_available=="true"` before `--no-fallback` waterfall. The plan says to build voter-2/voter-3 rows from `voter_policies("design.plan_voters")` but never pins this asymmetric inclusion. A registry-driven loop that always emits both policy rows can launch the wrong voter set when only one external is present (e.g., cursor-only runs voter-2 Codex with always-on `--no-fallback`).
- **Proposed resolution**: In `plan_review_panel.dispatch_voters`, keep explicit gating: append voter-2 row only when `codex_available=="true"`, voter-3 only when `cursor_available=="true"`; registry supplies tools/outputs only. Add firm `test_plan_review_panel.py` pins for codex-only and cursor-only manifest shapes.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:900-910
- **Concern**: `review.panel` static registry migration omits cursor-always / codex-when-present consumer gating. Scenario: The plan pins asymmetric gating for `design.plan_review_panel` but `review_pipeline.py` uses the same live rule: always append Cursor specialist rows, append Codex specialist rows only when `codex_slots_available`. Registry bullets describe a full cursor+codex matrix that can be read as always emitting six specialist rows. Gating Cursor rows on `cursor_present` changes manifest shape and waterfall fallback behavior.
- **Proposed resolution**: In `review_pipeline.py`, read specialist tool metadata from `slot_defaults("review.panel")` but preserve consumer gating: always emit Cursor specialist manifest rows; emit Codex specialist rows only when `codex_available=="true"`. Add firm `test_review_pipeline.py` pins for codex-absent (3 cursor specialists) vs codex-present (6 specialists) static counts.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:483-511
- **Concern**: Code-review voter dispatch must preserve `external_voter23` manifest shape and omit `--no-fallback`. Scenario: Live `agent_voters.dispatch_voters` includes voter-2 and voter-3 waterfall rows whenever either external is present (`external_voter23`), and `_dispatch_waterfall` never passes `--no-fallback` (unlike plan voters). The plan migrates `review.voters` policies but does not state these dispatch semantics. A shared voter-dispatch helper copied from `plan_review_panel.dispatch_voters` could shrink the manifest to one row or add always-on `--no-fallback`, breaking Codex-primary slots 2/3 waterfall fallback.
- **Proposed resolution**: Preserve `external_voter23` dual-row manifest construction and keep code-review `dispatch-waterfall` without `--no-fallback`. Document in `agent_voters.py` plan bullets; add/extend `test_agent_voters.py` pins for single-external-present manifest still containing both voter-2 and voter-3 rows and for absence of `--no-fallback` in the waterfall argv.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/cli.py:259-263
- **Concern**: Firm scout `--role-id` CLI enforcement still lacks firm test pins (FINDING_3 follow-up). Scenario: The plan makes `--role-id` required on `scout dynamic-archetypes` and `scout plan-archetypes` and requires nested forwarding from `scout_plan_archetypes`, but the only test coverage is `MAY_UPDATE: python/test_plan_scout.py`. An implementer can skip MAY_UPDATE updates and ship a CLI/schema change without CI failing on missing argv or nested subprocess forwarding.
- **Proposed resolution**: Promote scout CLI/`role_id` plumbing pins from `MAY_UPDATE` to firm `UPDATED: python/test_plan_scout.py` (required `--role-id`, review vs design role IDs, nested `scout plan-archetypes` argv includes `--role-id design.plan_archetype_scout`).



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:228-234
- **Concern**: Missing consumer test for the new aggregator role split. Scenario: Registry tests alone will not catch a hardcoded cursor slot, so plan review aggregation can still use the wrong tool for --input-mode plan while CI stays green.
- **Proposed resolution**: Add a focused test in python/test_review_aggregate.py or python/test_plan_review_round.py that inspects the generated slots file or dispatch argv for both --input-mode code and --input-mode plan.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:900-910
- **Concern**: Code-review `review.panel` static migration omits pinned cursor-always / codex-when-present row gating. Scenario: Live `_append_static_specialist_rows` always appends Cursor specialist rows and ignores `cursor_available`; Codex rows append only when `codex_present == "true"`. The plan pins this asymmetry for `design.plan_review_panel` but only says `review.panel` rows are "cursor + codex per archetype" with generic availability gates. Building manifest rows symmetrically from registry `slot_defaults` can drop Cursor static rows when Cursor is absent and change waterfall fallback/manifest shape.
- **Proposed resolution**: In `review_pipeline.py` and `python/test_review_pipeline.py`, mirror the plan-review contract: always emit Cursor static specialist rows from registry metadata; gate Codex static rows on `codex_present == "true"` only; add a test that Cursor rows remain when `cursor_available=false` and Codex rows are omitted when `codex_available=false`.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:3-29
- **Concern**: Loaded prompt references still hardcode the old plan-review/voter matrices. Scenario: The plan updates the runtime code and one docs table, but the `/design` Step 3 reference still spells out a fixed panel matrix, `--no-fallback` behavior, and the current voter matrix. The same stale source-of-truth pattern remains in `skills/review/SKILL.md`, `skills/implement/SKILL.md`, and `skills/shared/voting-protocol.md`. That leaves the old defaults visible to the models after the registry lands, so later role-default changes can still drift silently.
- **Proposed resolution**: Add the loaded prompt/reference files that restate fixed slot orders to UPDATED, and replace the hardcoded tables with registry-backed references or CLI lookups.



