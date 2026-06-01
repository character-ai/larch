### FINDING_1: Structural harness still pins removed inline Step 18b block
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan extracts Step 18b into `step-18b-final-report.sh` and drops the inline `_wfr_*` / `--print-stdout` / in-fence `cmp` block from `SKILL.md`, but `scripts/test-implement-structure.sh` (and related structural pins) still require those removed literals. After the extraction, `make lint` fails on assertion 18 / `test-harnesses-16` even when the runtime change is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `scripts/test-implement-structure.sh` and `scripts/test-render-cost-line-callsites.sh` to **Files to modify**; repin Step 18 to the wrapper call, `EMIT_BODY` parsing, and the no-`--print-stdout` contract (per `test-implement-structure.md:21-22`)
  - From Codex-Arch: Update this harness in the same PR to assert the new wrapper call and EMIT_BODY/WFR_RC parsing, and move the cmp/body-change behavior assertion to test-step-18b-final-report.sh.
  - From Cursor-Innovation: Add explicit plan steps to retarget those pins to `step-18b-final-report.sh` / `EMIT_BODY` (and run the harness in Testing strategy)
  - From Codex-Innovation: Update this harness to pin the new wrapper call plus EMIT_BODY/success-guard prose, or remove the obsolete inline _wfr_args and cmp shape checks
  - From Codex-Pragmatic: Update test-implement-structure.sh in the plan to pin the new step-18b-final-report.sh invocation and wrapper-level cmp/EMIT_BODY contract instead of the removed inline Bash block


### FINDING_2: EMIT_BODY can stay true when final report write fails or body is empty
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-emit-boundary, Codex-Requirements, Cursor-dyn-state-contract
- **Severity**: important
- **Concern**: The planned wrapper can set `EMIT_BODY=true` from `.step17-emitted` / cmp logic even when `write-final-report.sh` returns non-zero or leaves `summary-final.md` missing or empty. `SKILL.md` keys verbatim emission on `EMIT_BODY=true`, violating the existing Step 18 success gate: the orchestrator may emit stale pre-refresh content, write `.step17-emitted` incorrectly, or attempt a NEVER #20 verbatim emit on an empty body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the wrapper emit EMIT_BODY=true only when WFR_RC=0 and summary-final.md is non-empty, or make SKILL.md require both EMIT_BODY=true and WFR_RC=0 before reading/emitting the body and writing .step17-emitted.
  - From Codex-Innovation: (same slot as Codex-Arch in source FINDING_2 — covered by Codex-Arch bullet above; no separate verbatim in FINDING_2)
  - From Codex-Pragmatic: (same theme as Codex-Arch in source FINDING_2)
  - From Codex-dyn-emit-boundary: (grouped with Codex-Arch in source FINDING_2)
  - From Codex-Requirements: Gate EMIT_BODY on WFR_RC=0 and non-empty summary-final.md, or require SKILL.md to emit only when EMIT_BODY=true and WFR_RC=0; add a write-final-report failure case to test-step-18b-final-report.sh
  - From Cursor-dyn-state-contract: Gate EMIT_BODY in step-18b-final-report.sh on post-write `[ -s "$tmpdir/summary-final.md" ]` and keep the SKILL.md orchestrator `-s` guard alongside `EMIT_BODY=true`


### FINDING_3: Wrapper must use rooted helper paths and rehydrate token/session env
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned `step-18b-final-report.sh` drops rooted helper invocation and token/session rehydration that the current Step 18 block performs. Bare `token-report.sh` / `write-final-report.sh` PATH lookup can fail when plugin scripts are not on PATH, bind token reporting to the wrong transcript, or allow PATH hijack in consumer repos; PATH-stubbed tests may hide the integration break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Inside the wrapper, compute SCRIPT_DIR and PLUGIN_ROOT, rehydrate LARCH_TOKEN_SESSION_ID, LARCH_CLAUDE_SOURCE_FILE, and LARCH_TIMING_LEDGER from session-env.sh, and invoke $PLUGIN_ROOT/scripts/token-report.sh plus $SCRIPT_DIR/write-final-report.sh by rooted path
  - From Codex-Innovation: Have step-18b-final-report.sh resolve PLUGIN_ROOT/SCRIPT_DIR and invoke token-report.sh, write-final-report.sh, and append-tool-failure.sh by absolute repo paths; stub tests via a temp plugin root rather than PATH
  - From Codex-Pragmatic: Resolve SCRIPT_DIR/PLUGIN_ROOT in the wrapper and invoke "$PLUGIN_ROOT/scripts/token-report.sh" plus "$SCRIPT_DIR/write-final-report.sh"; adapt tests with a stub plugin root or explicit override vars


### FINDING_4: Duplicate Step 18b failure capture in SKILL orchestrator prose
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: After E2 moves token-report / write-final-report work into `step-18b-final-report.sh`, `SKILL.md` still instructs the orchestrator to capture those failures, risking duplicate `step18-*.failure.log` files and duplicate `append-tool-failure` Tool Failures rows when the wrapper already logs best-effort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When replacing the _wfr_* block, state that step-18b-final-report.sh owns capture/append; delete or narrow the orchestrator-only capture sentence


### FINDING_6: seed-terminal-state lacks symlink/malformed-state guards on existing file
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: important
- **Concern**: `clear-stall` gets regular-file / non-symlink / malformed-state validation, but `seed-terminal-state` only documents key-rewrite when `ship-pr-state.sh` exists, leaving the mutating terminal path without the same checks. A symlinked or malformed existing state file can be read/rewritten, violating the plain `KEY=value` non-symlink contract and making seed behavior inconsistent with classify/clear-stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-contract: Apply the same regular non-symlink guard and validate_ship_pr_state check before seed-terminal-state rewrites an existing file; reject malformed present state with the documented exit-3 path.


### FINDING_7: Malformed stall state may omit promised CLEARED/SEEDED machine keys
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: latent
- **Concern**: Proposed stall-recovery prose branches on `CLEARED` and `SEEDED`, but malformed-state handling may exit 3 without emitting those machine keys, leaving the orchestrator without the promised KV output for terminal-route decisions during `clear-stall` or `seed-terminal-state`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-contract: Either emit CLEARED=false or SEEDED=false before expected validation exits, or make the Step 7/8 prose explicitly treat non-zero or missing KV output as the terminal branch.


### FINDING_9: clear-stall tests omit append-when-absent STALL_* key contract
- **Reviewer(s)**: Codex-dyn-harness-integration
- **Severity**: latent
- **Concern**: Planned clear-stall happy-path tests may not cover the case where an existing `ship-pr-state.sh` lacks `STALL_TRACKING` / `STALL_STEP`. If the awk rewrite only updates existing keys, a partial state file can pass tests but still fail later teardown validation that requires those keys to exist after Step 7 success clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-integration: Add one minimal clear-stall fixture with an existing state file missing STALL_TRACKING and STALL_STEP, asserting CLEARED=true plus appended STALL_TRACKING=false and STALL_STEP= while preserving unrelated keys

---

**Merge notes (diagnostic):** 17 source rows → 9 merged findings. Harness/structure pins (source 1,3,5,6,10); EMIT_BODY gating (2,11,12); rooted paths/env (4,7,9) were consolidated. Source FINDING_2 listed Codex-Innovation, Codex-Pragmatic, and Codex-dyn-emit-boundary without distinct verbatim resolutions beyond Codex-Arch’s text — those slots are attributed on the finding but only slots with distinct verbatim bullets appear above.

