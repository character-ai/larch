### FINDING_1: Drafter pre-draft pause must emit POSTPLAN rows before pause-save
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: blocking
- **Concern**: When `.pause-requested` exists at drafter entry (after step-2a repair), the port must print whole-line `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before calling `design pause-save`. Step 2b orchestration and tests bind pause routing from those wrapper rows; a Python path that only execs pause-save drops machine routing evidence and can fall through to inline drafting or postplan fail-safes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit drafter requirement: after step-2a repair and design_require_plugin_root, when .pause-requested exists print POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save then call design pause-save with --repo when set; add pytest asserting those rows on the drafter pause short-circuit.
  - From Cursor-Requirements: In `design step2b-drafter`, before any vendor launch, mirror bash: emit `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save`, then call pause-save with optional `--repo`; add pytest asserting pre-draft pause stdout includes both rows (parity with `test-design-step2b-drafter.sh`).


### FINDING_3: Codex drafter must port both token append paths
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Bash runs both `token append-record` (tmpdir ledger) and `token record-vendor-sidecar` (active ledger). Porting only one path drops Codex drafter cost telemetry on the other ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port both append paths with the same env unset list, stale-sidecar ignore rules, and non-fatal warning stderr as bash.


### FINDING_5: Retired wrapper paths leave live tracked references that break lint-retired-scripts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-postplan-parity, Codex-dyn-autofix-audit
- **Severity**: blocking
- **Concern**: After appending deleted Step 2 and validator wrapper paths to `python/migrated-scripts.tsv`, `make lint-retired-scripts` will still fail on tracked full-path references in `.claude/rules/topology-generation.md` and `skills/design/scripts/_dbg-validator.sh`. The debug helper also invokes a deleted validator wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add both files to the plan. Retarget or remove the topology path entry, and retarget _dbg-validator.sh to python/cli.py plan validator-autofix or delete it if obsolete
  - From Codex-Innovation: Update or delete those references before adding the manifest rows. Point the topology rule at python/design_lifecycle.py as the new authority, and update _dbg-validator.sh to call python/cli.py plan validator-autofix or retire the debug helper.
  - From Codex-Pragmatic: Update the plan to cover these two files: replace the topology rule path with the new Python authority or remove it, and retarget or delete _dbg-validator.sh so it calls python/cli.py plan validator-autofix or no longer ships
  - From Codex-Requirements: Add these files to the plan: retarget the topology rule path to the Python authority or remove the stale path, and update or delete _dbg-validator.sh to call python/cli.py plan validator-autofix without the retired path literal
  - From Codex-dyn-postplan-parity: Expand the plan to update the topology rule path and either retarget or delete _dbg-validator.sh
  - From Codex-dyn-autofix-audit: Add these tracked references to the plan: retarget or remove skills/design/scripts/_dbg-validator.sh, and update .claude/rules/topology-generation.md to the new Python authority path.


### FINDING_6: Session-env parser must decode shlex-quoted export values
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: `write-design-env` emits shlex-quoted export lines; a quoted `DESIGN_TMPDIR` such as a path containing spaces can be parsed with literal quotes or truncated, breaking Step 2 rehydration and `validate-design-tmpdir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require the shared allowlist parser to decode the existing export KEY=shlex.quote(value) format, with a path-with-spaces regression for a ported Step 2 verb


### FINDING_7: Step 2a and Step 2b drafter ports must preserve timing marks
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Plan ports Step 2a and Step 2b drafter without the existing `timing mark` calls, causing `/design` timing ledger drift for Step 2a and Step 2b cost and duration reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `timing mark` for `design Step 2a — sentinel prep` and `design Step 2b — plan` to the Step 2a and step2b-drafter Python bodies with the same `|| true` best-effort semantics as bash.


### FINDING_8: Postplan rc 10 inline-retry contract is underspecified versus bash
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-postplan-parity
- **Severity**: important
- **Concern**: Bash rc 10 path writes `.step2b-postplan-inline-retry-pending`, flips `.step2b-plan-source` to `inline`, sets `.step2b-postplan-fallback-used=true`, clears scout manifests, emits `SCOUT_STALE_CLEARED=true`, and prints the inline-retry warning. Omitting any step breaks the single inline retry gate in `skills/design/SKILL.md` and drafter test case 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Spell out the full rc 10 sentinel and stdout choreography in the `design step2b-postplan` port and cover each artifact in pytest.
  - From Cursor-dyn-postplan-parity: Enumerate the full rc 10 side-effect list in the design step2b-postplan port section and mirror it in pytest assertions


### FINDING_9: Launcher cutover must forward caller argv tail after transport flags
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-launcher-cutover, Codex-dyn-launcher-cutover
- **Severity**: blocking
- **Concern**: Launcher remap plan pins only `--session-env-path` and `--claude-pid`. Settle, postplan, and validator fences pass required flags such as `--site`, `--snapshot-original`, `--write-completion-only`, and validator-specific args. A launcher that does not forward remaining argv drops them and breaks Gate B/A postplan and validator autofix after bash deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Generate launcher branches like `exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"` (and the analogous validator mapping).
  - From Cursor-dyn-launcher-cutover: Specify each retired-name case as `exec python3 "$PLUGIN_ROOT/python/cli.py" <verb> --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"` and add launcher tests asserting `--site` / `--snapshot-original` survive for postplan and validator flags for autofix
  - From Codex-dyn-launcher-cutover: Add "$@" to each mapped Python exec and add a python/test_session_env.py assertion that a mapped retired wrapper preserves a sample caller flag and value, while keeping the existing CLAUDE_PLUGIN_ROOT export and unported fallback behavior.


### FINDING_10: Structural tests and SKILL inventory must retarget after bash deletion
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-postplan-parity
- **Severity**: important
- **Concern**: Deleting Step 2 bash wrappers without updating `skills/design/SKILL.md` wrapper contract inventory, `test-design-structure.sh` greps, and postplan rc-matrix guards will fail `make test-design-structure` and `make lint`. Assertions still grep deleted `.sh` bodies for postplan rc matrix, drafter delegation, thin-fence rules, and folded-postplan contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend SKILL.md and test-design-structure.sh updates to drop retired inventory entries, retarget assert_step2b_drafter_folded_postplan_contract and assert_postplan_thin_fence to python/design_lifecycle.py (or pytest), and assert launcher-mapped authorities instead of bash file contents.
  - From Cursor-Innovation: Add an explicit plan step to retarget structure assertions to `python/design_lifecycle.py`, `python/plan_quality.py`, launcher routing, and CLI stdout contracts; drop greps that require deleted files.
  - From Cursor-dyn-postplan-parity: Update test-design-structure.sh (or test_design_lifecycle.py) to assert the Python design step2b-postplan body preserves the full rc case arms and pause-save REPO threading


### FINDING_11: Retained Step 2b.5 must echo check-size stdout and propagate exit code
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Current `design-step2b5.sh` captures `plan check-size` output but never prints it or exits with `_plan_size_rc`, breaking SKILL Step 2b.5 prompt-side KV parsing. The port must restore stdout and exit-code behavior and bind orchestrator `_plan_size_rc` from the process exit code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In design step2b5 port explicitly echo the LARCH_QUIET_DISABLE=1 check-size stdout to the wrapper stream and exit with the helper rc; add a one-line SKILL.md note that retained Step 2b.5 callers use the Bash fence exit code as _plan_size_rc after capturing stdout.
  - From Cursor-Innovation: Echo check-size stdout to the contract stream and `sys.exit` with the helper rc; add pytest for both behaviors.


### FINDING_12: Gate B settle must invoke postplan as argv, not a scalar executable string
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-postplan-parity
- **Severity**: blocking
- **Concern**: `design-step35-settle.sh` invokes `POSTPLAN_SH` as a single executable (`"$POSTPLAN_SH" --session-env-path ...`). Replacing the default with `python3 .../cli.py design step2b-postplan` without converting to argv form makes Bash look for one executable with spaces, so Gate B and discussion settle fail before `POSTPLAN_RC` parsing; pause exit 11 also breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Restructure settle to call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step2b-postplan` with explicit argv (or keep the launcher-routed `design-step2b-postplan.sh` name). Reserve `DESIGN_STEP35_POSTPLAN_SH` for a single executable test stub only.
  - From Codex-dyn-postplan-parity: Revise the plan to require an argv array for the default CLI command, while preserving DESIGN_STEP35_POSTPLAN_SH as a single-command test override path


### FINDING_13: Ported CLI surface must preserve full common wrapper flags
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Proposed parsers list only part of the common wrapper argv, so launcher-mapped calls that previously accepted flags such as `--mode`, `--step3-review-loop-status`, `--loop-status`, and validator `--outcome` would fail with unknown-argument exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Preserve the full common wrapper parser surface in the shared design runtime and validator-autofix verb, treating unused flags as no-ops while still binding values that affect behavior such as --outcome


### FINDING_14: Postplan port must emit POSTPLAN_STATUS for every non-fatal rc arm
- **Reviewer(s)**: Cursor-dyn-postplan-parity
- **Severity**: important
- **Concern**: Prompt-side binding requires both `POSTPLAN_RC=` and `POSTPLAN_STATUS=` after `DRAFTER_STATUS=succeeded`. Shell always emits `ok` / `validate-failed` / `pause-save` / `plan-size-trigger` / `partition-requested` per arm; the planned rc matrix omits mandatory `POSTPLAN_STATUS=` rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-postplan-parity: Extend the design step2b-postplan port bullets to require POSTPLAN_STATUS= for rc 0 10 11 12 13 matching design-step2b-postplan.sh


### FINDING_15: In-process drafter must propagate fatal postplan emit exit code
- **Reviewer(s)**: Cursor-dyn-postplan-parity
- **Severity**: blocking
- **Concern**: Shell uses exec on postplan so rc 1/2/* abort the drafter fence. An in-process call that returns 0 after printing stderr would let the orchestrator treat a failed emit as success or fall through to inline fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-postplan-parity: Specify that design step2b-drafter returns the postplan verb exit code on fatal arms and does not emit DRAFTER_STATUS=succeeded when postplan fails closed


### FINDING_16: Postplan completion-only and pre-emit pause paths must emit POSTPLAN rows
- **Reviewer(s)**: Cursor-dyn-postplan-parity
- **Severity**: important
- **Concern**: Shell emits `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before exec pause-save for `--write-step2b-completion-only`, `--write-completion-only`, and the normal pre-emit `.pause-requested` gate. `design-step35-settle.sh` keys off those rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-postplan-parity: Add explicit completion-only and pre-emit pause requirements to the postplan port bullets including REPO forwarding on pause-save


### FINDING_17: Validator autofix session rehydration must overlay env before file-only allowlist read
- **Reviewer(s)**: Cursor-dyn-autofix-audit
- **Severity**: important
- **Concern**: Bash seeds orchestrator exports (`DESIGN_TMPDIR`, `SUMMARY_OUTCOME`, `ISSUE_NUMBER`, etc.) before sourcing session-env.sh, overlays file values, then derives binary-found when still unset. A file-only allowlist read drops env-only keys and breaks operator-cancel audit (`OUTCOME=`) and pause-save (`--issue`/`--repo`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-autofix-audit: Match bash order: bind known keys from os.environ defaults, overlay allowlisted session-env.sh exports, then derive CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND when unset; document the required key set.




### FINDING_1: Step 2a omits pause-save short-circuit
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: The Step 2a port drops the terminal pause-save short-circuit when `.pause-requested` exists. After sentinel repair, a pending pause is ignored and `/design` continues into Step 2b instead of saving pause state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add to `design step2a`: after timing mark, if `.pause-requested` exists call `design pause-save` with `--issue` and optional `--repo`; do not emit `POSTPLAN_RC`/`POSTPLAN_STATUS` rows on this path


### FINDING_2: `test-design-structure.sh` grep pins still target retired bash wrappers
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan retargets some folded-postplan guards but leaves multiple `test-design-structure.sh` assertions still grepping deleted wrapper paths (`design-step2a.sh`, `design-step2b-drafter.sh`, `design-step2b-postplan.sh`, `design-step2b5.sh`, and related strings in `approval-gates.md`, `discussion-rounds.md`, `design-step35-settle.md`, and `SKILL.md`). After doc updates name `python/cli.py design step2b-postplan` authorities, `assert_reference_updates`, `assert_behavioral_harness_pins`, `assert_wrapper_contract_pins`, `assert_postplan_thin_fence`, `assert_step2b_drafter_folded_postplan_contract`, and settle site-mapping `contains` rows still fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the scripts/test-design-structure.sh section to retarget assert_reference_updates assert_behavioral_harness_pins the settle.md site-mapping contains rows and the early postplan wrapper contains block to python/design_lifecycle.py or python/cli.py design step2b-postplan wording
  - From Cursor-Pragmatic: Add an explicit checklist in the plan for every `test-design-structure.sh` function that references the retired wrappers, including `assert_reference_updates` Gate B/discussion internal-postplan strings and `design-step35-settle.md` table rows (lines 318-319).
  - From Cursor-Requirements: Add an explicit `test-design-structure.sh` task to retarget `assert_reference_updates()` (and the `design-step35-settle.md` mapping rows at 318-319) to the new Python CLI authority strings


### FINDING_3: Harness still requires on-disk `.sh`/`.md` for launcher-routed retired wrappers
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan deletes five Step 2 `.sh` wrappers but keeps `SKILL.md` launcher fences like `design-run-$PPID.sh design-step2a.sh`, and does not retarget `assert_direct_wrappers_are_executable_and_documented`. After manifest retirement, the harness still requires each cited wrapper to exist as an executable `.sh` with a sibling `.md`, so `make test-design-structure` fails even when `design-run-$PPID.sh` maps those names to Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the `scripts/test-design-structure.sh` section: either exempt launcher-routed retired names from the on-disk `.sh`/`.md` check, or assert launcher `case` mapping plus optional thin docs stubs. Do not delete the `.sh` files until this harness is green.


### FINDING_4: `SKILL.md` Step 2b.5 prose conflicts with echo-and-exit port contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 2b.5 items 2-3 still tell the orchestrator to run `plan check-size` in an inline subshell and bind `_plan_size_rc` from `$?`, while the plan ports `design step2b5` to echo stdout and `sys.exit` with the helper rc. The example fence already calls `design-step2b5.sh`, but the prose conflicts with the port contract. An implementer can bind `_plan_size_rc` from an inner subshell or Bash exit `0` while stdout is empty, breaking hard/partition/drift branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Expand the targeted `SKILL.md` edit: rewrite Step 2b.5 items 2-3 to capture wrapper stdout from the Bash fence and bind `_plan_size_rc` from the fence exit code after the echo-and-exit port.


### FINDING_6: `DRAFTER_STATUS=succeeded` can emit before fatal postplan outcome is known
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Step 2b drafter success row ordering conflicts with the fatal postplan contract. The plan first tells the port to print `DRAFTER_STATUS=succeeded` before running postplan, then says fatal postplan arms must not print that row. A postplan rc 1 or 2 path can emit a false success marker and break the wrapper-row contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Capture the in-process postplan result before emitting wrapper success rows. Emit STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN, DRAFTER_STATUS=succeeded, DRAFTER_VENDOR, and captured postplan output only for nonfatal postplan outcomes. On fatal postplan rc, print diagnostics and return that rc without DRAFTER_STATUS=succeeded.


### FINDING_7: Codex token append narrowed to success-only paths
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Token append is narrowed to Codex success instead of any fresh token sidecar. The current launcher can produce `step2b-drafter-status.txt.token-record` on failed Codex attempts, and the shell wrapper appends it regardless of drafter rc. The planned port can underreport failed Codex drafter usage when it falls back inline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: After every Codex launch attempt, append both token paths whenever the freshly-created non-empty token sidecar exists, independent of drafter rc or structural success. Keep stale-sidecar rejection and nonfatal warning behavior.



### FINDING_1: Step 2b.5 omits pre-check-size pause-save short-circuit
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Step 2b.5 port omits the pre-check-size pause-save short-circuit. A pause during retained Step 2b.5 would run `plan check-size` instead of honoring `.pause-requested` via `design pause-save`, breaking pause/resume at that boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `design step2b5`, before check-size: if `.pause-requested` exists, call `design pause-save` with `--design-tmpdir`, `--issue`, optional `--repo`, and exit (no POSTPLAN rows), matching current Bash `exec` semantics; add pytest coverage


### FINDING_2: In-process drafter postplan omits pinned `--site step2b` and `--snapshot-original`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The folded drafter postplan call omits pinned `--site step2b` and `--snapshot-original` transport. The drafter port calls the in-process `design step2b-postplan` body but does not bind the same argv the Bash wrapper execs today (`--site step2b --snapshot-original` plus transport flags). Without those args, initial Step 2b skips `--snapshot-original`, drift baseline seeding breaks, and Gate B/discussion site mapping can diverge from `design-step35-settle.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `design step2b-drafter` section, require the in-process call to pass exactly `--site step2b`, `--snapshot-original`, `--session-env-path`, `--claude-pid`, and `--plugin-root` (matching current `design-step2b-drafter.sh:304-309` and `test-design-step2b-drafter.sh` argv pins).
  - From Cursor-Requirements: In `design step2b-drafter`, call the in-process postplan body with the same argv semantics as Bash: `--site step2b --snapshot-original` (transport flags optional if env is already rehydrated).


### FINDING_3: `assert_postplan_thin_fence` still greps Bash-only tokens after Python port
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `assert_postplan_thin_fence` retarget keeps Bash-only grep tokens on the Python postplan body. The plan moves the postplan implementation to `python/design_lifecycle.py` but item 5 says to keep `case "${_postplan_rc:-1}" in`, `set +e`, and `${_postplan_out:-}` greps. Those strings will not exist in Python, so `make test-design-structure` fails even when the port is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite `assert_postplan_thin_fence` (and its call site) to assert Python markers instead: delegation to `design postplan-emit --with-plan-size`, pause `REPO` threading, rc arms 0/10/11/12/13/1/2, and `DRIFT_TRIGGER_FIRED` / `BASELINE_PLAN_LINES` still in `python/design_postplan.py`.


### FINDING_4: Postplan rc must flow via `POSTPLAN_RC` rows, not process exit code
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The port must preserve the thin-wrapper rc contract at two layers. Internally, an in-process drafter→postplan call that treats the wrapper return code as 0 will emit `DRAFTER_STATUS=succeeded` on validate-failed / plan-size paths and skip inline-retry / Split routing, because Bash `design-step2b-postplan.sh` prints `POSTPLAN_RC=10|12|13` then exits 0 and `exec` masked that for the drafter. Externally, exiting the drafter process with rc 10, 11, 12, or 13 would make prompt-side orchestration treat validation, pause, plan-size, or partition outcomes as fatal before row routing, contradicting the existing contract that carries those outcomes in `POSTPLAN_RC` / `POSTPLAN_STATUS` rows while the wrapper exits cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Have the shared postplan body return the `design postplan-emit` rc (or parse `POSTPLAN_RC` from captured stdout) to the in-process drafter caller. Document that subprocess callers (settle) may still exit 0 when stdout carries non-zero `POSTPLAN_RC`.
  - From Codex-Generic: Keep process exit 0 for nonfatal postplan outcomes after emitting rows; propagate only fatal postplan failures as nonzero and align the replacement pytest with the existing rc10, rc11, rc12, and rc13 exit-zero contract.


### FINDING_5: Postplan pause-save paths must not return to in-process drafter caller
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Postplan pause-save paths must not return to an in-process drafter caller. Bash uses `exec python3 ... design pause-save` on rc 11 and completion-only pause arms, so control never falls through. A Python port that calls pause-save and returns lets the in-process drafter continue and can double-emit success rows or launch the vendor after pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Match Bash `exec` semantics: after printing `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save`, call pause-save then `sys.exit` with the pause-save rc (or re-raise). Do not return to `design step2b-drafter` on pause paths.




### FINDING_1: Shared postplan helper must call Python entrypoints in-process
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The shared postplan body helper must invoke `design_postplan.postplan_emit_main` and `design_pause.pause_save_main` in-process rather than shelling out to `python/cli.py`. Subprocessing `cli.py design postplan-emit` or the full `design step2b-postplan` wrapper from inside `design step2b-drafter` isolates pause handling in a child process, so rc-11 pause arms cannot `sys.exit` the drafter fence and in-process delegation can return after pause or mis-layer exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement the helper as direct Python entrypoint calls with captured stdout; reserve subprocess use for external drafter launch scripts only.


### FINDING_2: Drafter pre-launch cleanup list underspecified versus Bash
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The drafter pre-launch cleanup list is underspecified relative to Bash. The plan says only "Remove stale Step 2b outputs," but Bash removes `plan.txt`, `plan-summary.md`, all `step2b-drafter-status.txt` sidecars (including `.token-record`), scout manifest globs, and `step2b-drafter-baseline.porcelain` (`design-step2b-drafter.sh:142-156`). Omitting `.token-record` lets a pre-seeded stale sidecar survive into the rc-independent Codex token append and regress `test-design-step2b-drafter` stale-sidecar behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port the exact `rm -f` set from `design-step2b-drafter.sh:142-156` verbatim (or one documented helper) and add pytest that pre-seeds `step2b-drafter-status.txt.token-record` before launch.


### FINDING_3: Missing preserved human success stdout line
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The port omits the preserved human success stdout line. The shell harness asserts `✅ 2b: drafter subprocess succeeded (vendor=... plan_lines=... diff_lines=...)` after plan-review preview (`test-design-step2b-drafter.sh:388`; `design-step2b-drafter.sh:300`). The plan lists preview output but not this line; the pytest replacement list omits it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After structural success, emit the same `printf` success line with `vendor`/`plan_lines`/`diff_lines` before `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN`; add a pytest assertion mirroring the harness.


### FINDING_5: `.step2b-postplan-fallback-used` seeding logic omitted
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Drafter entry must seed `.step2b-postplan-fallback-used` from `.step2b-postplan-inline-retry-done` before vendor launch. The plan says only to write `.step2b-postplan-fallback-used`, but Bash sets it to `true` when `.step2b-postplan-inline-retry-done` exists before vendor launch (`design-step2b-drafter.sh:113-117`). Postplan rc 10 inline-retry gating reads that file; always writing `false` (or omitting the conditional) can re-trigger the one-shot inline retry after a completed retry cycle on resume or re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Port the conditional: if `.step2b-postplan-inline-retry-done` exists write `true`, else `false`, before drafter launch; add a pytest asserting the seed blocks second inline-retry choreography.
  - From Cursor-Requirements: Add an explicit port bullet: on entry, if `.step2b-postplan-inline-retry-done` exists set `.step2b-postplan-fallback-used=true`, else false; mirror bash before pause-save and launch.


### FINDING_8: Codex token append omits sidecar `--input`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The Codex token append plan omits the sidecar input. If implemented literally, `token append-record` and `record-vendor-sidecar` get no `--input` and can return success while appending nothing, silently under-reporting Codex drafter usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add `--input "$DESIGN_TMPDIR/step2b-drafter-status.txt.token-record"` to both token commands and preserve `DESIGN_TMPDIR` for active-ledger recording.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:design step2a
- **Concern**: [SCOPE-REDUCTION] Shared wrapper-runtime must not call design_require_plugin_root before Step 2a sentinel repair. Scenario: Bash design-step2a.sh never validates CLAUDE_PLUGIN_ROOT; it repairs sentinels and writes .completed/step-2a first. A shared entry helper that fails fast on empty/unexpanded CLAUDE_PLUGIN_ROOT changes failure ordering and can block sentinel repair that Bash still performs today.
- **Proposed resolution**: Carve Step 2a out of the generic plugin-root gate: rehydrate env and run sentinel repair exactly first; only call design_require_plugin_root immediately before pause-save or timing mark (matching Bash lines 145-146).




### FINDING_1: Session-env keys must be exported to `os.environ` before in-process Step 2 helpers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The shared wrapper must export rehydrated session keys into `os.environ` before calling in-process `postplan_emit_main` or `pause_save_main`. `plan_quality.py` and `design_postplan.py` read `ISSUE_NUMBER`, `DESIGN_TMPDIR`, and `CLAUDE_PLUGIN_ROOT` from `os.environ` (and subprocess env copies). A local-only overlay without `os.environ` export breaks pause-save (`ISSUE_NUMBER` empty), plan-validate repo-root resolution, and token sidecar subprocesses even when `session-env.sh` was parsed correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After allowlisted session-env parse, write merged defaults into os.environ (same effective surface as Bash source) before any in-process postplan_emit_main or pause_save_main call; add pytest that sets keys only in session-env file and asserts postplan pause arm sees ISSUE_NUMBER.


### FINDING_6: Step 2a timing mark must stay best-effort when plugin root is empty
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The Step 2a plan makes plugin-root validation fatal before the best-effort timing mark. Bash Step 2a repairs sentinels and exits successfully on the non-pause path even when the timing command cannot run because `CLAUDE_PLUGIN_ROOT` is empty. Fatal validation before timing would regress that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep pause-save root validation fatal, but make the non-pause timing mark best-effort: skip timing or ignore root-validation failure before timing while returning success after sentinel repair.


### FINDING_7: Postplan rc 10 inline-retry plan condition is inverted
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The postplan rc 10 inline-retry condition is inverted in the parenthetical. The plan says fallback is not already used while pointing at `.step2b-postplan-fallback-used=true`; implementing that literal condition skips the required first inline retry or repeats the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Change the condition text to .step2b-postplan-fallback-used is absent or not true, matching the Bash != true check.


### FINDING_8: Validator autofix plan must pin required in-process delegation
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The validator autofix plan does not pin the required in-process delegation. The issue asks for an in-process port, but "Call existing plan auto-fix-commands" can be implemented as a subprocess back into `cli.py`, leaving the wrapper body only partially ported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: State that plan validator-autofix calls auto_fix_plan_commands_main(...) directly, captures its stdout and rc in-process, and add the planned pytest assertion for that direct delegation.


### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:design step2b-drafter
- **Concern**: [SCOPE-REDUCTION] Fatal in-process postplan should not sys.exit with raw emit rc 2. Scenario: Bash delegates via exec to design-step2b-postplan.sh which maps postplan_emit rc 2 to wrapper exit 1 (design-step2b-postplan.sh:230-232). Plan says drafter exits with the fatal postplan rc (plan.txt:108), so emit rc 2 would yield process exit 2 and change orchestrator/harness expectations vs today.
- **Proposed resolution**: Reuse the postplan wrapper fatal mapping: on emit rc 1 or 2 exit the drafter fence with 1 after diagnostics; reserve returning raw emit rc for the standalone design step2b-postplan CLI only if needed.



