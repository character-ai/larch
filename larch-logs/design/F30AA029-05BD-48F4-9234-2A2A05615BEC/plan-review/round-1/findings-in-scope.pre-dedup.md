### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:370-375
- **Concern**: Plan adds Makefile-only scripts/test-append-execution-issue.sh and .md but omits the repo's dead-script exclusion wiring. Scenario: agent-lint does not treat Makefile targets as reachability edges, so bash scripts/relevant-checks.sh can fail G004/S030 on the new harness despite the Makefile target and shard entry
- **Proposed resolution**: Add agent-lint.toml to the plan with exclude entries and a short Makefile-only rationale for scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md, mirroring scripts/test-append-tool-failure.sh/.md

### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:370-374; scripts/test-append-execution-issue.sh:planned
- **Concern**: New Makefile-only harness is not added to agent-lint dead-script excludes. Scenario: The plan creates scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md, referenced only from Makefile like test-append-tool-failure. agent-lint does not follow Makefile-only harness wiring, so the planned relevant-checks run can fail even though the harness is correctly sharded
- **Proposed resolution**: Add agent-lint.toml exclude entries for scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md beside the analogous test-append-tool-failure exclusions

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783
- **Concern**: Step 5 SKILL edit says run the round-cap CLI but omits capturing stdout into prior_degraded_rounds. Scenario: The adjacent prose still sets effective_round_cap=$((round_cap + prior_degraded_rounds)); an orchestrator that runs the CLI without command substitution leaves prior_degraded_rounds empty and the banner shows 5 regardless of degraded history
- **Proposed resolution**: Replace the glob/loop clause with prior_degraded_rounds=$("${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1) (or equivalent) before the round_cap/effective_round_cap lines; match Round 1 design discussion wording

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:370-375
- **Concern**: Plan adds a Makefile-only scripts/test-append-execution-issue.sh harness but does not update agent-lint.toml reachability or exclude config. Scenario: agent-lint ignores Makefile-only harnesses per adjacent comments, so bash scripts/relevant-checks.sh can fail on the new test script or sibling md as dead/unregistered despite Makefile wiring
- **Proposed resolution**: Add scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md to the exclude list near test-append-tool-failure, or add an agent-lint-visible structured registration if preferred

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Item 4 replaces the degraded-round prose with a bare directive to run the new lib CLI but does not place it in a fenced bash block with the canonical plugin-root rehydration prelude or assign stdout to prior_degraded_rounds. Scenario: Orchestrator must invoke a plugin script via Bash; without the same [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && … plugin-root.env guard used in the adjacent run-step5-review fence, CLAUDE_PLUGIN_ROOT is empty across Bash tool calls and the count invocation fails or the banner uses an empty/wrong effective_round_cap — the same friction class as item 1
- **Proposed resolution**: Add a small fenced bash block before the banner line: standard rehydration prelude, export IMPLEMENT_TMPDIR, then prior_degraded_rounds=$("${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1); keep round_cap/effective_round_cap and the existing run-step5-review fence unchanged

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:370-375
- **Concern**: Plan adds a Makefile-only append-execution-issue harness but does not add the new harness and sibling doc to agent-lint exclusions. Scenario: `bash scripts/relevant-checks.sh` runs agent-lint, and existing Makefile-only harnesses such as `scripts/test-append-tool-failure.sh` are excluded because agent-lint does not follow Makefile-only refs; the new `scripts/test-append-execution-issue.sh` / `.md` can fail the promised validation despite Makefile wiring
- **Proposed resolution**: Add `scripts/test-append-execution-issue.sh` and `scripts/test-append-execution-issue.md` to `agent-lint.toml` near the analogous append-tool-failure harness exclusion, or explicitly justify why agent-lint will see this harness through a runtime reference

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Item 4 replaces glob/loop prose with a prose-only CLI directive and does not add a fenced Bash capture block adjacent to the Step 5 entry prelude. Scenario: Orchestrator may still ad-lib Bash (missing plugin-root rehydration or malformed invocation), repeating the #3448 item-4 syntax-error friction the CLI was meant to eliminate
- **Proposed resolution**: Fold `lib-implement-round-cap.sh --count-prior-degraded "$IMPLEMENT_TMPDIR" 1` into the `770-775` bash fence after `plugin-root.env` sourcing; keep prose limited to parsing stdout into `prior_degraded_rounds` before the banner line

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-contract-surface
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Item 4 SKILL change is prose-only — no fenced CLI capture with rehydration before banner. Scenario: Orchestrator can still improvise invalid shell (the #3448 item 4 failure mode) because banner math stays prompt-side while only the algorithm text changed
- **Proposed resolution**: Add a Step 5 Bash fence (with IMPLEMENT_TMPDIR export + plugin-root.env rehydration) that runs lib-implement-round-cap.sh --count-prior-degraded and captures stdout; state orchestrator must parse that output into prior_degraded_rounds before printing the banner

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-contract-surface
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:298-308, scripts/implement-bootstrap-invoke.sh:32
- **Concern**: Planned self-derive is only inside the wrapper, but the documented initial caller still needs CLAUDE_PLUGIN_ROOT to locate that wrapper. Scenario: Fresh Step 0 initial entry with no IMPLEMENT_TMPDIR/plugin-root.env and no exported CLAUDE_PLUGIN_ROOT expands the call to /scripts/implement-bootstrap-invoke.sh before the new derivation can run, so item 1 can still fail earlier than the guard
- **Proposed resolution**: Update the Step 0 initial caller to make the wrapper path independent of CLAUDE_PLUGIN_ROOT in the no-tmpdir case, or render/export a plugin-root fallback before any ${CLAUDE_PLUGIN_ROOT}/... command; add a caller-level test for the unset initial path

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Step 5 SKILL edit says to run the round-cap CLI but omits binding stdout into prior_degraded_rounds. Scenario: Orchestrator can invoke lib-implement-round-cap.sh and still leave prior_degraded_rounds unset or re-improvise parsing, so effective_round_cap in the banner stays wrong and item 4 does not remove prompt-side glob/loop risk
- **Proposed resolution**: Replace the prose with an explicit assignment: prior_degraded_rounds="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1")" then round_cap=5 and effective_round_cap=$((round_cap + prior_degraded_rounds)) before the banner line

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:107-113,783-795
- **Concern**: Step 5 banner CLI is planned without the required CLAUDE_PLUGIN_ROOT rehydration guard. Scenario: After Step 0, Bash does not preserve CLAUDE_PLUGIN_ROOT; a fresh banner computation call to bash ${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh can fail before run-step5-review, recreating orchestrator friction
- **Proposed resolution**: Make the banner-count command a guarded Bash snippet: source $IMPLEMENT_TMPDIR/plugin-root.env with the canonical guard, then assign and validate prior_degraded_rounds from the new CLI before printing, or run it inside the existing guarded Step 5 block before invoking run-step5-review

