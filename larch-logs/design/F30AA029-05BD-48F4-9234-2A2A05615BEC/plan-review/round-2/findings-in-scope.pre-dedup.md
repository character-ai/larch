### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:783-791
- **Concern**: Step 5 banner-prep computes effective_round_cap inside a Bash subprocess but the proposed banner remains prompt-side prose. Scenario: Claude Code Bash state is not preserved between calls, so the orchestrator cannot use effective_round_cap after a silent prep block and may re-ad-lib the same calculation or print empty/literal banner variables
- **Proposed resolution**: Make the Bash block emit parseable KVs or print the complete banner itself, including dynamic_archetypes_cap, before run-step5-review starts

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:147-157
- **Concern**: The proposed extra Step 5 prep fence adds another IMPLEMENT_TMPDIR prelude and plugin-root.env guard, but the plan omits the pinned cardinality updates. Scenario: relevant-checks will fail because the harness still expects 42 plugin-root guards and the existing IMPLEMENT_TMPDIR assignment/export formula
- **Proposed resolution**: Update the rehydration harness and docs counts, or avoid a new fence by reusing the existing Step 5 invocation fence while keeping the run-step5-review argv unchanged

### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-lib-implement-round-cap.sh:1; .claude/rules/script-md-siblings.md:6-14
- **Concern**: Missing sibling contract for touched harness. Scenario: The plan updates scripts/test-lib-implement-round-cap.sh but does not add the required neighboring scripts/test-lib-implement-round-cap.md stub, leaving the edited scripts/ harness outside the repo's script-md-siblings contract
- **Proposed resolution**: Add scripts/test-lib-implement-round-cap.md as a short stub naming scripts/lib-implement-round-cap.sh as the primary contract and make test-lib-implement-round-cap as the target, matching the new append-execution harness pattern

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:154-161
- **Concern**: Item 4 adds a new Step 5 ```bash fence with plugin-root.env guard plus IMPLEMENT_TMPDIR assign/export but plan does not update timing-rehydration cardinality pins. Scenario: make lint fails: plugin-root guard count must stay 42 and IMPLEMENT_TMPDIR assign/export counts must match token-rehydration plus step-telemetry-mark coupling even when structure and new CLI tests pass
- **Proposed resolution**: [SCOPE-REDUCTION] Fold banner-prep into the existing run-step5-review.sh fence (skills/implement/SKILL.md:789-795) without new IMPLEMENT_TMPDIR assign/export lines, or add scripts/test-implement-timing-rehydration.sh to Files to modify with updated expected counts

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-789; scripts/test-implement-timing-rehydration.sh:145-156
- **Concern**: Step 5 banner-prep block computes values in a child Bash process but does not emit them, and the extra fence changes pinned rehydration cardinality. Scenario: The later prompt-side banner still has no reliable effective_round_cap value, and adding the proposed IMPLEMENT_TMPDIR/export/plugin-root guard block will fail the structural count checks
- **Proposed resolution**: Have the existing Step 5 prelude fence either print the final banner itself or emit parsed KVs for the orchestrator before printing; avoid adding a new rehydration fence, or update the timing-rehydration harness and sibling docs counts if a new fence is truly needed

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:154-161
- **Concern**: Step 5 banner-prep adds a new fenced bash block with another canonical plugin-root.env guard and IMPLEMENT_TMPDIR assign/export, but the plan never updates the byte-exact structural pins. Scenario: `make lint` / `test-harnesses-20` fails: plugin-root guard count stays pinned at 42 (becomes 43) and IMPLEMENT_TMPDIR assign/export coupling drifts because the new fence duplicates those lines without bumping the expected totals
- **Proposed resolution**: Fold banner-prep into the existing Step 5 telemetry fence (already has IMPLEMENT_TMPDIR + plugin-root rehydration) instead of a third Step 5 fence; or keep the new fence and update `test-implement-timing-rehydration.sh` expected counts plus the SKILL.md "42 executable rehydration sites" prose at skills/implement/SKILL.md:115

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-791; scripts/test-implement-timing-rehydration.sh:144-162
- **Concern**: [SCOPE-REDUCTION] Planned Step 5 banner prep is a separate side-effect-only Bash block with extra rehydration/export lines. Scenario: The Bash tool does not preserve shell variables, so assigned effective_round_cap is unavailable to the markdown banner unless the block emits it or prints the banner in the same shell; adding another plugin-root guard and IMPLEMENT_TMPDIR export also trips the exact-count rehydration harness
- **Proposed resolution**: Keep the computation in the existing Step 5 invocation fence and print the banner there before run-step5-review.sh, or emit parseable EFFECTIVE_ROUND_CAP from the prep block; drop the unnecessary IMPLEMENT_TMPDIR self-assignment/export and avoid adding a second plugin-root guard unless the timing test is updated intentionally

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:105-115
- **Concern**: Plan omits Bash block prelude update though issue item 1 cites missing initial-entry CLAUDE_PLUGIN_ROOT documentation there. Scenario: After wrapper self-derive lands, prelude still says pre-bootstrap sites only rehydrate from tmpdir/session-env and that plugin-rooted helpers are infeasible until CLAUDE_PLUGIN_ROOT is set — recreates the #3448 doc gap and misroutes orchestrators away from the new wrapper contract
- **Proposed resolution**: Add a short Bash block prelude bullet: initial Step 0 may call implement-bootstrap-invoke.sh before tmpdir exists; the wrapper self-derives and exports CLAUDE_PLUGIN_ROOT from $0 when unset; post-Step-0 rehydration via plugin-root.env unchanged

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-790
- **Concern**: Step 5 prep keeps computed banner values inside a Bash subshell. Scenario: The planned block assigns prior_degraded_rounds and effective_round_cap but emits neither value and shell state is not preserved across Bash calls, so the following prompt-side banner still lacks the computed value and may print a literal/stale value or force another ad-hoc computation
- **Proposed resolution**: Fold the CLI call and banner printf into the same Bash block, or emit parseable KV lines for effective_round_cap/dynamic_archetypes_cap and instruct the orchestrator to parse them before printing the banner

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:298-308 (proposed Step 0 edit)
- **Concern**: [SCOPE-REDUCTION] Item 1 adds a Step 0 SKILL.md CLAUDE_PLUGIN_ROOT literal fallback plus caller-level harness coverage beyond the approved outline which scoped SKILL edits to the Step 5 banner only. Scenario: The #3448 failure was implement-bootstrap-invoke.sh:32 with the wrapper already reached via template-expanded paths; wrapper self-derive+export fixes that without a SKILL prelude. Dual layers duplicate the issue's either/or remediations and widen review/structure-test surface
- **Proposed resolution**: Limit Item 1 to scripts/implement-bootstrap-invoke.sh self-derive+export (and its .md/test). Drop the proposed Step 0 caller fallback block and the mirror caller-level harness case; keep only the unset-CLAUDE_PLUGIN_ROOT direct-wrapper invoke test

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:298-308; .claude/rules/skill-runtime-root-paths.md:1-7
- **Concern**: [SCOPE-REDUCTION] Step 0 SKILL fallback exceeds the approved surface and invites a public-SKILL hardcoded root. Scenario: The approved direction limits skills/implement/SKILL.md work to the Scripted review loop banner, while current public skill paths use ${CLAUDE_PLUGIN_ROOT}/...; the plan adds a Step 0 pre-wrapper fallback using an <installed-plugin-root> literal/path source, broadening the startup contract and risking machine/cache path drift in shipped prompt text
- **Proposed resolution**: Drop the Step 0 SKILL.md fallback, its implement-bootstrap-invoke.md note, and the caller-level no-tmpdir test; keep the wrapper self-derive/export change plus a direct-wrapper unset-env test. If caller fallback is truly required, send it back for explicit scope approval and express it without literal installed paths

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-shell-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:100-105
- **Concern**: Step 0 fallback uses non-repo `<installed-plugin-root>` placeholder instead of skill-loader `${CLAUDE_PLUGIN_ROOT}` expansion. Scenario: The fenced assignment `CLAUDE_PLUGIN_ROOT="<installed-plugin-root>"` is not a loader token anywhere in the repo; a literal paste leaves `CLAUDE_PLUGIN_ROOT` wrong or empty and Step 0 still dies on `${CLAUDE_PLUGIN_ROOT}/...` expansion before wrapper self-derive runs
- **Proposed resolution**: Use the same pattern as `skills/design/SKILL.md` and `SECURITY.md`: `[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` (loader-expanded) before `export CLAUDE_PLUGIN_ROOT`, and pin that literal in `scripts/test-implement-structure.sh` if needed

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-shell-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:109-124
- **Concern**: The Step 5 banner-prep Bash fence assigns `prior_degraded_rounds` / `effective_round_cap` but the markdown banner line still expands `$effective_round_cap` outside the fence. Scenario: Each Bash tool call is a fresh subshell; the fence captures CLI output internally and emits no stdout KVs, so the orchestrator cannot see `effective_round_cap` for the separate Print line (resume/re-entry with prior degraded rounds shows the wrong cap or the model re-guesses)
- **Proposed resolution**: Either echo machine-readable stdout from the fence (`effective_round_cap=<n>` / `prior_degraded_rounds=<n>`) and instruct the orchestrator to parse it before printing, or move the banner `printf` into the same fenced block (keep `dynamic_archetypes_cap` prose-derived as today)

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-shell-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:109-122; skills/implement/SKILL.md:770-775; scripts/test-implement-timing-rehydration.sh:143-156
- **Concern**: Step 5 banner-prep snippet duplicates the existing IMPLEMENT_TMPDIR export and plugin-root source guard without updating the count-pinned structure harness. Scenario: Following the plan literally as a new fenced block adds another IMPLEMENT_TMPDIR assignment/export and plugin-root.env source line; test-implement-timing-rehydration expects those counts to match current telemetry/root-rehydration pins and will fail relevant-checks
- **Proposed resolution**: Revise the plan to extend the existing Step 5 setup fence at skills/implement/SKILL.md:770-775 and reuse its IMPLEMENT_TMPDIR export/root source, or explicitly include the required test-implement-timing-rehydration expectation update if a separate block is intentional.

