### FINDING_1: Dynamic specialist pre-render omits difficulty
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Cache Contract, Codex-dyn-Prompt Cache Contract
- **Severity**: major
- **Concern**: The dynamic specialist pre-render path calls `render specialist` without threading the normalized tier/difficulty, so TRIVIAL dynamic prompt files keep the full guidelines block instead of slimming.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `--difficulty` with the normalized `tier` to the `render_args` list in `_synthesize_dynamic_slots` (and extend `test_review_pipeline.py` render-call assertions)
  - From Cursor-Innovation: Add --difficulty tier to the render argv in _synthesize_dynamic_slots(); list this call site under ### UPDATED: review_dispatch_panel.py; add a focused test in test_review_pipeline.py asserting TRIVIAL passes --difficulty TRIVIAL
  - From Cursor-Pragmatic: In _synthesize_dynamic_slots(), append --difficulty with the normalized tier to the render specialist subprocess argv (alongside existing --diff-mode forwarding from context).
  - From Cursor-Requirements: Extend _synthesize_dynamic_slots render_args to pass --difficulty <tier> (same tier parameter already in scope) on every render specialist invocation; add a focused dispatch-panel test that TRIVIAL dynamic pre-renders omit guidelines
  - From Cursor-dyn-Prompt Cache Contract: Add `--difficulty` / `tier` to the `render_args` list in `_synthesize_dynamic_slots()` (alongside existing `--diff-mode` forwarding at lines 405-406). Optionally assert the flag in `test_review_pipeline.py` render-call tests.
  - From Codex-dyn-Prompt Cache Contract: Pass `--difficulty`, `tier` in the `render_args` list inside `_synthesize_dynamic_slots()` and extend that test with a TRIVIAL/MODERATE assertion.


### FINDING_2: Claude review launcher rejects forwarded difficulty
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: `agent_waterfall` forwards `--difficulty` to `launch-claude-review`, but the Claude launcher/parser/render path does not accept or forward the flag, so Claude slots fail on unknown arguments or continue rendering full prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either add optional --difficulty to _claude_runner.py and forward it to render specialist when --role reviewer and --agent-file are used, or emit --difficulty only on the launch-review argv branch (not the Claude branch)
  - From Cursor-Innovation: Add ### UPDATED: python/larch/agents/_claude_runner.py with --difficulty on the parser and forward to render specialist; mirror _review_launcher forwarding
  - From Cursor-Pragmatic: Add python/larch/agents/_claude_runner.py to the plan: accept --difficulty on launch-claude-review and forward it to render specialist (prefer reusing _review_specialist_render_args() so the path stays aligned with launch-review).
  - From Codex-Innovation: Gate `--difficulty` to launchers that accept it, or add `--difficulty` support to `launch_claude_review_main()` and thread it into its specialist render call.
  - From Codex-Pragmatic: Add `--difficulty` to `launch-claude-review` parser and forward it to the specialist render call, or keep `_common_args()` from forwarding it to Claude launchers.
  - From Cursor-Requirements: Add --difficulty to launch-claude-review parser and forward it into the render specialist argv when non-empty; thread tier from review_dispatch_panel waterfall/claude launch the same way as launch-review
  - From Codex-Requirements: Add `--difficulty` to `launch-claude-review`, and forward it into the specialist renderer when `--agent-file` is used, or otherwise keep `_common_args()` from sending the flag to Claude launchers.


### FINDING_3: Plan-review payload telemetry omits architectural bytes
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `render_plan_review_main` computes payload telemetry without counting the architectural guidelines section bytes, so the TRIVIAL payload reduction is underreported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `_byte_len(architectural_guidelines_section)` to `payload_bytes` in `render_plan_review_main` when the section is non-empty, and add a focused plan-review payload sidecar test parallel to the specialist one


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:823-848
- **Concern**: [SCOPE-REDUCTION] docs-only/generated-only gating exceeds required TRIVIAL-only acceptance. Scenario: Issue required change #1 is TRIVIAL-only; optional docs-only/generated-only gating changes MODERATE/HARD specialist output and conflicts with non-TRIVIAL byte-identical acceptance for those diff modes
- **Proposed resolution**: Defer diff_mode gating to a follow-up; ship TRIVIAL tier gating only unless acceptance criteria are revised to exempt docs-only/generated-only prompts ## Findings 1. **correctness** — `python/larch/review/review_dispatch_panel.py:386-415`: `_synthesize_dynamic_slots()` pre-renders dynamic specialist prompts via `render specialist` but never passes `--difficulty`, even though `tier` is already a parameter. On TRIVIAL `/implement` runs with dynamic archetypes, Cursor slots still receive full guidelines baked into `prompt_file`. **Fix:** add `--difficulty`, `tier` to that render argv; extend the plan’s `review_dispatch_panel.py` section and add a pipeline test. 2. **correctness** — `python/larch/agents/_claude_runner.py:461-530`: the plan threads difficulty through `agent_waterfall` → `launch-review` but not `launch-claude-review`, which also renders specialists from `--agent-file`. **Fix:** add `### UPDATED: python/larch/agents/_claude_runner.py` with parser support and render forwarding. 3. **risk-integration** — `python/larch/agents/agent_waterfall.py:484-499`: adding `--difficulty` to `_common_args()` without updating `_claude_runner.py` will make `launch-claude-review` reject unknown flags and break Claude waterfall slots. **Fix:** land both changes together. 4. **architecture** — `python/larch/rendering/rendering.py:823-848`: **[SCOPE-REDUCTION]** docs-only/generated-only guideline gating is optional in the issue and breaks strict non-TRIVIAL byte-identical output for those diff modes. Minimum-change v1 can gate on TRIVIAL only and defer diff-mode gating.


### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:169-274
- **Concern**: [SCOPE-REDUCTION] Optional control-character validation for --difficulty is unnecessary scope. Scenario: The feature only needs empty-allowed argv forwarding and fail-open rendering; extra validation adds parser branches and tests without affecting TRIVIAL gating correctness
- **Proposed resolution**: Drop the optional control-character rejection from agent_waterfall _parse_args; keep empty allowed and forward non-empty values unchanged ### 1. correctness — `python/larch/review/review_dispatch_panel.py:386-415` Dynamic scout slots are pre-rendered inside `_synthesize_dynamic_slots` via a direct `render specialist` subprocess. Those prompts are written to `prompt_file` and consumed by the waterfall without re-rendering. The plan threads `--difficulty` only through `waterfall_args`, so TRIVIAL runs with dynamic archetypes would still ship full guidelines on the Cursor path (Codex dynamic slots are already suppressed at TRIVIAL, but Cursor is not). ### 2. correctness — `python/larch/agents/_claude_runner.py:497-530` `launch-claude-review` renders specialist prompts from `--agent-file` without any difficulty flag. That path is used when the degraded Claude reviewer runs in the panel. It is a specialist-review surface covered by the acceptance criteria, and it is not listed in the plan’s file updates. ### 3. architecture — `python/larch/agents/agent_waterfall.py:169-274` The plan’s optional control-character validation for `--difficulty` in `agent_waterfall` is not required for correct TRIVIAL gating or fail-open behavior. Dropping it keeps the change closer to minimum scope.

### FINDING_1: Plan-review still omits difficulty wiring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: `render_plan_review_main()` is not explicitly required to pass `args.difficulty` into `_architectural_guidelines_review_section()`, so a TRIVIAL plan-review render can still fall back to the full guidelines block and miss the slim-prompt acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `render_plan_review_main()`, call `_architectural_guidelines_review_section(args.difficulty)` (or equivalent) before composing `architectural_guidelines_prompt`, and add a renderer test with `--difficulty TRIVIAL` that asserts invariants present and guidelines absent.
  - From Cursor-Innovation: Add an explicit `render_plan_review_main()` step mirroring `render_specialist_main()`: `architectural_guidelines_section = _architectural_guidelines_review_section(difficulty_value=args.difficulty)` before prompt assembly and payload counting.
  - From Cursor-Pragmatic: In `render_plan_review_main()`, call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before building `architectural_guidelines_prompt`, mirroring `render_specialist_main`.
  - From Cursor-Requirements: In `render_plan_review_main()`, pass `args.difficulty` into `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before building `architectural_guidelines_prompt`; mirror the `render_specialist_main()` step explicitly in the plan.
  - From Codex-Pragmatic: Add an explicit `render_plan_review_main` step to call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)`, and add a focused `render_plan_review_main` `--difficulty TRIVIAL` assertion that invariants remain and guidelines are omitted
  - From Codex-Requirements: Call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` in `render_plan_review_main` and add a TRIVIAL plan-review renderer assertion.


### FINDING_2: Existing payload sidecar expectations need updates
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: minor
- **Concern**: Once architectural section bytes are folded into payload telemetry, several existing payload sidecar tests still assert byte totals that exclude that content, so the current test plan does not account for those stale expectations and CI will break when telemetry is corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan testing strategy to update these existing payload sidecar expectations (or gate fixtures so architectural files are absent) alongside the new TRIVIAL-vs-MODERATE payload assertions.
  - From Cursor-Requirements: List the affected existing payload sidecar tests under python/tests/rendering/test_rendering.py and require updating their expected byte counts (or patching architectural fixtures) alongside the new TRIVIAL/MODERATE cases.


### FINDING_3: Plan-review TRIVIAL/MODERATE test matrix is incomplete
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Pragmatic
- **Severity**: minor
- **Concern**: The planned renderer coverage checks the missing-difficulty path, but it does not yet require explicit TRIVIAL and MODERATE plan-review assertions, so a plan-review slimming regression could ship without being exercised by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `render_plan_review_main()` cases for `--difficulty TRIVIAL` (invariants present, guidelines absent) and `--difficulty MODERATE` (both blocks), matching the specialist coverage already listed in the plan.
  - From Cursor-Pragmatic: Add a render_plan_review_main test with --difficulty TRIVIAL asserting invariants are present and architectural_guidelines tags are absent; keep the existing missing-difficulty fail-open case.
  - From Cursor-Requirements: Add render_plan_review_main() tests for --difficulty TRIVIAL (invariants present, guidelines absent) and MODERATE (both blocks), plus a TRIVIAL-vs-MODERATE payload sidecar reduction assertion once architectural bytes are counted.
  - From Codex-Pragmatic: add a focused render_plan_review_main --difficulty TRIVIAL assertion that invariants remain and guidelines are omitted

