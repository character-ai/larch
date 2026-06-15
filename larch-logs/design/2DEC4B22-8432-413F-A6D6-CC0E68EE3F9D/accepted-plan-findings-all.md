### FINDING_1: Plan missing required ## Acceptance section
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: blocking
- **Concern**: The plan lacks a `## Acceptance` section with at least one verifiable criterion. `/implement` Preflight item 4 (`preflight-plan-audit.md`) requires that section; `Testing strategy` alone does not satisfy the rubric, so a normal `/implement` run will get `AUDIT=refuse` before Step 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ## Acceptance with checkable criteria (for example: unset LARCH_DESIGN_DRAFTER selects Claude with default claude-opus-4-8; make test-design-step2b-drafter and make lint pass; in-scope grep finds no claude-fable-5 or prefer codex)
  - From Cursor-Innovation: Add ## Acceptance with concrete checks: unset LARCH_DESIGN_DRAFTER routes to launch-claude-drafter.sh with model claude-opus-4-8; LARCH_DESIGN_DRAFTER=codex still routes to Codex; docs match; listed tests pass


### FINDING_2: Test harness does not cover unset LARCH_DESIGN_DRAFTER Claude default
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-default-route-correctness
- **Severity**: important
- **Concern**: The planned `test-design-step2b-drafter.sh` work does not exercise the new unset-default Claude route. Existing fixtures export `LARCH_DESIGN_DRAFTER=codex` and stub only the Codex launcher, so tests can pass while the core behavior still defaults to Codex when `CODEX_PRESENT=true`, or passes the wrong Claude model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add one minimal fixture that unsets LARCH_DESIGN_DRAFTER with CODEX_PRESENT=true, stubs launch-claude-drafter.sh, and asserts it receives --model claude-opus-4-8. Keep existing explicit codex coverage unchanged.
  - From Codex-Innovation: Add the smallest routing test in test-design-step2b-drafter.sh: install a fake launch-claude-drafter.sh, run with LARCH_DESIGN_DRAFTER unset and CODEX_PRESENT=true, and assert DRAFTER_VENDOR=claude plus --model claude-opus-4-8
  - From Codex-Pragmatic: Add one focused wrapper test that removes LARCH_DESIGN_DRAFTER from the session env, sets CODEX_PRESENT=true, stubs launch-claude-drafter.sh, and asserts DRAFTER_VENDOR=claude plus --model claude-opus-4-8
  - From Codex-Requirements: Add the smallest update to skills/design/scripts/test-design-step2b-drafter.sh: include a Claude launcher stub and assertions for unset LARCH_DESIGN_DRAFTER with CODEX_PRESENT=true, explicit codex, and the default claude-opus-4-8 model
  - From Codex-dyn-default-route-correctness: Add a minimal test update to the plan: install a Claude drafter stub, assert unset LARCH_DESIGN_DRAFTER with CODEX_PRESENT=true launches Claude with claude-opus-4-8, keep explicit codex coverage, and assert explicit claude honors a LARCH_DESIGN_PLAN_MODEL override


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step2b-drafter.sh:132-143
- **Concern**: [SCOPE-REDUCTION] Plan says an empty LARCH_DESIGN_PLAN_MODEL should take the invalid-model skip path. Scenario: The planned replacement preserves ${LARCH_DESIGN_PLAN_MODEL:-...}, so empty or unset values use the default. Treating empty as invalid would change existing behavior outside the requested default-model swap.
- **Proposed resolution**: Revise the failure-mode bullet to preserve :- semantics: unset or empty uses claude-opus-4-8, while non-empty whitespace/control-containing values remain invalid.


### FINDING_5:
- **Reviewer(s)**: Codex-dyn-default-route-correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:58-62; skills/design/scripts/design-step2b-drafter.sh:131-144; scripts/launch-claude-drafter.sh:173-182
- **Concern**: [SCOPE-REDUCTION] Plan treats an empty LARCH_DESIGN_PLAN_MODEL as invalid even though the current wrapper defaults empty or unset via ${...:-claude-fable-5}. Scenario: An implementer following that failure-mode bullet could change explicit empty handling, violating the plan's own invalid model behavior unchanged requirement; current invalid skip covers whitespace/control model tokens after default expansion, while empty is replaced by the default before validation
- **Proposed resolution**: Revise the failure-mode bullet to remove empty, or state that unset/empty keep the default and only whitespace/control-character model values keep the existing invalid-model skip path




### FINDING_1: Default-route test cannot exercise unset LARCH_DESIGN_DRAFTER
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned default-routing test will not cover unset `LARCH_DESIGN_DRAFTER`. `write_session_env` always exports `LARCH_DESIGN_DRAFTER=codex` into `session.env` (line 142). Sourcing that file overrides a shell-level unset, so the wrapper still routes to Codex and the test can pass without validating Claude-as-default when `LARCH_DESIGN_DRAFTER` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a write_session_env parameter (or sibling helper) that omits LARCH_DESIGN_DRAFTER for the default-route case; keep explicit codex coverage for existing scenarios
  - From Cursor-Pragmatic: The harness step should omit or unset LARCH_DESIGN_DRAFTER in session.env for the default-routing case only; keep explicit codex export for existing cases


### FINDING_2: SECURITY.md omitted despite drafter and model default changes
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits `SECURITY.md` even though Step 2b drafter default selection and `LARCH_DESIGN_PLAN_MODEL` default change. After merge, `SECURITY.md` line 170 still states Step 2b defaults to Codex when Codex is present, and the doc still references `claude-fable-5` as the model default. That misstates the post-change subprocess default and security posture for consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add ### UPDATED: SECURITY.md with a minimal edit to the Step 2b drafter subprocess paragraph and include SECURITY.md in the stale-default grep



