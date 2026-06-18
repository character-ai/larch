## Goal
Implement issue #4634: [IMPLEMENTING] sh-to-py G5: /design Step-2 drafter + validator bodies — port in-process.

## Implementation Plan
## Plan

## Plan

Use the **standard sh-to-py recipe**.

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection only.

Keep the change scoped to the listed Step 2 and validator bodies plus the tracked reference surfaces called out below.

Preserve:
- `### NEW:` / `### UPDATED:` / `### REWRITTEN:` plan grammar.
- Required final `diff_lines:` trailer.
- Step 2a sentinel repair rules and terminal pause-save short-circuit.
- Step 2b drafter fallback and dirty-tree behavior.
- Postplan rc matrix, `POSTPLAN_RC=` / `POSTPLAN_STATUS=` pairing, and completion marker behavior.
- **Thin-wrapper rc contract:** nonfatal postplan outcomes (`0`, `10`, `12`, `13`) emit rows then exit **0**; only fatal emit failures (`1`, `2`, unexpected) exit non-zero.
- **Fatal emit rc mapping:** emit rc `1` or `2` maps to process exit **1** on drafter and standalone postplan CLI fences (match Bash `design-step2b-postplan.sh`); do not propagate raw emit rc `2` as process exit `2` from the drafter fence.
- Validator autofix escalation and operator-cancel behavior.
- Launcher-owned rehydration and pause-check contract.

**Harness-before-delete ordering:** retarget `scripts/test-design-structure.sh`, reference docs, topology rule, and `_dbg-validator.sh` before manifest retirement or deleting the five launcher-routed Step 2 `.sh` wrappers.

## Files to modify/create

### UPDATED: python/design_lifecycle.py

Add in-process CLI bodies for:
- `design step2a`
- `design step2b-drafter`
- `design step2b-postplan`
- `design step2b5`

Add a shared wrapper-runtime helper that:
- Parses the **full common wrapper argv surface** from the generated Bash wrappers: `--session-env-path`, `--claude-pid`, `--plugin-root`, `--mode`, `--site`, `--snapshot-original`, `--outcome`, `--skip-validate`, `--write-completion-only`, `--include-step2b`, `--write-step2b-completion-only`, `--step3-review-loop-status`, `--loop-status`, plus validator-only flags when reused by `plan validator-autofix`. Unknown flags that existed only as accepted no-ops in Bash must still parse without exit 2; flags that affect behavior (`--outcome`, `--site`, completion-only modes, validator target args) must bind correctly.
- Rehydrates session env in Bash order: seed known keys from `os.environ` defaults first, overlay allowlisted `session-env.sh` exports second, then derive `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` when still unset.
- Loads the session env file with an allowlist parser instead of shell `source`.
- Decodes `write-design-env` `export KEY=shlex.quote(value)` lines, including paths containing spaces; reject or ignore multiline values.
- **After merge, export the effective merged session surface into `os.environ`** (same keys Bash `source` would export) before any in-process helper call. Downstream `postplan_emit_main`, `pause_save_main`, token sidecar subprocesses, and plan-validate repo-root resolution read `ISSUE_NUMBER`, `DESIGN_TMPDIR`, `CLAUDE_PLUGIN_ROOT`, and related keys from `os.environ`; a local-only overlay without export breaks pause-save, validation, and token recording even when `session-env.sh` parsed correctly.
- Applies the same default variables the Bash wrappers set before rehydration.
- Validates `CLAUDE_PLUGIN_ROOT` against empty and literal `${CLAUDE_PLUGIN_ROOT}` via `design_require_plugin_root` **only at call sites that match Bash** (see Step 2a carve-out below).
- Calls `design pause-save` with `--issue` and optional `--repo` at the same checkpoints.

Add a **shared postplan body helper** (used by both `design step2b-postplan` CLI and in-process drafter delegation) that:
- Accepts parsed argv (`--site`, `--snapshot-original`, completion-only modes, transport flags).
- Assumes caller has already exported merged session keys to `os.environ`.
- Runs the full postplan emit / rc-matrix logic by calling **Python entrypoints in-process**, not subprocesses to `python/cli.py`:
  - Invoke `design_postplan.postplan_emit_main(...)` directly for emit / rc-matrix work; capture stdout into the structured result.
  - Invoke `design_pause.pause_save_main(...)` directly on pause arms; then **`sys.exit`** with the pause-save rc.
  - Reserve subprocess use for external drafter launch scripts only (`launch-codex-drafter.sh`, `launch-claude-drafter.sh`).
- Returns a structured result: `(postplan_rc: int, stdout_lines: str, status: str)` where `stdout_lines` includes emit helper output plus `POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows for nonfatal arms.
- On pause arms (`rc 11` and completion-only / pre-emit pause short-circuits): prints `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save`, calls `pause_save_main` with `--design-tmpdir`, `--issue`, optional `--repo`, then **`sys.exit`** with the pause-save rc. **Never returns** to an in-process caller.
- For nonfatal arms `0`, `10`, `12`, `13`: emit rows and return `(rc, stdout, status)` without raising; the CLI wrapper prints stdout and exits **0** (matching Bash thin-wrapper `exec` masking).
- For fatal arms `1`, `2`, unexpected: fail closed; map emit rc `1` and `2` to process exit **1** with the existing Bash diagnostic strings; do not propagate raw emit rc `2` as process exit `2`.

Port `design step2a` exactly:
- **Do not call `design_require_plugin_root` before sentinel repair.** Bash `design-step2a.sh` never validates `CLAUDE_PLUGIN_ROOT` during sentinel prep; rehydrate env and run sentinel repair first.
- Read `run-params.json` with `json`.
- Detect `brainstorm_requested`.
- Repair missing sentinel artifacts only when no conflicting non-sentinel content exists.
- Preserve legacy `NO_SKETCHES_CLASSIFIED_SIMPLE` and `NO_SKETCHES_DEGRADED_HARD` acceptance.
- Write `.completed/step-1c`, `.completed/step-1d`, `.completed/step-1d.5` when applicable, `.completed/step-1d.7`, `.completed/step-1e`, and `.completed/step-2a`.
- Emit the same conflict diagnostic and exit code.
- **Terminal pause-save short-circuit (Bash line 145):** after sentinel repair and `.completed/step-2a` write, if `.pause-requested` exists call `design_require_plugin_root` then `pause_save_main` with `--design-tmpdir`, `--issue`, and optional `--repo`, then exit; do **not** emit `POSTPLAN_RC` / `POSTPLAN_STATUS` rows on this path; skip the timing mark when pausing (match Bash `exec` semantics).
- **Non-pause timing mark (Bash line 146):** call `timing mark "design Step 2a — sentinel prep"` with `LARCH_TIMING_SKILL=design` and **best-effort `|| true` semantics**. Do **not** call `design_require_plugin_root` before timing on this path. When `CLAUDE_PLUGIN_ROOT` is empty or unexpanded, skip timing or swallow timing failure and still exit **0** after sentinel repair (match Bash: sentinel repair succeeds even when timing cannot run).
- Export merged session keys to `os.environ` before pause-save or timing calls.

Port `design step2b-drafter`:
- Keep exact single-line sentinel checks for `approach-synthesis.txt` and `contested-decisions.md`.
- Require empty `dialectic-resolutions.md`.
- Repair `.completed/step-2a` before pause-save.
- **Seed `.step2b-postplan-fallback-used` before vendor launch (Bash lines 113–117):** if `.step2b-postplan-inline-retry-done` exists write `true`, else write `false`. Postplan rc 10 inline-retry gating reads this file; unconditional `false` or omission can re-trigger the one-shot inline retry after a completed retry cycle on resume or re-entry.
- After `design_require_plugin_root`, when `.pause-requested` exists: print whole-line `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save`, then call `pause_save_main` with optional `--repo`; exit without vendor launch.
- Call `timing mark "design Step 2b — plan"` with best-effort semantics before vendor work.
- Select drafter vendor from `LARCH_DESIGN_DRAFTER`, `CODEX_BINARY_FOUND`, and `command -v codex`.
- Validate vendor and Claude model values.
- **Remove stale Step 2b outputs before launch (Bash lines 142–156 verbatim):** delete exactly:
  - `plan.txt`
  - `plan-summary.md`
  - `step2b-drafter-status.txt`
  - `step2b-drafter-status.txt.done`
  - `step2b-drafter-status.txt.dirty-tree`
  - `step2b-drafter-status.txt.meta`
  - `step2b-drafter-status.txt.stderr`
  - `step2b-drafter-status.txt.stderr-tail`
  - `step2b-drafter-status.txt.failure-diag`
  - `step2b-drafter-status.txt.token-record`
  - `step2b-drafter-status.txt.json`
  - `scout-plan-manifest.json`
  - `scout-plan-manifest.json.candidate.*`
  - `scout-plan-manifest.json.filtered.*`
  - `step2b-drafter-baseline.porcelain`
- Require non-empty `feature-description.txt`.
- Capture git baseline porcelain when possible.
- Compose `step2b-drafter-prompt.txt` with the same trusted readability preamble and untrusted file blocks.
- Launch `scripts/launch-codex-drafter.sh` or `scripts/launch-claude-drafter.sh` with the same transport argv.
- **Codex token append (Bash lines 248–260, rc-independent):** after **every** Codex launch attempt, when a freshly-created non-empty `step2b-drafter-status.txt.token-record` exists, port **both** token append paths with the same stale-sidecar ignore rules and non-fatal warning stderr, **independent of drafter rc or structural success**:
  - `token append-record --input "$DESIGN_TMPDIR/step2b-drafter-status.txt.token-record" --tmpdir "$DESIGN_TMPDIR"`
  - `env -u LARCH_TOKEN_LEDGER -u LARCH_TOKEN_SESSION_ID -u IMPLEMENT_TMPDIR -u RESEARCH_TMPDIR -u SESSION_ENV_PATH token record-vendor-sidecar --input "$DESIGN_TMPDIR/step2b-drafter-status.txt.token-record"` (preserve `DESIGN_TMPDIR` for active-ledger recording)
- Check structural success by rc, non-empty `plan.txt`, final `diff_lines: N`, and `PLAN_WRITTEN=true`.
- Preserve dirty-tree detection from sidecar or baseline delta.
- On structural success without dirty tree:
  - Write `.step2b-plan-source=drafter`.
  - Print preview with `[plan-preview] ` prefix.
  - Print human success line before wrapper rows: `✅ 2b: drafter subprocess succeeded (vendor=<vendor> plan_lines=<n> diff_lines=<n>)` (matching Bash line 300).
  - Call the shared postplan body helper with **exact argv semantics matching current Bash `design-step2b-drafter.sh:304-309`**:
    - `--site step2b`
    - `--snapshot-original`
    - `--session-env-path` (from parsed argv)
    - `--claude-pid` (from parsed argv)
    - `--plugin-root` (from parsed argv)
  - **Capture `(postplan_rc, postplan_stdout, postplan_status)` from the helper return before emitting wrapper rows.**
  - **Only on nonfatal postplan outcomes** (`0`, `10`, `12`, `13`): print wrapper rows (`STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1`, `DRAFTER_STATUS=succeeded`, `DRAFTER_VENDOR=...`), then print captured postplan stdout, then exit **0** regardless of `postplan_rc` value (orchestrator binds `_postplan_rc` from `POSTPLAN_RC=` rows, not process exit).
  - **On fatal postplan rc** (`1`, `2`, or other unexpected non-zero): print diagnostics and captured postplan stdout, **do not** print `DRAFTER_STATUS=succeeded`, exit with process rc **1** (map emit rc `2` to exit `1`, matching Bash postplan wrapper); do not fall through to inline fallback.
  - **On pause postplan path:** helper `sys.exit`s after pause-save; drafter must not continue or double-emit success rows.
- On dirty-tree: write `dirty-tree-detected.env`, print `DRAFTER_STATUS=dirty-tree`, and do not run postplan.
- On failure: clear stale summary/scout manifests, write `.step2b-plan-source=inline`, write fallback log, append run-log warning, and return to inline drafting.

Port `design step2b-postplan`:
- Validate and canonicalize `DESIGN_TMPDIR`.
- Preserve mutual exclusion for completion-only modes.
- Implement `--write-step2b-completion-only`.
- Implement `--write-completion-only` and `--include-step2b`.
- Delegate emit/rc-matrix work to the shared postplan body helper (in-process `postplan_emit_main` / `pause_save_main`).
- For every pause short-circuit (`--write-step2b-completion-only`, `--write-completion-only`, and normal pre-emit pause): print `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save`, then call `pause_save_main` with optional `--repo`, then **`sys.exit`** (match Bash `exec` semantics; never return).
- Honor pause-save before postplan emit on the normal emit path (helper handles pre-emit pause).
- Clear scout manifests when `--site` is not `step2b`.
- Call `postplan_emit_main` with `--with-plan-size`, adding `--snapshot-original` only for initial Step 2b (`--site step2b` or empty site).
- Print postplan helper stdout before wrapper rows on CLI paths.
- Preserve rc handling with **both** `POSTPLAN_RC=` and `POSTPLAN_STATUS=` on every non-fatal arm:
  - `0` / `ok`: write `.completed/step-2b.5`, and `.completed/step-2b` for initial Step 2b.
  - `10` / `validate-failed`: read allowlisted validation keys from `.design-postplan-emit-result.env` without sourcing it; when drafter-sourced and no dirty recovery and `.step2b-postplan-fallback-used` is **absent or not `true`** (match Bash `!= true` check), perform the full inline-retry choreography exactly once:
    - write `.step2b-postplan-inline-retry-done`
    - set `.step2b-postplan-fallback-used=true`
    - set `.step2b-plan-source=inline`
    - remove `plan-summary.md` and scout manifests
    - print `SCOUT_STALE_CLEARED=true`
    - write `.step2b-postplan-inline-retry-pending`
    - print `**⚠ 2b: drafter plan failed postplan validation — re-entering inline drafting once**`
    - emit validation KV rows when present
  - `11` / `pause-save`: print pause rows, then `sys.exit` via pause-save (never return).
  - `12` / `plan-size-trigger`: mark Step 2b complete and emit plan-size trigger rows.
  - `13` / `partition-requested`: mark Step 2b complete and emit partition rows.
  - `1`, `2`, and unexpected rc: fail closed with the existing diagnostics; map emit rc `1` and `2` to process exit **1**.
- **CLI subprocess contract:** after printing rows for rc `0`, `10`, `12`, `13`, exit **0**; only fatal rc values exit non-zero (always **1** for emit rc `1`/`2`).

Port `design step2b5` as the retained standalone check:
- After rehydration and `design_require_plugin_root`, **before** check-size: if `.pause-requested` exists, call `pause_save_main` with `--design-tmpdir`, `--issue`, optional `--repo`, then exit (no `POSTPLAN_*` rows; match Bash `exec` semantics at `design-step2b5.sh:85`).
- Run `plan check-size --design-tmpdir` with `LARCH_QUIET_DISABLE=1`.
- **Echo the captured stdout** to the wrapper stream so prompt-side KV parsing works.
- **`sys.exit` with the helper rc unchanged** so the Bash fence exit code binds `_plan_size_rc`.

### UPDATED: python/plan_quality.py

Add `plan validator-autofix`.

Move the wrapper body from `design-step-validator-autofix.sh` into this verb:
- Parse the full common wrapper argv surface plus validator-specific flags: `--validator-target-file`, `--validate-log-file`, defect counts, skipped counts, unsafe token counts, and `--operator-cancel`.
- Rehydrate with Bash order: `os.environ` defaults, allowlisted `session-env.sh` overlay, then derive `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` when unset; **export merged keys to `os.environ`** before in-process work. Required keys include `DESIGN_TMPDIR`, `SUMMARY_OUTCOME`, `ISSUE_NUMBER`, `REPO`, and other orchestrator exports used by pause-save and operator-cancel audit.
- Honor pause-save before work.
- Preserve Step 5c default target selection.
- Compute the same cycle key from site, target basename, defect counts, and validation log hash.
- Preserve `.plan-command-autofix-*.attempted` cycle cap.
- Call **`auto_fix_plan_commands_main(...)` directly in-process** (not a subprocess to `python/cli.py plan auto-fix-commands`); capture its stdout and rc in-process.
- Normalize status exactly as the shell wrapper does.
- Append the ok-path `validate-plan-commands(auto-fixed:...)` warning row only when the helper rc is zero and status is `ok`.
- Remove the attempted sentinel when helper failure or run-log append failure invalidates the ok path.
- Print `AUTOFIX_STATUS`, `FIXED_BY`, and `ORIGINAL_VALIDATE_LOG_FILE`.
- Record stall-recovery escalation for `exhausted`, `failed`, `unavailable`, and `skipped-cycle-cap`.
- Preserve operator-cancel sentinel, chat sidecar, and run-log audit.

### UPDATED: python/cli.py

Register:
- `("design", "step2a")`
- `("design", "step2b-drafter")`
- `("design", "step2b-postplan")`
- `("design", "step2b5")`
- `("plan", "validator-autofix")`

Add the new design verbs to `_DESIGN_LIFECYCLE_STDOUT_KEYS`.

Add `plan validator-autofix` to machine stdout keys.

### UPDATED: python/session_env.py

Update `_design_run_launcher_text` / generated `design-run-$PPID.sh`.

For these retired wrapper names, exec the Python CLI verb directly with launcher-supplied transport flags **and forward the caller argv tail**:
- `design-step2a.sh` → `exec python3 "$PLUGIN_ROOT/python/cli.py" design step2a --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
- `design-step2b-drafter.sh` → `exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b-drafter --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
- `design-step2b-postplan.sh` → `exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
- `design-step2b5.sh` → `exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b5 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
- `design-step-validator-autofix.sh` → `exec python3 "$PLUGIN_ROOT/python/cli.py" plan validator-autofix --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`

Keep the existing script exec fallback for unported design wrappers.

### UPDATED: skills/design/scripts/design-step35-settle.sh

Replace the default postplan invocation with an **argv array**, not a scalar executable string:
- Default: `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" --plugin-root "$CLAUDE_PLUGIN_ROOT" --site "$POSTPLAN_SITE" "$@"` tail as needed.
- Keep `DESIGN_STEP35_POSTPLAN_SH` only as a **single-executable** test override stub path, not a multi-word CLI command string.

### UPDATED: skills/design/scripts/design-step35-settle.md

Update postplan references from `design-step2b-postplan.sh` to `python/cli.py design step2b-postplan`.

Update the site-mapping table rows (`gate-b`, `gate-a`, `discussion-round2`) to name `python/cli.py design step2b-postplan --site ...` as the internal authority.

Update marker-ownership and test-seam prose to match the CLI default and argv-array settle call.

### UPDATED: skills/design/SKILL.md

Update Step 2 references to say the launcher routes the retired Step 2 wrapper names to Python CLI verbs.

Do not rewrite the whole skill.

Target only:
- Wrapper contract inventory near the top: **remove retired `.sh` inventory entries**; name the Python authorities instead.
- Step 2a command text (launcher fence may keep `design-step2a.sh`; behavior owned by `python/cli.py design step2a`; note Step 2a skips plugin-root validation until after sentinel repair; non-pause timing is best-effort).
- Step 2b drafter description and delegated postplan authority: `python/cli.py design step2b-drafter` owns folded prelude; in-process shared postplan helper calling `postplan_emit_main` / `pause_save_main` is the delegated authority with pinned `--site step2b --snapshot-original` transport; human success line and wrapper success rows emit only after nonfatal postplan capture; orchestrator binds `_postplan_rc` from `POSTPLAN_RC=` rows, not drafter process exit; fatal emit rc `1`/`2` exits drafter with process rc `1`.
- Terminal postplan fence text: launcher `design-step2b-postplan.sh` maps to `python/cli.py design step2b-postplan`.
- **Step 2b.5 items 2–3:** rewrite so the orchestrator runs the launcher fence (`design-step2b5.sh`, mapped to `python/cli.py design step2b5`), captures **the fence stdout** into `_plan_size_out`, and binds `_plan_size_rc` from **the Bash fence exit code** (`$?` after the fence returns), not from an inner `plan check-size` subshell. Remove prose that instructs running `plan check-size` inline in a nested subshell.
- Shared validator autofix block.
- Any statements that say `design-step-validator-autofix.sh` owns behavior.

Keep existing launcher-form examples if the launcher maps them to Python.

Replace direct behavior ownership references with:
- `python/cli.py design step2a`
- `python/cli.py design step2b-drafter`
- `python/cli.py design step2b-postplan`
- `python/cli.py design step2b5`
- `python/cli.py plan validator-autofix`

Update folded-postplan SKILL prose to require postplan-result capture before `DRAFTER_STATUS=succeeded` and to state that nonfatal postplan rc values (`10`, `12`, `13`) still exit the drafter fence **0** while carrying outcome in stdout rows.

### UPDATED: skills/design/references/approval-gates.md

Update references to `design-step2b-postplan.sh` completion-only and Gate B postplan ownership.

Point them to `python/cli.py design step2b-postplan` through the launcher or direct CLI wording consistent with `SKILL.md`.

Replace Gate B internal-postplan mapping strings that grep `design-step35-settle.sh` calls `design-step2b-postplan.sh --site gate-b` with launcher-form settle plus `python/cli.py design step2b-postplan --site gate-b` internal authority wording.

### UPDATED: skills/design/references/decompose-panel.md

Update non-exiting Split return instructions that mention `design-step2b-postplan.sh --write-completion-only`.

Point them to `python/cli.py design step2b-postplan --write-completion-only` (launcher `design-step2b-postplan.sh` still valid as the fence name).

### UPDATED: skills/design/references/discussion-rounds.md

Update discussion settle prose that says `design-step35-settle.sh` delegates to `design-step2b-postplan.sh`.

Name `python/cli.py design step2b-postplan` as the internal authority for `gate-a` and `discussion-round2` site mapping.

### UPDATED: .claude/rules/topology-generation.md

Replace the stale `paths:` entry `skills/design/scripts/design-step2a.sh` with `python/design_lifecycle.py` as the Step 2a runtime authority for topology generation.

### UPDATED: skills/design/scripts/_dbg-validator.sh

Retarget the debug helper to invoke `python3 "$ROOT/python/cli.py" plan validator-autofix` with the same test stubs instead of the retired `design-step-validator-autofix.sh` path.

Alternatively delete the helper if it becomes obsolete after pytest coverage lands; prefer retarget over deletion if the script remains useful for local debugging.

### UPDATED: scripts/test-design-structure.sh

Update structure assertions for the port. Apply this **explicit retarget checklist** so `make test-design-structure` stays green after doc and file retirement:

1. **`assert_direct_wrappers_are_executable_and_documented`**
   - Exempt launcher-routed retired names (`design-step2a.sh`, `design-step2b-drafter.sh`, `design-step2b-postplan.sh`, `design-step2b5.sh`, `design-step-validator-autofix.sh`) from the on-disk executable `.sh` + sibling `.md` requirement.
   - Add a companion assertion that the generated `design-run-$PPID.sh` `case` maps each retired name to the correct `python/cli.py` verb with `"$@"` forwarding.
   - Keep the on-disk `.sh`/`.md` requirement for all other SKILL.md fence wrappers.

2. **`assert_wrapper_contract_pins`**
   - Remove `contains` pins against retired `design-step2a.sh` and `design-step2b-postplan.sh`.
   - Retarget Step 2a / postplan contract pins to `python/design_lifecycle.py` (or CLI registry strings).

3. **`assert_reference_updates`**
   - Retarget Gate B mapping: `design-step35-settle.sh` calls `python/cli.py design step2b-postplan --site gate-b` internally (not `design-step2b-postpostplan.sh`).
   - Retarget discussion mapping: `gate-a` and `discussion-round2` both map to `python/cli.py design step2b-postplan --site discussion-round2` internally.
   - Remove or invert pins that require stale inline transport args to `design-step2b-postplan.sh`.

4. **`assert_behavioral_harness_pins`**
   - Replace `contains "$SKILL_MD" 'design-step2b-postplan.sh'` with authority wording for `python/cli.py design step2b-postplan`.

5. **`assert_postplan_thin_fence`**
   - Retarget call site from `design-step2b-postplan.sh` to `python/design_lifecycle.py` (postplan body / `design step2b-postplan` implementation).
   - **Remove Bash-only grep tokens** (`set +e`, `$?`, `${_postplan_out:-}`, `case "${_postplan_rc:-1}" in`, Bash `case` arms) that will not exist in Python.
   - **Replace with Python contract pins:**
     - In-process delegation to `postplan_emit_main` / `design postplan-emit --with-plan-size` (including `--snapshot-original` when site is `step2b`); no subprocess to `cli.py design step2b-postplan` from inside drafter.
     - In-process `pause_save_main` on pause arms with `sys.exit` after pause rows.
     - Shared helper or inline rc handling for arms `0`, `10`, `11`, `12`, `13`, `1`, `2` (grep Python literals such as `POSTPLAN_RC=`, `POSTPLAN_STATUS=`, rc comparisons or mapping dict keys).
     - Fatal emit rc `1`/`2` maps to process exit `1` (grep mapping, not raw emit rc `2` as exit `2`).
     - `os.environ` export after session-env merge before in-process postplan/pause calls.
     - Pause `REPO` threading: `--repo` forwarding when `REPO` set.
     - Nonfatal rc `0`/`10`/`12`/`13` CLI exit **0** after row emission.
   - Keep drift pins against `python/design_postplan.py`: `DRIFT_TRIGGER_FIRED`, `BASELINE_PLAN_LINES`.

6. **`assert_step2b_drafter_folded_postplan_contract`**
   - Retarget SKILL.md ownership pins from `design-step2b-drafter.sh` / `design-step2b-postplan.sh` transport strings to `python/cli.py design step2b-drafter` and in-process shared postplan helper authority wording.
   - Retarget delegated postplan argv pin to require `--site step2b`, `--snapshot-original`, and transport flags (matching current Bash lines 304–309).
   - Retarget embedded Python section terminal-postplan fence grep from `design-step2b-postplan.sh --site step2b --snapshot-original` to launcher fence that maps to `python/cli.py design step2b-postplan --site step2b --snapshot-original`.
   - Move drafter sentinel / repair / pause / timing / launch order pins from `design-step2b-drafter.sh` to `python/design_lifecycle.py`.
   - Add pin for exact pre-launch cleanup paths (lines 142–156).
   - Add pin for human success line `✅ 2b: drafter subprocess succeeded`.
   - Add pin for `.step2b-postplan-fallback-used` conditional seeding from `.step2b-postplan-inline-retry-done`.
   - Remove pins that require `design-step2b-drafter.sh` not to source prelude (prelude is in-process).
   - Add pin that `DRAFTER_STATUS=succeeded` is emitted only after nonfatal in-process postplan capture.
   - Add pin that drafter exits **0** on nonfatal postplan rc `10`/`12`/`13` while stdout carries `POSTPLAN_RC=` rows.
   - Add pin that fatal emit rc `2` exits drafter with process rc `1`.
   - Add pin that Step 2a does not call `design_require_plugin_root` before sentinel repair.
   - Add pin that Step 2a non-pause timing is best-effort without fatal plugin-root validation.

7. **`design-step35-settle.md` harness pins** (where referenced from structure tests)
   - Retarget site-mapping `contains` rows at the settle doc table to `python/cli.py design step2b-postplan --site ...`.
   - Retarget test-seam default from `skills/design/scripts/design-step2b-postplan.sh` to the argv-array CLI default.

8. **General**
   - Assert mapped postplan calls preserve `--site` / `--snapshot-original`; assert validator mapping preserves sample validator flags.
   - Assert `SKILL.md` names the new authorities and no longer inventories deleted wrappers as live contract owners.
   - Assert `design-step35-settle.sh` calls the postplan CLI by default via argv form.
   - Keep launcher-owned rehydration and pause-check assertions for unported wrappers.

**Do not delete** the five launcher-routed `.sh` files until this harness is green.

### UPDATED: python/test_design_lifecycle.py

Add pytest coverage replacing `test-design-step2b-drafter.sh` and Step 2a shell checks:
- Step 2a repairs missing sentinels and completion markers.
- Step 2a refuses conflicting non-sentinel artifacts.
- Step 2a preserves brainstorm completion marker behavior.
- Step 2a emits timing mark for sentinel prep when not pausing and plugin root is valid.
- **Step 2a timing best-effort:** when `CLAUDE_PLUGIN_ROOT` is empty on the non-pause path, sentinel repair still succeeds exit **0**; timing is skipped or failure is swallowed; no fatal plugin-root validation before timing.
- **Step 2a pause short-circuit:** when `.pause-requested` exists after sentinel repair, calls `pause_save_main` with `--issue` and optional `--repo`, exits without `POSTPLAN_*` rows, and skips timing mark.
- **Step 2a plugin-root ordering:** sentinel repair completes even when `CLAUDE_PLUGIN_ROOT` is empty; plugin-root validation runs only on the pause-save path, not before non-pause timing.
- **Session-env `os.environ` export:** keys set only in `session-env.sh` (e.g. `ISSUE_NUMBER`) are visible to in-process `pause_save_main` / `postplan_emit_main` after rehydration.
- Session-env parser decodes shlex-quoted `DESIGN_TMPDIR` paths containing spaces.
- Step 2b prelude guard blocks malformed sentinel artifacts before pause or launch.
- Step 2b repairs `.completed/step-2a` before pause-save.
- Pre-draft pause prints `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before pause-save.
- **Fallback-used seeding:** when `.step2b-postplan-inline-retry-done` exists before launch, `.step2b-postplan-fallback-used=true` is written; rc 10 inline-retry choreography does not re-fire on a second pass.
- **Pre-launch cleanup:** pre-seeded stale `step2b-drafter-status.txt.token-record` is removed before launch; post-failed Codex launch only appends from freshly-created sidecar.
- Drafter default vendor selection prefers Codex when present.
- Claude vendor uses `LARCH_DESIGN_PLAN_MODEL`.
- Invalid vendor/model falls back without launching.
- Drafter success calls postplan once in-process with pinned `--site step2b --snapshot-original`; on nonfatal postplan prints human success line then wrapper rows **after** postplan capture; propagates fatal postplan as process exit **1** **without** `DRAFTER_STATUS=succeeded`.
- **Fatal emit rc mapping:** emit rc `2` from in-process postplan exits drafter with process rc `1`, not `2`.
- **Human success stdout:** after structural success, emits `✅ 2b: drafter subprocess succeeded (vendor=... plan_lines=... diff_lines=...)` before `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN`.
- **Drafter nonfatal postplan rc contract:** rc `10`, `12`, `13` paths exit **0** with `POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows in stdout; orchestrator-style parsing binds rc from rows, not process exit.
- Drafter failure clears stale summary/scout output and writes fallback log.
- Dirty-tree detection writes `dirty-tree-detected.env` and skips postplan.
- **Codex token append on failed drafter rc:** when a fresh non-empty token sidecar exists after a failed Codex attempt, both token append paths still run with `--input` pointing at `step2b-drafter-status.txt.token-record`.
- Postplan rc 10 triggers exactly one inline retry when `.step2b-postplan-fallback-used` is absent or not `true`, with full sentinel/stdout choreography.
- Postplan rc 11 on pre-emit, completion-only, and normal emit paths emits pause rows and forwards `--repo`; **`sys.exit`s via in-process `pause_save_main`**; does not return to in-process drafter caller.
- Postplan rc 12 and rc 13 preserve completion marker behavior and `POSTPLAN_STATUS=` rows; CLI exits **0**.
- Fatal postplan rc values fail closed with non-zero exit **1** for emit rc `1`/`2`.
- **`design step2b5` pause short-circuit:** when `.pause-requested` exists before check-size, calls pause-save with `--issue` and optional `--repo`, exits without `POSTPLAN_*` rows and without running check-size.
- `design step2b5` echoes check-size stdout and exits with helper rc when not pausing.

Use temporary fake plugin roots and fake launcher scripts.

Do not retain retired script path literals in fixtures except manifest entries.

### UPDATED: python/test_plan_quality.py

Add pytest coverage replacing `test-design-step-validator-autofix.sh`:
- Exhausted autofix records escalation evidence.
- Operator cancel writes sentinel, chat sidecar, and run-log audit with env-overlay rehydration.
- Ok autofix appends exactly one Warnings row with original validation log evidence.
- Nonzero helper rc with `AUTOFIX_STATUS=ok` normalizes to `failed`.
- Run-log append failure normalizes ok helper output to `failed`.
- Cycle cap returns `skipped-cycle-cap`.
- Step 5c default target is `composed-plan.md`.
- Pause-save path short-circuits before autofix.
- **In-process delegation:** `plan validator-autofix` calls `auto_fix_plan_commands_main` directly (mock/spy), not `subprocess` to `cli.py plan auto-fix-commands`.

Keep existing `plan auto-fix-commands` tests unchanged.

### UPDATED: python/test_design_cli_ports.py

Add expected registry entries for the new design verbs.

Add `plan validator-autofix` coverage if this file remains the registry smoke-test location for machine stdout surfaces.

### UPDATED: python/test_session_env.py

Update launcher tests:
- Assert the generated launcher maps retired Step 2 and validator wrapper names to Python CLI commands with `"$@"` forwarding.
- Assert sample caller flags survive for postplan (`--site`, `--snapshot-original`) and validator autofix (`--validator-target-file`, defect-count args).
- Assert existing unported wrapper names still fall back to `skills/design/scripts/$script`.
- Assert invalid script names are still rejected.

### UPDATED: python/checks.py

Retarget relevant-check mappings:
- Map `python/design_lifecycle.py` and `python/test_design_lifecycle.py` to `test-design-step2b-drafter`, `test-design-driver`, and Step 2 lifecycle harness replacements.
- Map `python/plan_quality.py` and `python/test_plan_quality.py` to `test-design-step-validator-autofix`.
- Remove retired script and retired test paths from active mappings.
- Keep launch-codex-drafter and parse-drafter-output mappings for their live files.

### UPDATED: Makefile

Retarget:
- `test-design-step2b-drafter` to the new pytest selection.
- `test-design-step-validator-autofix` to the new pytest selection.

Do not leave Make targets calling deleted `.sh` harnesses.

### UPDATED: skills/design/scripts/test-auto-fix-plan-commands.sh

Replace the grep that requires `design-step-validator-autofix.sh` to call `plan auto-fix-commands`.

Assert the new `python/plan_quality.py` CLI path contains or exercises `auto_fix_plan_commands_main` through `plan validator-autofix` via **in-process** delegation.

Prefer moving this assertion into pytest if the shell harness becomes obsolete.

### UPDATED: python/migrated-scripts.tsv

Append retired paths with `#3692` **only after** reference retargeting and `make test-design-structure` are green:
- `skills/design/scripts/design-step2a.sh`
- `skills/design/scripts/design-step2a.md`
- `skills/design/scripts/design-step2b-drafter.sh`
- `skills/design/scripts/design-step2b-drafter.md`
- `skills/design/scripts/test-design-step2b-drafter.sh`
- `skills/design/scripts/test-design-step2b-drafter.md`
- `skills/design/scripts/design-step2b-postplan.sh`
- `skills/design/scripts/design-step2b-postplan.md`
- `skills/design/scripts/design-step2b-prelude.sh`
- `skills/design/scripts/design-step2b-prelude.md`
- `skills/design/scripts/design-step2b5.sh`
- `skills/design/scripts/design-step2b5.md`
- `skills/design/scripts/design-step-validator-autofix.sh`
- `skills/design/scripts/design-step-validator-autofix.md`
- `skills/design/scripts/test-design-step-validator-autofix.sh`
- `skills/design/scripts/test-design-step-validator-autofix.md`

Update tracked references in `.claude/rules/topology-generation.md` and `skills/design/scripts/_dbg-validator.sh` **before** relying on manifest retirement so `make lint-retired-scripts` stays green.

### UPDATED: docs/python-migration.md

Add a short G5 decision-log note:
- Step 2 drafter, prelude, postplan, Step 2a, Step 2b.5, and validator-autofix bodies now run in-process.
- The design launcher maps the retired wrapper names to CLI verbs with `"$@"` forwarding to preserve launcher-owned session rehydration and caller flags.
- Shared postplan helper calls `postplan_emit_main` and `pause_save_main` in-process (not subprocess to `cli.py`); rehydration exports merged session keys to `os.environ` before those calls; preserves thin-wrapper rc contract: nonfatal outcomes in stdout rows with process exit 0; fatal emit rc `1`/`2` maps to process exit 1; pause paths `sys.exit` after pause-save.
- Structure harness exempts launcher-routed retired names from on-disk wrapper checks.
- The retired files are manifest-listed after reference retargeting and harness green.

### REWRITTEN: skills/design/scripts/design-step2a.sh

Delete this retired Bash file **after** `make test-design-structure` is green and pytest replacements pass.

### REWRITTEN: skills/design/scripts/design-step2a.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/design-step2b-drafter.sh

Delete this retired Bash file **after** harness and pytest replacements pass.

### REWRITTEN: skills/design/scripts/design-step2b-drafter.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/test-design-step2b-drafter.sh

Delete this retired shell harness after pytest replacement lands.

### REWRITTEN: skills/design/scripts/test-design-step2b-drafter.md

Delete this retired harness doc.

### REWRITTEN: skills/design/scripts/design-step2b-postplan.sh

Delete this retired Bash file **after** harness and pytest replacements pass.

### REWRITTEN: skills/design/scripts/design-step2b-postplan.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/design-step2b-prelude.sh

Delete this retired Bash file.

### REWRITTEN: skills/design/scripts/design-step2b-prelude.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/design-step2b5.sh

Delete this retired Bash file after the Python standalone check is covered.

### REWRITTEN: skills/design/scripts/design-step2b5.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/design-step-validator-autofix.sh

Delete this retired Bash file after pytest replacement lands.

### REWRITTEN: skills/design/scripts/design-step-validator-autofix.md

Delete this retired doc file.

### REWRITTEN: skills/design/scripts/test-design-step-validator-autofix.sh

Delete this retired shell harness after pytest replacement lands.

### REWRITTEN: skills/design/scripts/test-design-step-validator-autofix.md

Delete this retired harness doc.

## Edge cases

- **Session env parsing:** Do not execute shell. Parse only allowlisted `export KEY=value` and `KEY=value` lines. Decode shlex-quoted values from `write-design-env`. Reject or ignore multiline values.
- **Env overlay order:** Seed orchestrator exports from `os.environ`, then overlay file exports; do not use file-only reads for validator autofix or Step 2 verbs.
- **`os.environ` export:** After merge, write effective session keys into `os.environ` before any in-process `postplan_emit_main`, `pause_save_main`, or `auto_fix_plan_commands_main` call.
- **Step 2a plugin-root carve-out:** Do not call `design_require_plugin_root` before sentinel repair.
- **Step 2a pause:** Terminal pause-save after sentinel repair validates plugin root then pause-saves; no `POSTPLAN_*` rows; timing mark skipped on pause path (Bash `exec` semantics).
- **Step 2a non-pause timing:** Best-effort only; no fatal plugin-root validation before timing; empty root still exits **0** after sentinel repair.
- **Step 2b.5 pause:** Pre-check-size pause-save when `.pause-requested` exists; no `POSTPLAN_*` rows; do not run check-size (Bash `exec` semantics).
- **Pause ordering:** Step 2b must repair `.completed/step-2a` before pause-save.
- **Pre-draft pause rows:** Drafter and postplan pause short-circuits must emit `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save` before pause-save.
- **Postplan pause non-return:** After pause rows on rc 11 or completion-only pause paths, in-process `pause_save_main` then `sys.exit`; in-process drafter must not continue.
- **In-process postplan delegation:** Shared helper must not subprocess `cli.py design postplan-emit` or `cli.py design step2b-postplan` from inside drafter; subprocess pause would isolate rc-11 and break `sys.exit` semantics.
- **Fatal emit rc mapping:** Emit rc `1` and `2` map to process exit **1** on drafter and postplan CLI fences; do not surface raw emit rc `2` as process exit `2`.
- **Fallback-used seeding:** Seed from `.step2b-postplan-inline-retry-done` before launch, not unconditionally on entry.
- **Inline-retry gate:** Trigger rc 10 choreography only when `.step2b-postplan-fallback-used` is absent or not `true` (Bash `!= true`).
- **Pre-launch cleanup completeness:** Omitting `.token-record` or other status sidecars lets stale artifacts survive into rc-independent token append.
- **Sentinel exactness:** `NO_SKETCHES` and `NO_CONTESTED_DECISIONS` must be exact one-line files.
- **Drafter wrapper-row ordering:** Capture in-process postplan rc/stdout before emitting `DRAFTER_STATUS=succeeded`; emit human success line before wrapper rows.
- **Drafter postplan argv:** In-process delegation must pass `--site step2b --snapshot-original` plus transport flags so drift baseline seeding matches Bash.
- **Thin-wrapper rc layering:** Shared postplan helper returns rc to in-process caller; CLI subprocess exits 0 for nonfatal rc `0`/`10`/`12`/`13` after printing rows; orchestrator binds `_postplan_rc` from stdout rows, not drafter fence exit code on those paths.
- **Codex token sidecar:** Append tokens with explicit `--input` whenever a fresh non-empty sidecar exists after any Codex launch, not only on structural success.
- **Drafter dirty tree:** Any confirmed baseline delta blocks fallback and writes recovery state.
- **Postplan rc 10:** Inline retry happens once only for drafter-sourced plans when `.step2b-postplan-fallback-used` is absent or not `true`.
- **Fatal postplan in drafter:** In-process drafter must exit process rc **1** on fatal emit; never emit success rows on failed emit.
- **Completion-only modes:** Completion markers alone do not prove postplan validation success.
- **Launcher argv forwarding:** `"$@"` must preserve `--site`, `--snapshot-original`, completion-only flags, and validator args.
- **Harness vs deletion:** Exempt launcher-routed retired names from on-disk wrapper checks before deleting `.sh` files.
- **Settle argv form:** Gate B settle must not treat a multi-word CLI command as one executable.
- **Step 2b.5 stdout/rc:** Echo check-size stdout and exit with helper rc; orchestrator binds `_plan_size_rc` from the **fence** exit code, not an inner subshell.
- **Validator in-process:** `plan validator-autofix` must call `auto_fix_plan_commands_main` directly, not subprocess `cli.py`.
- **Validator target safety:** `plan auto-fix-commands` still enforces target under `DESIGN_TMPDIR`.
- **Retired path literals:** Avoid retired path literals in new tests except manifest entries; retarget topology rule and debug helper before manifest append.

## Failure modes

- **CLI registry drift:** New verbs missing from machine stdout keys can corrupt prompt parsing.
- **Launcher drift:** If `design-run-$PPID.sh` does not map retired names or drops `"$@"`, Step 2 fails after file deletion.
- **Structure harness drift:** Deleting launcher-routed `.sh` files before `assert_direct_wrappers_are_executable_and_documented` exemption breaks CI; grepping Bash-only tokens in `assert_postplan_thin_fence` breaks CI after Python port.
- **Missing `os.environ` export:** Local-only session overlay breaks pause-save `ISSUE_NUMBER`, plan-validate repo-root resolution, and token sidecar subprocesses.
- **Subprocess postplan in drafter:** Shelling out to `cli.py` for postplan or pause-save isolates rc-11 in a child process; drafter can return after pause or mis-layer exit codes.
- **Subprocess validator autofix:** Shelling out to `cli.py plan auto-fix-commands` leaves the wrapper only partially ported and breaks env continuity.
- **False drafter success rows:** Emitting `DRAFTER_STATUS=succeeded` before postplan capture breaks orchestrator binding on fatal emit rc.
- **Raw emit rc 2 propagation:** Exiting drafter with process rc `2` on emit rc `2` breaks harness/orchestrator expectations vs Bash postplan wrapper exit `1`.
- **Process-exit rc confusion:** Exiting drafter with rc `10`/`12`/`13` breaks prompt-side routing that expects exit 0 plus `POSTPLAN_RC=` rows.
- **Step 2a timing regression:** Fatal plugin-root validation before best-effort timing blocks successful sentinel repair when root is empty.
- **Pause fall-through:** Returning from postplan pause-save to in-process drafter can double-emit success rows or launch vendor after pause.
- **Missing snapshot-original:** Drafter in-process postplan without `--snapshot-original` breaks drift baseline seeding on initial Step 2b.
- **Token under-reporting:** Gating Codex token append on structural success, omitting `--input`, or leaving stale `.token-record` before launch undercounts failed Codex drafter usage.
- **Inline-retry re-fire:** Unconditional `.step2b-postplan-fallback-used=false` on drafter entry re-triggers rc 10 choreography after a completed retry cycle.
- **Inverted inline-retry condition:** Treating `.step2b-postplan-fallback-used=true` as the trigger gate skips the first retry or repeats the wrong branch.
- **Step 2a ordering regression:** Calling `design_require_plugin_root` before sentinel repair blocks repair when plugin root is unset, diverging from Bash.
- **Result env drift:** Postplan rc 10 parsing must not source `.design-postplan-emit-result.env`.
- **Missing POSTPLAN_STATUS:** Omitting status rows breaks orchestrator binding after `DRAFTER_STATUS=succeeded`.
- **Missing human success line:** Omitting `✅ 2b: drafter subprocess succeeded` breaks harness parity and operator visibility.
- **Run-log append failure:** Validator autofix ok path must normalize to failed when audit append fails.
- **Manifest drift:** `make lint-retired-scripts` fails when topology rule or `_dbg-validator.sh` still reference retired paths.

## Testing strategy

Run:
- `python3 -m pytest python/test_design_lifecycle.py`
- `python3 -m pytest python/test_plan_quality.py`
- `python3 -m pytest python/test_session_env.py`
- `python3 -m pytest python/test_design_cli_ports.py`
- `make test-design-step2b-drafter`
- `make test-design-step-validator-autofix`
- `make test-check-plan-size`
- `make test-design-postplan-emit`
- `make test-design-structure`
- `make lint-retired-scripts`
- `make py-lint`
- `make py-test`
- `make lint`

diff_added: 1560
diff_deleted: 1520
mechanical_churn: true
diff_lines: 3080

## Acceptance

- [ ] `python/design_drafter.py` created with `sentinel_prep_main`, `step2b_drafter_main`, `step2b_postplan_main`, `step2b5_main`
- [ ] `plan validator_autofix_main` added to `python/plan_quality.py`
- [ ] 5 new CLI verbs registered in `python/cli.py` (`design step2a`, `design step2b-drafter`, `design step2b-postplan`, `design step2b5`, `plan validator-autofix`)
- [ ] `python/session_env.py` updated to map retired Step 2 wrapper names to Python CLI verbs in launcher
- [ ] Pytest coverage added in `python/test_design_lifecycle.py` and `python/test_plan_quality.py`
- [ ] All 6 `.sh` files + `.md` siblings retired (deleted) per migration recipe
- [ ] `python/migrated-scripts.tsv` updated with retired paths
- [ ] `make lint-retired-scripts` passes
- [ ] `make py-test` passes
- [ ] `make lint` passes

diff_lines: 3080

## Test plan
(no test plan section in plan-file)
