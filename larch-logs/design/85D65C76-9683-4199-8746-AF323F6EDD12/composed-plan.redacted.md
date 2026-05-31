## Plan

Make `STDERR_SINK` a first-class `.meta` field that survives a collector retry, so a
re-invoked launcher keeps the real agent stderr in its `.stderr-tail` instead of falling
back to `.sidecar` / output / `.diag`. Cover both the outer-launcher retry path (defensive
wiring — `launch-review.sh` learns the flag) and the CMD_JSON retry path (the functional
fix — default-mode lanes that pass `--stderr-sink` to `run-external-agent.sh`). Record only
when a sink is set, so no-sink lanes keep their current `.meta` byte-for-byte.

### UPDATED: `scripts/run-external-agent.sh`
- In the base `.meta` writer (the `{ echo TOOL=… ; … ; printf CMD_JSON=… } > "${OUTPUT_FILE}.meta"` block, ~lines 193-200), record the sink between the `OUTPUT_FILE=` and `CMD_JSON=` lines, only when non-empty: an `if [[ -n "$STDERR_SINK" ]]; then printf 'STDERR_SINK=%s\n' "$STDERR_SINK"; fi` line (use the `if`-form, not `&&`, because this script runs under `set -e` and the line is not last in the group).
- `STDERR_SINK` is already parsed and validated upstream (`--stderr-sink` at ~line 85, `validate_meta_scalar_path` at ~line 106), so the recorded value is already `.meta`-grammar-safe (single line, no traversal). No new validation here.

### UPDATED: `scripts/lib-external-launcher-common.sh`
- Extend `external_launcher_append_outer_meta` with a trailing 6th positional `local stderr_sink="${6:-}"` (after `risk`).
- Append `STDERR_SINK=<path>` to the meta block after the `OUTER_LAUNCHER_RISK=` line, only when non-empty: `[[ -n "$stderr_sink" ]] && printf 'STDERR_SINK=%s\n' "$stderr_sink"` (this sourced lib runs with no `set -e`, so the `&&` form is fine).
- Keep the existing 4 `OUTER_LAUNCHER_*` lines unchanged; the new line is additive and conditional.

### UPDATED: `scripts/launch-review.sh`
- Both the codex branch and the cursor branch have their own var-init region, argv-parse loop, inner `run-external-agent.sh` call, and `*_launcher_append_outer_meta` call. Apply the change symmetrically to both branches (parity per `.claude/rules/external-tool-launcher-parity.md`).
- Init: add `STDERR_SINK=""` to each branch's init block (codex ~line 100-110; cursor ~line 630-644).
- Parse: add `--stderr-sink) STDERR_SINK="${2:?--stderr-sink requires a value}"; shift 2 ;;` to both argv-parse loops (codex ~line 131; cursor ~line 661), before the `*) unknown flag` arm. This stops the retry forward from hitting `exit 2`.
- Validate the value using `validate_meta_scalar_path` (charset-only allowlist, matching how `--output` is validated in `launch-review.sh`): reject embedded newline/CR before use. Do NOT add a `..` traversal check here — `..` is caught fail-closed by `validate_retry_stderr_sink_or_mark` in `collect-agent-results.sh` (symmetric to `OUTER_LAUNCHER`). Fail with `exit 2` and a `launch-review.sh:`-prefixed message on bad input.
- Thread to the inner launches: after each branch's parse, build `_RUN_EXTERNAL_SINK_ARGS=()` then `[[ -n "$STDERR_SINK" ]] && _RUN_EXTERNAL_SINK_ARGS+=(--stderr-sink "$STDERR_SINK")`. Insert `"${_RUN_EXTERNAL_SINK_ARGS[@]+"${_RUN_EXTERNAL_SINK_ARGS[@]}"}"` into each `"$RUN_EXTERNAL"` invocation after `--timeout "$TIMEOUT"` and before `--` (codex: both the SIDECAR and the `/dev/null` branches, ~lines 529 and 546; cursor: ~line 957, after `--capture-stdout-only`).
- Record in outer-meta: change both append call sites (codex ~line 594, cursor ~line 1010) to pass the sink as the 6th arg with an empty 5th risk arg to preserve the current `${RISK:-high}` default: `…_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-review.sh" "$PROMPT_FILE_SIDECAR" "$PWD" "" "$STDERR_SINK"`.
- Note: for `launch-review.sh`'s current capture modes the threaded sink is inert (codex routes stderr to `${OUTPUT}.sidecar`; cursor uses `--capture-stdout-only`, where the tail selector ignores `explicit_sink`). The change is correct/safe defensive plumbing — accept-and-honor rather than accept-and-ignore — and future-proofs the lane. The functional stderr-preservation win lands in the CMD_JSON path below.

### UPDATED: `scripts/collect-agent-results.sh`
- Parse the field at both `.meta` parse sites: add `META_STDERR_SINK=""` to the reset list and `STDERR_SINK) META_STDERR_SINK="$meta_val" ;;` to the `case` in `parse_retry_meta()` (~lines 504-532) and in the inline empty-output/transient meta parse inside the retry loop (~lines 883-908).
- Add a small validation helper mirroring `validate_retry_timeout_or_mark`: `validate_retry_stderr_sink_or_mark idx orig_output` that, when `META_STDERR_SINK` matches `*..*`, calls `mark_retry_metadata_invalid … "Retry metadata invalid: STDERR_SINK contains .."` and returns 1; else returns 0. This is symmetric to the OUTER_LAUNCHER `..` guard; `run-external-agent.sh` re-validates on the inner call.
- Forward in all four retry sites, only when non-empty, after the validation call:
  - `launch_outer_retry_or_mark()` (~lines 628-642): build `_outer_sink_args=()`; `[[ -n "$META_STDERR_SINK" ]] && _outer_sink_args+=(--stderr-sink "$META_STDERR_SINK")`; add `"${_outer_sink_args[@]+"${_outer_sink_args[@]}"}"` to the `"$META_OUTER_LAUNCHER"` exec after `--prompt-file "$prompt_file"`.
  - inline empty-output outer launch (~lines 998-1022): same array build + insertion into the `"$META_OUTER_LAUNCHER"` exec; on invalid, `continue` (the loop idiom) instead of `return 1`.
  - `launch_cmd_json_retry_or_mark()` `RETRY_ARGS` (~line 669): `[[ -n "$META_STDERR_SINK" ]] && RETRY_ARGS+=(--stderr-sink "$META_STDERR_SINK")` before the `RETRY_ARGS+=(--)` line.
  - inline empty-output CMD_JSON `RETRY_ARGS` (~line 1056): same append before `RETRY_ARGS+=(--)`.
- Keep the duplicated function-vs-inline structure as-is (no refactor); apply the same change to both copies.

### UPDATED: `scripts/run-external-agent.md`
- Document the optional `STDERR_SINK=<path>` base-`.meta` field: written only when `--stderr-sink` is non-empty; consumed by `collect-agent-results.sh` on CMD_JSON retry.

### UPDATED: `scripts/lib-external-launcher-common.md`
- Update the `external_launcher_append_outer_meta` signature to `<meta_path> <outer_launcher_path> <prompt_file_sidecar> <workdir> [risk] [stderr_sink]` and document the optional `STDERR_SINK=` line (written only when the 6th arg is non-empty; empty 5th arg keeps the `high` risk default).

### UPDATED: `scripts/collect-agent-results.md`
- Document `META_STDERR_SINK` parsing at both parse sites, the `..` validation symmetric to `OUTER_LAUNCHER`, and `--stderr-sink` forwarding across both outer-launcher and both CMD_JSON retry paths.

### UPDATED: `scripts/launch-review.md`
- Document the new `--stderr-sink PATH` flag: accepted on both tool lanes, validated, threaded to the inner `run-external-agent.sh`, and recorded in the outer `.meta` for retry round-trip.

### UPDATED: `scripts/test-run-external-agent.sh`
- Assert the base `.meta` includes `STDERR_SINK=<path>` when `--stderr-sink` is passed, and omits the line entirely when it is absent (no-sink byte-stability).

### UPDATED: `scripts/test-lib-external-launcher-common.sh`
- Assert `external_launcher_append_outer_meta` writes `STDERR_SINK=` when the 6th arg is non-empty and omits it when empty/absent; assert the empty 5th risk arg still records `OUTER_LAUNCHER_RISK=high`.

### UPDATED: `scripts/test-launch-review.sh`
- Per `.claude/rules/launcher-argv-test-coverage.md`: assert `--stderr-sink` is accepted (no `exit 2`) on both lanes, that a newline-bearing value is rejected with the exact `launch-review.sh:`-prefixed message + exit code 2 (`..`-only paths are NOT rejected at this layer — `..` is caught only by the collector's `validate_retry_stderr_sink_or_mark`), that the value is threaded to the inner `run-external-agent.sh` argv, and that it lands in the outer `.meta`.

### UPDATED: `scripts/test-collect-agent-retry.sh`
- Assert `--stderr-sink` is forwarded on outer-launcher retry (both the `launch_outer_retry_or_mark()` helper and the inline empty-output path) and on CMD_JSON retry (both `launch_cmd_json_retry_or_mark()` and the inline path); assert a `..` value fails closed via `mark_retry_metadata_invalid`; assert no `--stderr-sink` is forwarded when the field is absent.

### Approach
Wire one optional `.meta` key, `STDERR_SINK`, end-to-end. Two writers record it (the base
writer in `run-external-agent.sh` for direct/CMD_JSON lanes; `external_launcher_append_outer_meta`
for outer-launcher lanes), each only when a sink is set. `collect-agent-results.sh` parses it at
both `.meta` parse sites, validates it like `OUTER_LAUNCHER` (reject `..`), and forwards
`--stderr-sink` in all four retry sites when non-empty. `launch-review.sh` learns the flag so the
outer-launcher forward is accepted instead of dying on `exit 2`. The change is additive and
conditional, so every existing no-sink lane is byte-for-byte unchanged.

### Edge cases
- No sink set (the common case): no `.meta` line, no forwarded flag, behavior identical to today.
- Sink with `..` traversal: collector marks the retry metadata invalid (fail-closed), symmetric to `OUTER_LAUNCHER`; `run-external-agent.sh` re-validates on the inner call.
- `launch-review.sh` sink is inert for its current capture modes (codex → `.sidecar`; cursor → `--capture-stdout-only` `.diag`): the selector only prefers a non-empty sink, so it correctly falls back; the sink still round-trips through meta.
- CMD_JSON retry: `--stderr-sink` is a `run-external-agent.sh` flag (before `--`), not part of `CMD_JSON`, so it is forwarded via `RETRY_ARGS`, not reconstructed from the tool argv.

### Failure modes
1. Forwarding `--stderr-sink` to a launcher that rejects unknown flags → `exit 2`, retry breaks. Mitigation: `launch-review.sh` learns the flag; the CMD_JSON path forwards to `run-external-agent.sh`, which already accepts it. Signal: `test-collect-agent-retry.sh` + `test-launch-review.sh`.
2. `.meta` grammar corruption from a newline-bearing sink value. Mitigation: `validate_meta_scalar_path` in `run-external-agent.sh` and the symmetric guard in `launch-review.sh`; the value is single-line by contract. Signal: meta-write assertions.
3. Parity drift — fixing codex but not cursor, or the function but not the inline copy. Mitigation: apply to both lanes and all four retry sites; harnesses assert both. Signal: `test-launch-review.sh` + `test-collect-agent-retry.sh`.

### Testing strategy
- Extend the four named harnesses (`test-run-external-agent.sh`, `test-lib-external-launcher-common.sh`, `test-launch-review.sh`, `test-collect-agent-retry.sh`) with the accept / omit / forward / reject assertions above.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) after edits: shellcheck, `make lint-bash32`, bare-grep-probe, renderer-substitution-safety, agent-lint S030 pins, and the `.md`-sibling check.

## Acceptance
- `STDERR_SINK=<path>` is recorded in `run-external-agent.sh`'s base `.meta` and by `external_launcher_append_outer_meta`, **only when non-empty**; with no sink set, `.meta` output is byte-identical to before.
- `collect-agent-results.sh` parses `META_STDERR_SINK` at both `.meta` parse sites and forwards `--stderr-sink` (when non-empty) in **all four** retry sites: `launch_outer_retry_or_mark()`, the inline empty-output outer launch, `launch_cmd_json_retry_or_mark()`, and the inline empty-output CMD_JSON path.
- A `..`-bearing `STDERR_SINK` is rejected fail-closed via `validate_retry_stderr_sink_or_mark` → `mark_retry_metadata_invalid` (symmetric to `OUTER_LAUNCHER`).
- `launch-review.sh` accepts `--stderr-sink` on both the codex and cursor lanes (no `exit 2`), validates it via `validate_meta_scalar_path`, threads it to the inner `run-external-agent.sh`, and records it in the outer `.meta`.
- The four regression harnesses assert accept / omit / forward / reject, covering both tool lanes and both function-vs-inline copies.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes: shellcheck, `make lint-bash32`, bare-grep-probe, renderer-substitution-safety, agent-lint S030, and the `.md`-sibling check.

diff_lines: 248
