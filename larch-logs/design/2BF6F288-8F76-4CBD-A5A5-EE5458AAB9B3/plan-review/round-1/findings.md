### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:302-310
- **Concern**: Plan omits structural-harness updates that grep Step 18 `_wfr_*` / `--print-stdout` literals. Scenario: After SKILL.md swaps the `_wfr_*` block for `step-18b-final-report.sh`, `make lint` fails on assertion 18 (`_wfr_args+=(--print-stdout)` and `.step18-prebody` cmp pins)
- **Proposed resolution**: Add `scripts/test-implement-structure.sh` and `scripts/test-render-cost-line-callsites.sh` to **Files to modify**; repin Step 18 to the wrapper call, `EMIT_BODY` parsing, and the no-`--print-stdout` contract (per `test-implement-structure.md:21-22`)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-emit-boundary, Codex-dyn-harness-integration
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1449-1451; skills/implement/scripts/step-18b-final-report.sh:NEW
- **Concern**: FINDING_1: Proposed EMIT_BODY can stay true when write-final-report.sh fails. Scenario: The plan says WFR non-zero skips only the cmp branch and EMIT_BODY still reflects .step17-emitted absence, while SKILL.md will key emission on EMIT_BODY=true. That violates the existing success gate and can emit stale or failed summary-final.md content.
- **Proposed resolution**: Make the wrapper emit EMIT_BODY=true only when WFR_RC=0 and summary-final.md is non-empty, or make SKILL.md require both EMIT_BODY=true and WFR_RC=0 before reading/emitting the body and writing .step17-emitted.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:302-310
- **Concern**: FINDING_2: Structure harness still pins the old inline Step 18b block. Scenario: The plan replaces the SKILL.md inline _wfr_args/cmp block with step-18b-final-report.sh, but leaves this harness expecting those removed literals, so make lint will fail after the intended extraction.
- **Proposed resolution**: Update this harness in the same PR to assert the new wrapper call and EMIT_BODY/WFR_RC parsing, and move the cmp/body-change behavior assertion to test-step-18b-final-report.sh.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-18b-final-report.sh:1 (planned), skills/implement/SKILL.md:1423-1428
- **Concern**: Planned wrapper drops the rooted helper calls and token env rehydration that the current Step 18 block performs. Scenario: Token reporting can bind to the wrong Claude transcript or fail to find helpers when scripts/ is not on PATH, producing stale or wrong final cost data
- **Proposed resolution**: Inside the wrapper, compute SCRIPT_DIR and PLUGIN_ROOT, rehydrate LARCH_TOKEN_SESSION_ID, LARCH_CLAUDE_SOURCE_FILE, and LARCH_TIMING_LEDGER from session-env.sh, and invoke $PLUGIN_ROOT/scripts/token-report.sh plus $SCRIPT_DIR/write-final-report.sh by rooted path

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:302-310
- **Concern**: Plan rewrites Step 18b SKILL prose but does not update structural pins that require `_wfr_args+=(--print-stdout)` and in-fence `cmp -s` against `.step18-prebody`. Scenario: `make lint` fails on `test-harnesses-16` (`test-implement-structure`) after SKILL drops the `_wfr_*` block
- **Proposed resolution**: Add explicit plan steps to retarget those pins to `step-18b-final-report.sh` / `EMIT_BODY` (and run the harness in Testing strategy)

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:302-310
- **Concern**: Structural test still pins the old inline Step 18b Bash shape. Scenario: The plan replaces _wfr_args/inline cmp logic with step-18b-final-report.sh, so test-implement-structure.sh and make lint will fail even if the extraction is correct
- **Proposed resolution**: Update this harness to pin the new wrapper call plus EMIT_BODY/success-guard prose, or remove the obsolete inline _wfr_args and cmp shape checks

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/SKILL.md:1428-1442
- **Concern**: Plan appears to move trusted helper calls from absolute plugin paths to PATH-resolved names. Scenario: The new wrapper spec and PATH-stubbed harness imply bare token-report.sh/write-final-report.sh lookup; a consumer repo or altered PATH could hijack cleanup-time execution
- **Proposed resolution**: Have step-18b-final-report.sh resolve PLUGIN_ROOT/SCRIPT_DIR and invoke token-report.sh, write-final-report.sh, and append-tool-failure.sh by absolute repo paths; stub tests via a temp plugin root rather than PATH

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1451-1452
- **Concern**: Step 18b still tells the orchestrator to capture token-report/write-final-report failures after E2 moves that work into step-18b-final-report.sh. Scenario: Duplicate step18-*.failure.log captures and append-tool-failure Tool Failures rows when the wrapper already logs best-effort
- **Proposed resolution**: When replacing the _wfr_* block, state that step-18b-final-report.sh owns capture/append; delete or narrow the orchestrator-only capture sentence

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-18b-final-report.sh (planned), plan.txt:36-39
- **Concern**: Planned wrapper appears to invoke token-report.sh and write-final-report.sh as bare PATH commands. Scenario: Production Step 18 currently uses CLAUDE_PLUGIN_ROOT absolute paths; if plugin scripts are not on PATH, the wrapper can fail to refresh the final report while PATH-stubbed tests hide the integration break
- **Proposed resolution**: Resolve SCRIPT_DIR/PLUGIN_ROOT in the wrapper and invoke "$PLUGIN_ROOT/scripts/token-report.sh" plus "$SCRIPT_DIR/write-final-report.sh"; adapt tests with a stub plugin root or explicit override vars

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:302-310
- **Concern**: Plan rewrites Step 18 but does not update the existing structural pin for the removed _wfr_args --print-stdout block. Scenario: make lint will fail because the current structure test still requires tokens the plan removes
- **Proposed resolution**: Update test-implement-structure.sh in the plan to pin the new step-18b-final-report.sh invocation and wrapper-level cmp/EMIT_BODY contract instead of the removed inline Bash block

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1449-1451; plan.txt:37-41,72,79-81
- **Concern**: Plan can emit EMIT_BODY=true after write-final-report.sh fails. Scenario: The current Step 18 contract says not to emit summary-final.md when Step 18 render failed, but the plan keeps EMIT_BODY=true from a missing .step17-emitted sentinel even when WFR_RC is nonzero; the orchestrator could emit stale pre-refresh content and write .step17-emitted incorrectly
- **Proposed resolution**: Gate EMIT_BODY on WFR_RC=0 and non-empty summary-final.md, or require SKILL.md to emit only when EMIT_BODY=true and WFR_RC=0; add a write-final-report failure case to test-step-18b-final-report.sh

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1449 / plan.txt:37-41
- **Concern**: Step 18b wrapper sets EMIT_BODY from .step17-emitted and cmp only; SKILL still gates verbatim emit on non-empty summary-final.md. Scenario: Orchestrator keyed only on EMIT_BODY=true can attempt a NEVER #20 verbatim emit when summary-final.md is empty (e.g. write-final-report succeeded with an empty body), regressing Step 17/18 collapse-resistant rules
- **Proposed resolution**: Gate EMIT_BODY in step-18b-final-report.sh on post-write `[ -s "$tmpdir/summary-final.md" ]` and keep the SKILL.md orchestrator `-s` guard alongside `EMIT_BODY=true`

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh (planned seed-terminal-state); scripts/ship-pr.md:37-43; scripts/ship-pr.sh:510-571; scripts/implement-finalize.sh:177-206,1228-1257
- **Concern**: The fresh seed path proposes a six-key ship-pr-state.sh, but the current state-file contract requires the full write_initial_state key set, including issue/repo identity and finalizer booleans.. Scenario: A pre-Step-8 stall with no existing ship-pr-state.sh gets SEEDED=true, then restore-finalize-state.sh derives empty ISSUE_NUMBER/REPO/RUN_ID defaults; implement-finalize.sh sees STALL_TRACKING=true but cannot apply the [STALLED] title-prefix branch or flush the stalled run log against the right run.
- **Proposed resolution**: Seed the existing canonical Step-8 state shape rather than the six-key subset, pulling ISSUE_NUMBER/RUN_ID/REPO/REPO_UNAVAILABLE and finalizer booleans from the same session/parent sources used by the current Step 5 seed or ship-pr write_initial_state contract; add the harness assertion for these rename-critical keys.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/stall-recovery-report.sh (planned seed-terminal-state); skills/implement/scripts/stall-recovery-report.sh:79-90,114-130; scripts/ship-pr.md:43
- **Concern**: The plan gives clear-stall a regular-file/non-symlink/malformed-state guard, but seed-terminal-state only says “when ship-pr-state.sh exists: key-rewrite,” leaving the mutating terminal path without the same validation.. Scenario: A symlinked or malformed existing ship-pr-state.sh can be read/rewritten on the terminal path, violating the plain KEY=value non-symlink state contract and making seed behavior differ from classify/clear-stall.
- **Proposed resolution**: Apply the same regular non-symlink guard and validate_ship_pr_state check before seed-terminal-state rewrites an existing file; reject malformed present state with the documented exit-3 path.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:30-44; skills/implement/scripts/stall-recovery-report.md:101-110
- **Concern**: The proposed prose branches on CLEARED and SEEDED, but the proposed malformed-state behavior exits 3 and may not emit those machine keys.. Scenario: A malformed state during clear-stall or seed-terminal-state can produce no CLEARED=false or SEEDED=false line, leaving the orchestrator without the promised machine output for the terminal-route decision.
- **Proposed resolution**: Either emit CLEARED=false or SEEDED=false before expected validation exits, or make the Step 7/8 prose explicitly treat non-zero or missing KV output as the terminal branch.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-harness-integration
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-write-final-report.sh:505-558; skills/implement/scripts/test-write-final-report.md:3-6
- **Concern**: F2 Existing write-final-report harness would keep pinning the retired inline Step 18 --print-stdout contract. Scenario: The plan moves Step 18 emit decision into step-18b-final-report.sh and intentionally drops --print-stdout, but the existing harness and sibling doc still describe Step 18 conditional --print-stdout mirroring; leaving them unchanged creates contradictory coverage that can pass while no longer testing the live Step 18 path
- **Proposed resolution**: Move the Step 18 emit matrix to test-step-18b-final-report.sh and retitle or trim the old cases/docs so test-write-final-report only covers write-final-report.sh interface behavior

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-harness-integration
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:30-37; scripts/implement-finalize.sh:177-184
- **Concern**: F3 Planned clear-stall tests do not cover the append-when-absent state-key contract. Scenario: Step 7 requires the success clear to leave durable STALL_TRACKING=false and STALL_STEP=, and teardown later requires STALL_TRACKING to exist; if the new awk rewrite only updates existing keys, a session-layer stall with a partial ship-pr-state.sh can pass the proposed happy-path tests but still fail teardown validation
- **Proposed resolution**: Add one minimal clear-stall fixture with an existing state file missing STALL_TRACKING and STALL_STEP, asserting CLEARED=true plus appended STALL_TRACKING=false and STALL_STEP= while preserving unrelated keys
