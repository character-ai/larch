## Plan

# sh-to-py C1a5: Port `agent dispatch-waterfall`

## Approach

Port the three-phase waterfall dispatcher into a new stdlib-only module and cut every live caller over to the CLI verb in the same change. Keep the bash behavior observable byte-for-byte. Do not re-implement reviewer launch or collection; keep shelling out to the existing `agent launch-review`, `agent launch-claude-review`, and `agent collect-results` CLI verbs (satisfies the Piece 3 / Piece 4 dependency).

**Module shape.** New `python/agent_waterfall.py` exposes `dispatch_waterfall(...)` (importable) and `dispatch_waterfall_main(argv)` (CLI). Mirror `python/review_dispatch.py` style: `from __future__ import annotations`, `import logging_util`, `import proc`, `REPO_ROOT = Path(__file__).resolve().parents[1]`. Use a distinct name; `agents.run_waterfall` is the unrelated coder-tier helper and must not be imported or shadowed.

**Phase launch/collect concurrency (pin explicitly).** Match `scripts/dispatch-with-waterfall.sh:258-526` (`reset_phase` → launch loop → `collect_phase` per phase). For each phase (1, 2, 3):
1. `reset_phase()` clears per-phase `pids` / `phase_indices` / `phase_outputs` / `phase_tools`.
2. Launch **every** pending slot in that phase with parallel `Popen(start_new_session=True)` (bash `launch_slot` background jobs) before any collection.
3. `collect_phase()` waits for all phase PIDs, then runs **one** `agent collect-results --summary-only` invocation with **all** phase output paths in launch order, splitting stdout into blank-line-separated positional blocks (same retry-path-safe positional mapping as bash).
4. Only after `collect_phase` settles does the driver advance queues into the next phase.

Do **not** serially launch-and-collect per slot inside a phase. Serial per-slot collection changes phase-2/phase-3 fallback ordering, `ALL_OUTPUT_FILES` alignment, and `PHASE*_SLOTS` bookkeeping versus bash.

**Phase-3 failure finalization and tail replay (pin explicitly).** Match `scripts/dispatch-with-waterfall.sh:540-558`. After `collect_phase(phase3_failed)`:
1. For each index in `phase3_failed`, assign `final_outputs[idx] = output_for_phase(slot_outputs[idx], phase3)`, `final_tools[idx] = "claude"`, set `dispatch_ok = false`, and flip `static_dispatch_ok` / `dynamic_dispatch_ok` per the `dyn-*` slot-name split (same as bash lines 540-549).
2. When `phase3_failed` is non-empty, run a **separate** tail `agent collect-results` replay: `LARCH_QUIET_DISABLE=1`, positional output paths only (no `--summary-only`), stdout discarded, errors ignored (`|| true` equivalent). Path order follows `phase3_failed` iteration order; each path is the phase-3 `final_outputs[idx]` just assigned.

This loop is **not** part of per-phase `collect_phase`; omitting it leaves `final_outputs` empty for hard-failed phase-3 slots, skips tail replay, and mis-emits `ALL_OUTPUT_FILES` / the paths-file versus bash even when process exit is 0.

**Exit-code contract (pin explicitly).** Match bash caller expectations:
- **Exit 0**: normal completion, including settled dispatch where one or more slots failed (`DISPATCH_OK=false`, `STATIC_DISPATCH_OK=false`, `DYNAMIC_DISPATCH_OK=false`, `ALL_SLOTS_DROPPED=true`, or `WARN=cost-fallback-exceeded-threshold`). Callers parse KVs from captured stdout; they must not treat `DISPATCH_OK=false` as a process failure.
- **Exit 2**: argv/usage errors, invalid ERE pre-validation, empty manifest / invalid NDJSON slot rows, paths-file write failures, and other pre-launch validation failures (no paths-file written on empty manifest).
- **Exit 143**: SIGTERM teardown path after killing active launcher subtrees.
- Never exit non-zero solely because a slot dropped or an external launcher failed when the bash would have emitted KVs and returned 0.

**fd-3 / stdout contract.** Call `logging_util.quiet_init(argv0="dispatch-with-waterfall.sh")` then emit every KV through `logging_util.emit_kv`. This matches the bash lib-quiet routing: callers that run the verb with captured stdout still receive the KVs (fd-3 is dup'd from the inherited stdout before redirect). Do **not** add `("agent","dispatch-waterfall")` to `_MACHINE_STDOUT_KEYS`; that mirrors every other `agent` verb. Human diagnostics go through `logging_util.diagnostic` / `BreadcrumbWriter`, never raw `print` after quiet init.

**POSIX ERE translation (pin explicitly).** Callers pass grep-style ERE with POSIX classes (`^[[:space:]]*## Recommendation`, `^[[:space:]]*(schema_version|\{"no_issues_found)`). Python `re` does not accept `[[:space:]]` literally. Add a small `posix_ere_to_python(pattern: str) -> str` helper in `agent_waterfall.py` that translates POSIX character classes callers actually use (`[[:space:]]`, `[[:digit:]]`, etc.) before compiling with `re.compile(..., re.MULTILINE)`.
- **Pre-validation**: mirror bash `grep -E` on empty stdin — compile the translated pattern; reject only invalid syntax (bash rc > 1 equivalent), not no-match (rc 1). Exit `2` with the same diagnostic tokens (`--require-result-pattern is not a valid ERE` / `--require-first-line-pattern is not a valid ERE`) before launching any slot.
- **First-line gate**: mirror bash `awk '/[^[:space:]]/ { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print; exit }'` on the check file before applying the translated first-line pattern.
- **Result gate / salvage**: apply the translated result pattern to the full file content; confine #3423 salvage to the format-gate-miss branch only.

**Behavioral parity surface (preserve exactly).** Drive the port from the retired harness assertions:
- NDJSON slot validation: `slot` non-empty, `tool` in `codex|cursor`, `output` non-empty, `agent`/`prompt_file` mutual-exclusion and exactly-one, newline/CR rejection in output paths, empty manifest exits `2` with `slots file contains no slot rows` and writes no paths-file.
- Pre-validate `--require-result-pattern` and `--require-first-line-pattern` as ERE once before any launch; invalid pattern exits `2` before launching any slot.
- Three-phase fallback: phase 1 primary tool, phase 2 other present tool, phase 3 `claude`. `STATUS=OK` and `STATUS=cap_hit` settle; `cap_hit` bypasses the pattern gate.
- `--no-fallback`: single-phase drop-on-failure; emit per-slot `slot<TAB>tool<TAB>reason<TAB>snippet` sidecar at `<paths-file>.dropped-slots` with `DROPPED_SLOTS_FILE`; reasons `format-gate-miss|result-gate-miss|empty|collector-failure|result-unreadable|tool-absent`; `ALL_SLOTS_DROPPED=true` when nothing settles; flatten TAB/CR/newline in slot/tool fields.
- #3423 salvage: on a non-empty first-line-gate miss, find the first matching line, strip preceding lines, rewrite in place (temp + atomic rename), settle. Confine salvage to the format-gate-miss branch; `empty`, `result-gate-miss`, `result-unreadable`, `collector-failure` are untouched.
- Phase output suffixing (`-phaseN`, `.txt`-aware), line-oriented paths-file with temp+rename replace and default `<slots-file>.output-files`, `FALLBACK_COUNT`/`COMBINED_FALLBACK_COUNT`, `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default 3) → `WARN=cost-fallback-exceeded-threshold`, `DISPATCH_OK`/`STATIC_DISPATCH_OK`/`DYNAMIC_DISPATCH_OK` (the `dyn-*` slot-name split), `--fallback-counter-file` accumulation, per-phase `collect-results --summary-only`, and the post-phase-3-failure tail `collect-results` replay (with `LARCH_QUIET_DISABLE=1`, no `--summary-only`).
- KV grammar emitted in the same order: `PHASE1_SLOTS`, `PHASE2_SLOTS`, `PHASE3_SLOTS`, `ALL_OUTPUT_FILES`, `ALL_OUTPUT_FILES_PATH`, `ALL_OUTPUT_TOOLS`, `FALLBACK_COUNT`, `COMBINED_FALLBACK_COUNT`, optional `WARN`, `DISPATCH_OK`, `STATIC_DISPATCH_OK`, `DYNAMIC_DISPATCH_OK`, optional `ALL_SLOTS_DROPPED`, optional `DROPPED_SLOTS_FILE`.

**Process-subtree teardown (Decision 2).** Launch each slot with `subprocess.Popen(argv, start_new_session=True, stdout=DEVNULL, stderr=open(f"{output}.launch-stderr","wb"))` so each launcher is its own session/process-group leader. Track `(pid, pgid)` per active phase. On normal completion reap with `wait`. Install a `signal.signal(SIGTERM, ...)` handler and an `atexit` handler that, for each active group, sends `SIGTERM` via `os.killpg(pgid, SIGTERM)`, then performs a recursive descendant sweep (call `pgrep -P` like the bash, since macOS has no `/proc`), then reaps. The SIGTERM path exits `143`. This avoids orphaned codex/cursor/claude subprocesses on cancel or timeout. Write the `${output}.done` sentinel fallback exactly as the bash does when the launcher leaves none.

**Launcher + collector reuse.** Build the launcher argv the same way the bash does (claude vs external branch, `--timing-task-kind` clamped to 64 chars, `--competition-notice[-file]`, common context args `--diff-file/--commit-count/--plan-file/--feature-file/--scope-files/--description-text`). Collect each phase by running `agent collect-results --timeout N --summary-only <outputs...>` and splitting stdout into blank-line-separated positional blocks (same retry-path-safe positional mapping the bash uses). After phase-3 failures, run the tail replay collector described above.

**Multi-token default invocation (array form).** Any caller whose default becomes `python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall` must not store that string in a scalar shell variable executed as `"$VAR"`. Use the dispatch-panel pattern:
- Env override: single executable path → one-element array (`dispatch_cmd=("$AGGREGATE_DISPATCH_SH")`).
- Default: multi-token argv array (`dispatch_cmd=(python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall)`).
- Invoke `"${dispatch_cmd[@]}" "${dispatch_args[@]}"`.
Apply this to `aggregate-findings.sh`, `dispatch-panel.sh`, and the regenerated embedded `dispatch-plan-review-panel.sh` / `dispatch-plan-voters.sh` blobs.

**Caller cutover (preserve env seams).** Each live caller keeps its subprocess boundary and captures stdout; only the default command changes to `python3 "<cli>" agent dispatch-waterfall`:
- `decompose.py`: **do not** use `os.environ.get(DECOMPOSE_*_WATERFALL_SH, default)` with a truthy default string — that makes the override branch unreachable. Split override detection from default:
  - `if "DECOMPOSE_PANEL_WATERFALL_SH" in os.environ:` → `waterfall_argv = [os.environ["DECOMPOSE_PANEL_WATERFALL_SH"]]` (single executable override, same as today).
  - `else:` → `waterfall_argv = [sys.executable, str(PLUGIN_ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]`.
  - Same pattern for `DECOMPOSE_AGGREGATE_WATERFALL_SH` in `aggregate_partition`.
  - Build `cmd = waterfall_argv + ["--slots-file", ...]` (argv list, never a one-string `cmd = [waterfall, ...]` where `waterfall` was the old default path).
  - Update `_append_failure` tool labels from `dispatch-with-waterfall.sh` to `agent dispatch-waterfall`.
- `dispatch-code-voters.sh`: repoint the direct call to `python3 "$CLI" agent dispatch-waterfall`.
- `legacy_review_shell/dispatch-panel.sh`: replace scalar `DISPATCH_WATERFALL` with `DISPATCH_WATERFALL_CMD` array default; keep `DISPATCH_WATERFALL` env as one-element override; call `"${DISPATCH_WATERFALL_CMD[@]}"`.
- `legacy_review_shell/aggregate-findings.sh`: replace scalar `DISPATCH_SH` with `dispatch_cmd` array; keep `AGGREGATE_DISPATCH_SH` as one-element override; call `"${dispatch_cmd[@]}"`.
- `plan_review.py` embedded blobs: regenerate `scripts/dispatch-plan-voters.sh` (hardcoded path → verb) and `skills/design/scripts/dispatch-plan-review-panel.sh` (`DISPATCH_PLAN_REVIEW_WATERFALL_SH` override → one-element array; default → `python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall` argv array) so they call the verb through the materialized root's symlinked `python/`.

**Audit / run-log detection continuity.** `exn-agg-dispatch-fail` in `python/run_logs.py` and `python/audit_runs.py` currently grep `dispatch-with-waterfall exited non-zero`. When aggregate-findings renames its warning to `agent dispatch-waterfall exited non-zero`, update both detectors to accept **both** substrings (historical + new) plus `DISPATCH_OK=false`, so old run logs and new failures remain visible.

**Deletions.** Remove `scripts/dispatch-with-waterfall.sh`, `scripts/dispatch-with-waterfall.md`, `scripts/test-dispatch-with-waterfall.sh`, `scripts/test-dispatch-with-waterfall.md`, `scripts/test-no-grouped-reuse-guard.sh` (and its sibling `.md` if present). Record each in `python/migrated-scripts.tsv`. Remove the `agent-lint.toml` allowlist entry for the deleted grouped-reuse harness.

## Files to modify/create

### NEW: python/agent_waterfall.py
The ported dispatcher. `dispatch_waterfall(...)` core plus `dispatch_waterfall_main(argv)` argparse-free flag parser matching the bash flags (`--slots-file`, `--codex-present|--codex-available`, `--cursor-present|--cursor-available`, `--mode`, `--diff-file`, `--commit-count`, `--plan-file`, `--feature-file`, `--scope-files`, `--description-text`, `--timeout`, `--fallback-counter-file`, `--competition-notice`, `--competition-notice-file`, `--paths-file`, `--require-result-pattern`, `--require-first-line-pattern`, `--no-fallback`, `--help`). Stdlib-only; `quiet_init` + `emit_kv`; explicit exit-code matrix above; `posix_ere_to_python()` for caller ERE patterns; per-phase `reset_phase` / parallel launch-all / single `collect_phase` sequencing; phase-3 failure loop that writes `final_outputs`/`final_tools` and sets `DISPATCH_OK=false`; tail `collect-results` replay (`LARCH_QUIET_DISABLE=1`, positional paths only, no `--summary-only`, stdout discarded, errors ignored); `Popen(start_new_session=True)` launches; SIGTERM/atexit subtree teardown; `agent collect-results --summary-only` once per phase; atomic paths-file and dropped-slots sidecar.

### NEW: python/test_agent_waterfall.py
Colocated pytest replacing `scripts/test-dispatch-with-waterfall.sh`. **This file is the sole behavioral parity authority** for the retired bash harness; do not depend on rerunning the deleted script after cutover. Build the CLI path from `Path(__file__).with_name("cli.py")`; do not write retired-path literals (build paths at runtime). Use codex/cursor/claude/cp stubs on `PATH` as the bash harness does. Cover: phase-2 and phase-3 fallback, two-slot order, optional metadata fields, claude hard-fail `DISPATCH_OK=false` plus `.launch-stderr` sidecar (process exit 0), phase-3 hard-fail still emits the phase-3 path in `ALL_OUTPUT_FILES` / paths-file and invokes tail `collect-results` without `--summary-only` (stub or spy on collector argv), WARN threshold, invalid-schema and empty-manifest exit `2`, newline/CR rejection, competition notice, override and default paths-file, embedded-space paths, both ERE gates with POSIX `[[:space:]]` patterns (match, cap_hit bypass, invalid-ERE pre-launch exit `2`, salvage cases a/b/c/d), `--no-fallback` drop/keep/partial/absent with `DROPPED_SLOTS_FILE` reasons and TAB-flattening, fallback-counter persistence, degraded-cursor fallback, phase concurrency (multi-slot phase launches all Popen children before one collect-results call; assert collector argv order matches launch order), and a behavioral SIGTERM teardown test asserting the launcher subtree dies.

**Aggregate-findings ERE parity (pin explicitly).** Mirror the live aggregate gate from `python/legacy_review_shell/aggregate-findings.sh:29` / `:887`. Use the exact expanded pattern (fixed attestation literal, no shell variable expansion in the test fixture):

`^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)`

Add dedicated pytest cases that pass this pattern to `--require-result-pattern`:
1. **Finding-heading branch**: stub output whose first non-empty line is `### FINDING_1:` (with optional preamble stripped by first-line gate) settles / passes the result gate.
2. **Attestation branch**: stub output that is only `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` (with optional surrounding whitespace per the `[[:space:]]*` anchors) settles / passes.
3. **No-match rejection**: preamble-only or unrelated body (neither a `### FINDING_N:` heading nor the bare attestation line) fails the result gate and does not settle.
4. **Invalid ERE pre-launch**: a deliberately broken alternation exits `2` before any slot launch with `--require-result-pattern is not a valid ERE`.

Keep existing decompose/voter `[[:space:]]` and plan-review TSV sentinel cases; this aggregate alternation is additive, not a replacement.

**Grouped-reuse guard** (ports `test-no-grouped-reuse-guard.sh` intent without self-match):
- Assert `python/agent_waterfall.py` contains none of the retired grouped-reuse symbols (`reuse_slot_result`, `find_group_ok_for_tool`, `append_group_ledger_ok`, `GROUP_LEDGER`, `REUSED_INDICES`, `idx_was_reused`, `has_fallback_groups`, `waterfall-group-results`, `DEDUPE_REUSED`, `slot_fallback_groups`, `REUSED_INDICES_FILE`, `phase2_grouped`).
- **Artifact-name guard on the dispatcher module**: dynamically construct the needles `fallback_` + `group`, `.dedup`, and `waterfall-group-results` (never embed those literals as static grep needles inside `python/test_agent_waterfall.py`) and assert `python/agent_waterfall.py` contains none of them. This mirrors the retired harness's `waterfall-group-results` / `.dedup` scan of `dispatch-with-waterfall.sh` now that the dispatcher lives in Python.
- Scan `skills/` and `scripts/` for the dynamically constructed `fallback_` + `group` token exactly as the retired harness does (exclude `.md` and `/test-*.sh` paths).
- Do **not** grep a literal `fallback_group` token across all of `python/` from inside this test file. Either omit `python/` from that repo-wide scan (retired harness never scanned `python/`) **or** build the searched token dynamically and exclude `python/test_agent_waterfall.py` from any broader repo scan, matching the retired-path literal-avoidance pattern used elsewhere in pytest ports.

### UPDATED: python/cli.py
Add registry row `("agent", "dispatch-waterfall"): ("agent_waterfall", "dispatch_waterfall_main")`. Do not add it to `_MACHINE_STDOUT_KEYS`.

### UPDATED: python/decompose.py
Retarget `dispatch_panel` and `aggregate_partition` waterfall invocation:
- Replace `waterfall = os.environ.get("DECOMPOSE_*_WATERFALL_SH", str(PLUGIN_ROOT / "scripts" / "dispatch-with-waterfall.sh"))` with explicit `in os.environ` override detection and a multi-token default argv list (`sys.executable`, `str(PLUGIN_ROOT / "python" / "cli.py")`, `"agent"`, `"dispatch-waterfall"`).
- Build `cmd = waterfall_argv + slot_args` (never a single-string default in `cmd[0]`).
- Update failure logging tool name from `dispatch-with-waterfall.sh` to `agent dispatch-waterfall`.
- Keep `DECOMPOSE_PANEL_WATERFALL_SH` / `DECOMPOSE_AGGREGATE_WATERFALL_SH` as single-executable override seams (unchanged test contract).

### UPDATED: python/test_decompose.py
Add tests that **unset** `DECOMPOSE_PANEL_WATERFALL_SH` / `DECOMPOSE_AGGREGATE_WATERFALL_SH` and spy or monkeypatch `subprocess.run` to assert the default `cmd` prefix is `[sys.executable, "<plugin>/python/cli.py", "agent", "dispatch-waterfall"]` (not the deleted `scripts/dispatch-with-waterfall.sh` path). Keep existing stub-override tests unchanged. One case per call site (`dispatch_panel` / `aggregate_partition`) is sufficient.

### UPDATED: scripts/dispatch-code-voters.sh
Repoint the direct `dispatch-with-waterfall.sh` invocation (the `waterfall_output=$(...)` call) to `python3 "$CLI" agent dispatch-waterfall`. No other behavior change; this script is not otherwise ported here.

### UPDATED: scripts/dispatch-code-voters.md
Replace every `dispatch-with-waterfall.sh` / `scripts/dispatch-with-waterfall.sh` reference with `python/cli.py agent dispatch-waterfall` wording. Preserve shrink-not-backfill semantics and the `set +e`/`set -e` non-zero-exit tolerance prose (now describing the verb, not the deleted script).

### UPDATED: scripts/test-dispatch-code-voters.sh
Move the waterfall stub from writing `$root/scripts/dispatch-with-waterfall.sh` to handling `agent dispatch-waterfall` inside the stub `$root/python/cli.py`, so the repointed call site is intercepted and the harness stays green.

### UPDATED: python/legacy_review_shell/dispatch-panel.sh
Replace scalar `DISPATCH_WATERFALL` default with `DISPATCH_WATERFALL_CMD` array: env override `DISPATCH_WATERFALL` → `DISPATCH_WATERFALL_CMD=("$DISPATCH_WATERFALL")`; default → `DISPATCH_WATERFALL_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall)`. Invoke `"${DISPATCH_WATERFALL_CMD[@]}" "${waterfall_args[@]}"`. Update rc-failure WARN prose to verb wording.

### UPDATED: python/legacy_review_shell/aggregate-findings.sh
Replace scalar `DISPATCH_SH` with `dispatch_cmd` array: env override `AGGREGATE_DISPATCH_SH` → `dispatch_cmd=("$AGGREGATE_DISPATCH_SH")`; default → `dispatch_cmd=(python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall)`. Invoke `"${dispatch_cmd[@]}" "${dispatch_args[@]}"`. Change failure warning to `agent dispatch-waterfall exited non-zero (rc=$dispatch_rc)` (drop the `scripts/` path).

### UPDATED: python/plan_review.py
Regenerate the two gzip-embedded assets so their waterfall invocation uses argv-array defaults calling `agent dispatch-waterfall`. Decode each asset, edit the bash, re-encode with `base64.b64encode(gzip.compress(body, compresslevel=9, mtime=1781390774))` to stay byte-stable with the existing header; replace only the changed string literals. Leave all other `_LEGACY_ASSETS` entries untouched.

### UPDATED: python/test_plan_review.py
Add decode-and-assert tests for both regenerated embedded scripts (`dispatch-plan-voters.sh`, `skills/design/scripts/dispatch-plan-review-panel.sh`): decoded bodies must invoke `agent dispatch-waterfall`, use array-form dispatcher invocation (not a scalar multi-token path), and must not contain `dispatch-with-waterfall.sh`. Lint cannot see inside gzipped `_LEGACY_ASSETS`; this pytest is the runtime backstop.

### UPDATED: python/run_logs.py
Extend `exn-agg-dispatch-fail` to match `agent dispatch-waterfall exited non-zero` in addition to the legacy `dispatch-with-waterfall exited non-zero` substring; keep `DISPATCH_OK=false` as an alternate signal.

### UPDATED: python/audit_runs.py
Mirror the `run_logs.py` substring expansion for `exn-agg-dispatch-fail` so audit completeness keeps detecting aggregator dispatch failures in both historical and post-cutover execution-issues text.

### UPDATED: agent-lint.toml
Remove the `scripts/test-no-grouped-reuse-guard.sh` allowlist entry (lines ~330–332); grouped-reuse guard coverage moves to `python/test_agent_waterfall.py`.

### UPDATED: python/migrated-scripts.tsv
Add `#4169` rows (one row per retired path, no duplicates):
- `scripts/dispatch-with-waterfall.sh`
- `scripts/dispatch-with-waterfall.md`
- `scripts/test-dispatch-with-waterfall.sh`
- `scripts/test-dispatch-with-waterfall.md`
- `scripts/test-no-grouped-reuse-guard.sh` (and `scripts/test-no-grouped-reuse-guard.md` if present)

### UPDATED: Makefile
Retarget `test-dispatch-with-waterfall` to run `python3 -m pytest -q python/test_agent_waterfall.py`. Retarget or retire `test-no-grouped-reuse-guard` to the pytest guard. Keep both inside their existing `test-harnesses-*` shard rows; update the rip-out-guard wiring so no recipe runs the deleted bash files.

### UPDATED: skills/shared/topology.tsv
Update the `design.decompose.dispatch` row note from `dispatch-with-waterfall` to the verb wording; then regenerate `docs/topology.md`.

### UPDATED: docs/topology.md
Regenerated output of `python3 python/cli.py generate topology-docs` after the `topology.tsv` edit. Do not hand-edit beyond regeneration.

### UPDATED: skills/shared/voting-protocol.md
Replace the four `dispatch-with-waterfall.sh` references with `agent dispatch-waterfall` wording.

### UPDATED: skills/review/SKILL.md
In the retained-deps / harness inventory line: replace `dispatch-with-waterfall.sh` with `python/cli.py agent dispatch-waterfall`; replace `test-dispatch-with-waterfall.sh` with `python/test_agent_waterfall.py` (or `make test-dispatch-with-waterfall`).

### UPDATED: skills/design/references/plan-review.md
Replace the `dispatch-with-waterfall` reference with the verb.

### UPDATED: skills/design/references/decompose-panel.md
Replace the `dispatch-with-waterfall` reference with the verb.

### UPDATED: skills/design/references/flags.md
Replace the `dispatch-with-waterfall` reference with the verb.

### UPDATED: docs/external-reviewers.md
Update the fallback-taxonomy sentence naming `scripts/dispatch-with-waterfall.sh` to the verb.

### UPDATED: docs/vendor-agent-diagnostics-audit.md
Update the two `dispatch-with-waterfall.sh` references to the verb.

### UPDATED: docs/linting.md
Update the harness reference so it names `python/test_agent_waterfall.py` instead of the deleted bash harness.

### UPDATED: docs/python-migration.md
Add a short C1a5 decision-log note: waterfall dispatcher ported to `agent dispatch-waterfall`; callers cut over; `decompose.py` uses `in os.environ` override detection (not `get` with a truthy default path); embedded plan-review blobs regenerated to call the verb; audit predicates widened for renamed aggregator warnings; POSIX ERE patterns translated for Python `re`; per-phase launch-all-then-collect-once concurrency preserved; phase-3 failure finalization and tail `collect-results` replay preserved; aggregate-findings alternation pattern pinned in pytest; grouped-reuse guard covers `fallback_group` / `.dedup` / `waterfall-group-results` on the Python dispatcher via dynamic needles; `python/test_agent_waterfall.py` is the sole parity authority for the retired bash harness.

### UPDATED: SECURITY.md
Update the `dispatch-with-waterfall.sh` mention to the verb (security-relevant behavior is unchanged; only the path name changes).

## Edge cases
- ERE translation: callers pass POSIX patterns like `^[[:space:]]*## Recommendation` and `^[[:space:]]*(schema_version|\{"no_issues_found)`. `posix_ere_to_python()` must make Python `re` behave like bash `grep -E` on the harness fixtures; pre-validation rejects only compile/syntax failures (grep rc > 1), not no-match (grep rc 1).
- **Aggregate alternation**: the `^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)` pattern exercises both alternation branches and whitespace anchors; a partial translator can pass simpler single-branch cases yet break `/review` aggregate-findings at runtime.
- Phase concurrency: a serial launch-collect loop inside phase 2 or 3 can settle slots in the wrong order relative to bash queue seeding; the pytest phase-concurrency case pins one collect-results call per phase with ordered outputs.
- **Phase-3 hard failure**: even when phase-3 Claude collection fails, bash still records the phase-3 output path in `final_outputs`, sets `DISPATCH_OK=false`, and runs tail `collect-results` without `--summary-only`; skipping that path yields empty `ALL_OUTPUT_FILES` for the slot.
- `close_fds` interaction: the verb runs under callers that capture stdout; verify KVs still arrive on the captured pipe via the `quiet_init` fd-3 dup, with no stray output to the real terminal.
- Embedded-space and newline-in-path: keep the line-oriented paths-file invariant and the pre-write newline/CR guard.
- `cap_hit` must bypass the gate; salvage must never fire on `empty`.
- Scalar-vs-array shell defaults: any missed `"$SCALAR"` call site for a multi-token default breaks at ENOENT; pytest embedded-blob decode tests and `bash scripts/test-dispatch-code-voters.sh` are the guardrails.
- **Decompose `os.environ.get` trap**: `get("DECOMPOSE_PANEL_WATERFALL_SH", deleted_path)` always returns a truthy default when the env var is unset, so a naive `if env: override else: verb` branch never selects the verb; `in os.environ` is mandatory.
- Grouped-reuse guard self-match: a naive `rg fallback_group python/` inside `test_agent_waterfall.py` false-fails; use dynamic token construction and/or exclude the test module from scans. The `.dedup` and `waterfall-group-results` checks on `agent_waterfall.py` must use the same dynamic-needle pattern.

## Failure modes
- Orphaned subprocesses: if teardown misses a descendant, codex/cursor/claude can survive cancel. The SIGTERM teardown must kill the group and sweep descendants; the behavioral test pins this.
- False hard-failure on partial dispatch: if the Python verb exits non-zero when bash would exit 0 with `DISPATCH_OK=false`, callers (`dispatch-panel.sh`, `decompose.py`) mis-log failures or skip KV parsing. The exit-code matrix and pytest cases for `DISPATCH_OK=false` with exit 0 pin this.
- Phase ordering drift: per-slot collection inside a phase changes which slots see phase-2 vs phase-3 fallback and misaligns `ALL_OUTPUT_FILES` with bash. The explicit `reset_phase` / launch-all / `collect_phase` structure and pytest guard prevent this.
- **Phase-3 failure bookkeeping drift**: omitting the `phase3_failed` → `final_outputs` loop or the tail `collect-results` replay leaves `ALL_OUTPUT_FILES` / paths-file empty for failed Claude fallbacks while still emitting `DISPATCH_OK=false`; callers assume per-slot output paths exist for diagnostics. The hard-fail pytest case pins `ALL_OUTPUT_FILES`, paths-file line, and tail collector invocation.
- POSIX ERE mismatch: passing `[[:space:]]` literally to `re.compile` rejects valid caller patterns or changes gate behavior vs `grep -E`. `posix_ere_to_python()` plus harness parity cases for decompose/aggregator/voter patterns pin this.
- **Aggregate gate regression**: missing the alternation pytest matrix lets a broken `posix_ere_to_python()` ship; aggregate-findings then drops or mis-settles aggregator slots while callers only log a warning. The four-case aggregate pattern matrix is mandatory.
- **Decompose default-path regression**: copying `os.environ.get(..., scripts/dispatch-with-waterfall.sh)` into a truthy-branch refactor leaves production calling the deleted script (ENOENT) even after the verb lands; `python/test_decompose.py` default-argv tests pin the fix.
- Stale references: any remaining literal `scripts/dispatch-with-waterfall.sh` or `scripts/test-no-grouped-reuse-guard.sh` in a tracked, non-`larch-logs` file fails `make lint-retired-scripts`. The sweep must include `scripts/dispatch-code-voters.md` and `agent-lint.toml`; also check `scripts/test-design-multi-round-integration.sh` and `skills/design/scripts/review-design-step3-loop.sh` for residual literals.
- **Migration manifest typo**: duplicate or missing `migrated-scripts.tsv` rows (e.g. listing `dispatch-with-waterfall.sh` twice and omitting `.md`) break `lint-retired-scripts` bookkeeping and can leave retired contract docs untracked.
- Embedded-blob drift: a regenerated blob that still points at the deleted path breaks plan-review panel/voter dispatch at runtime (lint will not catch it, since it is gzipped). `python/test_plan_review.py` decode-and-assert tests are mandatory.
- Audit blind spot: if aggregate warning prose is renamed without widening `exn-agg-dispatch-fail` matchers, run-log completeness and `audit_runs` miss rc!=0 aggregator failures that do not also log `DISPATCH_OK=false`. Dual-substring detection is the backstop.
- Grouped-reuse guard false positive: scanning `python/` with a literal `fallback_group` needle inside the guard test itself fails `make py-test` on a correct port. Dynamic token construction and test-file exclusion are mandatory.
- **Grouped-reuse reintroduction via artifact names**: omitting `.dedup` / `waterfall-group-results` / dynamic `fallback_group` checks on `agent_waterfall.py` lets grouped-reuse bookkeeping return under different symbol names while the symbol-list guard stays green.

## Testing strategy
- `python3 -m pytest -q python/test_agent_waterfall.py` covering every accept/reject path above, including POSIX `[[:space:]]` ERE gates, the **aggregate-findings alternation pattern** (both branches, no-match rejection, invalid-ERE pre-launch exit 2), per-phase launch-all-then-collect-once concurrency, phase-3 hard-fail `final_outputs` + tail `collect-results` replay (no `--summary-only`), the SIGTERM teardown, the no-grouped-reuse guard (symbol list + dynamic `fallback_group` / `.dedup` / `waterfall-group-results` checks on `agent_waterfall.py`, no self-match), and `DISPATCH_OK=false` with process exit 0. **This pytest file is the sole behavioral parity authority** for the retired `scripts/test-dispatch-with-waterfall.sh`; do not add a post-deletion rerun of the bash harness (its cases hardcode `$REPO_ROOT/scripts/dispatch-with-waterfall.sh` and cannot run once the script is deleted).
- `python3 -m pytest -q python/test_decompose.py` (new default-argv tests when env overrides are unset) plus `python/test_plan_review.py` (embedded-blob decode tests) and `python/test_review_pipeline.py python/test_review_aggregate.py python/test_plan_review_panel.py` to confirm caller cutover and regenerated blobs.
- `bash scripts/test-dispatch-code-voters.sh` (all sections) after the stub update.
- `make lint` + `make py-lint` + `make py-test` + `make lint-retired-scripts` all green.

## Acceptance

- `python/agent_waterfall.py` exists with importable `dispatch_waterfall(...)` and `dispatch_waterfall_main(argv)`; `("agent","dispatch-waterfall")` is registered in `python/cli.py`, runs stdlib-only, and is not added to `_MACHINE_STDOUT_KEYS`.
- Behavioral parity with the retired bash: NDJSON slot validation; three-phase fallback (`STATUS=OK`/`cap_hit` settle, `cap_hit` bypasses the gate); both ERE gates with POSIX-class translation and #3423 preamble salvage; `--no-fallback` drop-on-failure with the per-slot dropped-slots TSV (`DROPPED_SLOTS_FILE`, all six reasons), TAB/CR flattening, and `ALL_SLOTS_DROPPED`; phase output suffixing; atomic line-oriented paths-file; full KV grammar in order; `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` WARN; `--fallback-counter-file` accumulation; per-phase launch-all-then-one-collect concurrency; phase-3 failure finalization plus the tail `collect-results` replay; and the exit-code matrix (0 on settled `DISPATCH_OK=false`, 2 on validation, 143 on SIGTERM).
- Process-subtree teardown: launchers run in new sessions; SIGTERM/atexit kills the process group and sweeps descendants; no orphaned codex/cursor/claude subprocess survives cancel or timeout.
- Every live caller is cut over to `agent dispatch-waterfall` and stays green: `decompose.py` panel + aggregate (using `in os.environ` override detection and an array argv, never `get` with a truthy default path), `scripts/dispatch-code-voters.sh` (+ `.md`), `legacy_review_shell/dispatch-panel.sh` and `aggregate-findings.sh` (array-form defaults, env-override seams preserved), and the regenerated gzip-embedded `dispatch-plan-voters.sh` + `dispatch-plan-review-panel.sh` blobs in `plan_review.py`.
- `run_logs.py` and `audit_runs.py` `exn-agg-dispatch-fail` detectors match both the legacy and the renamed aggregator-warning substrings, plus `DISPATCH_OK=false`.
- `python/test_agent_waterfall.py` is the sole behavioral-parity authority (covers every path above, including the aggregate-findings alternation pattern, phase concurrency, phase-3 hard-fail replay, SIGTERM teardown, and the no-grouped-reuse guard via dynamically built needles with no self-match). `python/test_decompose.py` (default-argv when overrides unset) and `python/test_plan_review.py` (decode-and-assert on both embedded blobs) pin the caller and blob cutover.
- `scripts/dispatch-with-waterfall.sh` + `.md`, `test-dispatch-with-waterfall.sh` + `.md`, and `test-no-grouped-reuse-guard.sh` (+ `.md` if present) are deleted; each retired path is recorded in `python/migrated-scripts.tsv`; the `agent-lint.toml` grouped-reuse allowlist entry is removed; Makefile harness targets are retargeted to pytest.
- All stale `dispatch-with-waterfall` references are swept (docs, skills, `SECURITY.md`, `skills/shared/topology.tsv` + regenerated `docs/topology.md`).
- `make lint`, `make py-lint`, `make py-test`, and `make lint-retired-scripts` are all green.

review_status: complete
rounds_completed: 5
diff_lines: 3280
