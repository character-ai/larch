## Goal
Implement issue #3273: [IMPLEMENTING] [OOS] Complete stderr surfacing and forwarding coverage: resolve-conflict CI lanes, behavioral tests, launcher round-trip, and risk flag wiring\n\n## Description.

## Implementation Plan
## Plan

Complete the stderr forwarding coverage gaps from #3263 (launcher round-trip + risk-flag wiring + behavioral tests). **Part 1 (#3257) is dropped** — already fixed by #3270 (commit `12677a01e`) at `ship-pr.sh:3401` (direct vendor resolve-conflict launch) and `ship-pr.sh:2835` (recovery waterfall). SIMPLE-tier: smallest change that closes the three live gaps. Reviewed across 2 rounds; round 1 accepted FINDING_2/3/4 (test-approach corrections), round 2 clean.

### UPDATED: `scripts/launch-review.sh`
FINDING_12 — capture `--risk` and forward it as the 5th `*_launcher_append_outer_meta` arg. The flag is parsed but discarded today, so collector retries always get `OUTER_LAUNCHER_RISK=high` regardless of caller intent.
- Codex lane: initialize `RISK=""` next to `STDERR_SINK=""` (near line 111); in the `--risk)` case (line 131) keep the non-empty validation and add `RISK="$2"` before `shift 2`; at the `codex_launcher_append_outer_meta ... "$PWD" "" "$STDERR_SINK"` call (line 604) pass `"$RISK"` as the 5th arg in place of the literal `""`.
- Cursor lane (mirror, same file): `RISK=""` init near `STDERR_SINK=""` (near line 652); capture in the `--risk)` case (line 672); pass `"$RISK"` as the 5th arg at the `cursor_launcher_append_outer_meta` call (line 1028).
- Empty `RISK` (no `--risk` given) preserves today's behavior: the function default `${5:-${RISK:-high}}` resolves to `high`, so only callers that pass `--risk` change behavior.

### UPDATED: `scripts/launch-cursor-implement.sh`
FINDING_6 — at the `cursor_launcher_append_outer_meta "${TRANSCRIPT_PATH}.meta" "$SCRIPT_DIR/launch-cursor-implement.sh" "$PROMPT_FILE_SIDECAR" "$PWD"` call (line 339), append two empty positional args: `"" ""` (5th = risk, 6th = stderr_sink). Documents both optional slots and guards against future arg-position drift. No new flag acceptance. Behavior is unchanged: empty 5th keeps the existing `OUTER_LAUNCHER_RISK=high`; empty 6th omits the `STDERR_SINK=` line (the current 4-arg result).

### UPDATED: `scripts/launch-cursor-ci.sh`
FINDING_6 — at the `cursor_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-cursor-ci.sh" "$PROMPT_FILE" "$PWD"` call (line 227), append `"" ""` as above. Same no-op-today / future-proofing rationale.
(Parity note: `launch-codex-implement.sh` and `launch-codex-ci.sh` do NOT call `*_append_outer_meta` at all, so FINDING_6 has no codex-side edit — a classified, intentional asymmetry per `.claude/rules/external-tool-launcher-parity.md`.)

### UPDATED: `scripts/test-launch-review.sh`
Two changes, both lanes (codex and cursor invocation blocks):
1. FINDING_1/2 — remove the static source grep at line 1381 (`grep -F -- "_RUN_EXTERNAL_SINK_ARGS+=(--stderr-sink \"\$STDERR_SINK\")" …/launch-review.sh`) and do not assert on leaf codex/cursor argv for `--stderr-sink` (the flag is consumed at the `run-external-agent.sh` boundary). On the existing accept-path stubbed runs (`SS_ACCEPT_*` / `CSS_ACCEPT_*`, lines 1368-1390 / 2724-2742), keep the newline-reject checks and the `grep -Fxq "STDERR_SINK=$…_SINK"` outer `.meta` line check. Add a wrapper-ownership assertion on `${…_OUT}.meta`: the first physical line matching `^STDERR_SINK=` must appear before the first line matching `^OUTER_LAUNCHER=` (run-external-agent writes base meta before `*_launcher_append_outer_meta`; same contract as `scripts/test-run-external-agent.sh` #19h). Apply symmetrically in both lanes. Only if ordering proves ambiguous in practice, add a test-only `$STUB_BIN/run-external-agent.sh` shim that logs `"$@"` then `exec`s the real script and assert `--stderr-sink` plus the sink path — do not rely on leaf argv alone.
2. FINDING_12 — add a `--risk` round-trip test in both lanes: invoke the launcher with `--risk low` and assert the outer `.meta` contains `OUTER_LAUNCHER_RISK=low`; invoke without `--risk` and assert `OUTER_LAUNCHER_RISK=high` (the fail-closed default). Directly catches the discarded-flag regression.

### UPDATED: `scripts/test-collect-agent-retry.sh`
FINDING_1 (FINDING_3/4 revisions) — replace the static source grep at lines 815-821 (`_outer_sink_args+=(--stderr-sink …)` / `RETRY_ARGS+=(--stderr-sink …)` against `$COLLECTOR`) with runtime artifact assertions. Do NOT point `OUTER_LAUNCHER` at an argv-recording stub (collector validation requires canonical `$REPO_ROOT/scripts/launch-review.sh`; cases Q/W/Z) and do NOT put `run-external-agent.sh` in `CMD_JSON` (shape allowlists reject it; cases P2-P4). Two runtime cases after the existing `corrupt-risk` block (lines 800-813):
- **Outer-launcher retry (FINDING_3):** mirror case Q (lines 650-660): `prepare_outer_candidate`, `write_outer_meta` with `OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh`, valid prompt sidecar/workdir, plus `STDERR_SINK=<abs path under $TMPROOT>`. Run `PATH="$CURSOR_STUB_BIN:$PATH" run_collector …` (codex mirror: case Q2 pattern with codex stub + `LARCH_CODEX_MODEL`). On success, assert `${OUT%.txt}-retry.txt.meta` contains `STDERR_SINK=<sink>` and the first `^STDERR_SINK=` precedes the first `^OUTER_LAUNCHER=` (retry meta from real `run-external-agent.sh` inside launch-review). Stub only the leaf CLI via PATH.
- **CMD_JSON retry (FINDING_4):** mirror case A / sink-dotdot-cmd-json fixture shape: `write_empty_candidate`, `write_meta_body` with valid `TOOL=cursor`, `CMD_JSON=$(json_array bash "$HELPER" --output "$OUT")`, and `STDERR_SINK=<abs sink>`; `run_collector`. Assert `${OUT%.txt}-retry.txt.meta` records `STDERR_SINK=<sink>` from real `scripts/run-external-agent.sh` on the CMD_JSON retry path; optionally assert the first `^STDERR_SINK=` precedes `^CMD_JSON=`.
Keep the existing fail-closed `..` guard cases (lines 823-840) and the sink-absent case (842-852) unchanged.

### UPDATED: `scripts/launch-review.md`
FINDING_12 doc sync (script-md-siblings rule): add one line noting `--risk high|low` is captured and forwarded as `OUTER_LAUNCHER_RISK` in the outer `.meta` so `collect-agent-results.sh` replays empty-output retries with the caller's risk-gated effort. No other `.md` needs updating: `lib-external-launcher-common.md` already documents the 5th/6th args, and FINDING_6 is behavior-neutral for the cursor launcher `.md` files.

### Approach
Pure wiring + test-fidelity cleanup. FINDING_12 changes one real behavior (a discarded flag becomes functional); FINDING_6 is a documentary no-op; FINDING_1/2/3/4 replace source greps and invalid harness shapes with runtime meta artifact assertions at the `run-external-agent.sh` boundary (canonical outer launcher + valid CMD_JSON fixtures). Preserve the `external_launcher_append_outer_meta` contract verbatim: `<meta_path> <outer_launcher_path> <prompt_file_sidecar> <workdir> [risk] [stderr_sink]`. Keep both `launch-review.sh` lanes symmetric (launcher-parity rule).

### Edge cases
- No `--risk` passed: `RISK=""` → outer `.meta` keeps `OUTER_LAUNCHER_RISK=high` (unchanged). Round-trip test asserts this default branch too.
- Invalid `--risk` value: existing `[[ -n "${2:-}" ]]` guard still rejects empty; any non-empty value flows to the function, which normalizes anything other than `high|low` to `high` (fail-closed). No new launcher validation.
- FINDING_6 empty 6th arg: function still emits no `STDERR_SINK=` line, so the sink-absent meta invariant holds; existing meta tests stay green.
- Collector outer-retry tests must use canonical `launch-review.sh` and valid vendor-shaped `CMD_JSON`; invalid launcher paths or inner-command shapes fail closed before forwarding is exercised — do not weaken validation to accommodate stubs.

### Failure modes
- Risk capture wired in only one lane → asymmetric behavior. Mitigation: round-trip test runs in both lanes.
- Runtime assertion targets leaf argv or outer-only duplicate `STDERR_SINK=` after `OUTER_LAUNCHER=` → false green (FINDING_2). Mitigation: require first `^STDERR_SINK=` before first `^OUTER_LAUNCHER=` on primary launch-review `.meta`.
- Outer-retry test uses non-canonical `OUTER_LAUNCHER` → fail-closed or validation-weakening pressure (FINDING_3). Mitigation: keep `$REPO_ROOT/scripts/launch-review.sh`; stub leaf CLI only.
- CMD_JSON embeds `run-external-agent.sh` → rejected/wrong path (FINDING_4). Mitigation: valid `json_array bash "$HELPER"` cursor fixture; assert `${retry}.meta` wrapper ownership.

## Acceptance

- `scripts/launch-review.sh` captures `--risk` in BOTH the codex and cursor lanes and passes the captured value as the 5th `*_launcher_append_outer_meta` arg; the outer `OUTPUT.meta` records `OUTER_LAUNCHER_RISK=low` when launched with `--risk low`, and `OUTER_LAUNCHER_RISK=high` when `--risk` is omitted.
- `scripts/launch-cursor-implement.sh:339` and `scripts/launch-cursor-ci.sh:227` pass empty 5th + 6th positional args to `cursor_launcher_append_outer_meta`; the emitted `.meta` is unchanged (still `OUTER_LAUNCHER_RISK=high`, no `STDERR_SINK=` line). No `--stderr-sink`/`--risk` flag acceptance added to those launchers.
- `scripts/test-launch-review.sh` no longer contains the static source grep for `_RUN_EXTERNAL_SINK_ARGS+=(--stderr-sink …)`; both lanes assert the outer `.meta` line `STDERR_SINK=<sink>` appears before `OUTER_LAUNCHER=`; both lanes add a `--risk` round-trip assertion (low + default). `bash scripts/test-launch-review.sh` passes for `--tool codex` and `--tool cursor`.
- `scripts/test-collect-agent-retry.sh` no longer contains the static source greps for `_outer_sink_args`/`RETRY_ARGS`; it adds runtime outer-launcher (case-Q shape, canonical `launch-review.sh`) and CMD_JSON (case-A shape, valid vendor `CMD_JSON`) retry cases that assert the retry `.meta` records `STDERR_SINK=<sink>`. The fail-closed `..` and sink-absent cases stay green. `bash scripts/test-collect-agent-retry.sh` passes.
- `scripts/launch-review.md` documents that `--risk` is forwarded as `OUTER_LAUNCHER_RISK`.
- `collect-agent-results.sh` canonical `OUTER_LAUNCHER` validation and CMD_JSON shape allowlists are NOT weakened.
- Part 1 (#3257) is not touched (already fixed by #3270).
- `bash scripts/relevant-checks.sh` (or `make lint`) passes: shellcheck, bash 3.2 portability, bare-grep-probe, script-md-siblings.

diff_lines: 125

## Test plan
(no test plan section in plan-file)
