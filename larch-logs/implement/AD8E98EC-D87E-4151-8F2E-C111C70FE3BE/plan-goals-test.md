## Goal
Implement issue #3393: [IMPLEMENTING] [BUG] Cursor reviewer slots can return empty .result under the parallel plan-review burst with no transient retry (low-confidence; needs instrumentation)\n\n## Summary.

## Implementation Plan
## Plan

Fix the exit-0 empty-`.result` blind spot entirely in the **cursor launcher layer**, where the empty envelope is produced and where a retry can re-issue the same request. Three pieces, all in `scripts/launch-review.sh`'s `_launch_cursor`:

1. **Instrument** — capture the cursor JSON envelope's diagnostic fields when an empty `.result` is detected, so the next occurrence is diagnosable.
2. **Retry** — treat an exit-0 empty `.result` as a transient condition and retry it (bounded, backoff+jitter), reusing the existing transient-retry budget.
3. **Jitter** — add a per-process pre-spawn delay so parallel cursor slots do not synchronize into a burst.

This placement keeps #3393 in launcher-layer files (`launch-review.sh` + its `.md` + its harness) with **zero file overlap with #3392** (which edits the dispatcher/collector layer). The two compose: #3393 reduces how often an empty reaches #3392's first-line gate, and enriches the `.diag` that #3392's per-slot diagnostic surfaces.

### Design decisions (binding for /implement)

- **Empty vs. no-findings sentinel — the critical correctness invariant.** Retry/diagnostic fire only when `jq -e '(.result // "") == ""'` is true against the envelope JSON — i.e. `.result` is empty, `null`, or absent. The legitimate no-findings result `{"no_issues_found": true}` is a **non-empty `.result` string**, so it is never matched and never retried. Malformed / non-JSON `$OUTPUT` makes the `jq` probe error (false) → not retried via this branch (existing paths still handle it).
- **Reuse the transient budget, do not invent a new one.** The empty-result retry shares `TRANSIENT_ATTEMPT` / `MAX_TRANSIENT_RETRIES=2` and the existing backoff (`LARCH_TRANSIENT_RETRY_DELAY` honored; otherwise `_backoff=$((1<<TRANSIENT_ATTEMPT))` + `RANDOM%2` jitter). Total cursor backend calls stay bounded at 3.
- **Diagnostic is additive — never changes slot classification.** The slot is already dropped today via `CURSOR_EMPTY_RESPONSE` → first-line gate. Writing `.diag` only enriches the failure reason; it must not flip any slot from dropped→OK or OK→dropped.
- **Env gates, default-on, test-disable.** `LARCH_CURSOR_RETRY_EMPTY_RESULT` (default on; `0` disables the retry) and `LARCH_CURSOR_LAUNCH_JITTER_MS` (default `250`; `0` disables jitter). Both are read once.
- **Cursor-only, classified asymmetry.** Codex uses `${OUTPUT}.events.jsonl` + `codex exec --json` (no `.result` envelope), so there is no codex equivalent of this empty-result path. Per `.claude/rules/external-tool-launcher-parity.md`, this asymmetry is intentional and documented — do **not** mirror these branches into the codex launcher. (Codex's separate burst/quota degradation is tracked by #3390.)

### UPDATED: `scripts/launch-review.sh`

All changes are inside `_launch_cursor`.

- **Launch jitter** — immediately before the `while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES ))` loop (~line 978, after the `MAX_*`/`AUTH_ATTEMPT`/`TRANSIENT_ATTEMPT` setup): one-time per-process jittered sleep. Read `LARCH_CURSOR_LAUNCH_JITTER_MS` (default `250`; validate `^[0-9]+$`, else default; `0` skips). Compute a random `0..JITTER_MS` from `RANDOM` and sleep it as fractional seconds, bash-3.2-safe:
  `sec=$((ms/1000)); rem=$((ms%1000)); sleep "$(printf '%d.%03d' "$sec" "$rem")"`.
  Rationale comment: parallel cursor slots are fanned out near-simultaneously by `dispatch-with-waterfall.sh:launch_slot()`; a per-process random delay de-synchronizes backend hits without a coordinator. On Darwin `external_serial_lock_acquire` (~line 980) already serializes cursor ~0.5s apart, so jitter primarily helps non-Darwin/CI; the small default keeps Darwin impact negligible.
- **Empty-result transient retry** — add a new branch in the loop **after** the existing exit-code transient branch (the `if (( EXIT_CODE != 0 … )) && … external_is_transient_infra_failure …` block, ~line 1001-1014) and **before** the auth-retry branch (~line 1015). Condition:
  `EXIT_CODE == 0` **and** `TRANSIENT_ATTEMPT <= MAX_TRANSIENT_RETRIES` **and** `[[ "${LARCH_CURSOR_RETRY_EMPTY_RESULT:-1}" != "0" ]]` **and** `command -v jq` **and** `[[ -s "$OUTPUT" ]]` **and** `jq -e '(.result // "") == ""' "$OUTPUT" >/dev/null 2>&1`.
  On match: `TRANSIENT_ATTEMPT=$((TRANSIENT_ATTEMPT + 1))`, run the same backoff sleep as the exit-code transient branch, `: > "$SIDECAR"`, `continue`. (At this point in the loop `$OUTPUT` still holds the raw wrapper JSON — the `cp`→`.json` and `.result` extraction happen only in the post-loop block — so probing `$OUTPUT` directly is correct.)
  Factor the shared backoff (`LARCH_TRANSIENT_RETRY_DELAY` honored else `1<<TRANSIENT_ATTEMPT` + `RANDOM%2`) into a small local helper (e.g. `_cursor_transient_backoff`) used by both branches so they cannot drift.
- **Envelope diagnostic capture** — in the post-loop `.result` extraction block, at the empty-result detection (~line 1124, the `if jq -e '(.result // "") == ""' "${OUTPUT}.json"` that writes `CURSOR_EMPTY_RESPONSE`): in addition to writing the sentinel to `$OUTPUT`, write `${OUTPUT}.diag` using the existing `TOOL=cursor` / `FAILURE_REASON=…` KV grammar that `collect-agent-results.sh` already consumes. Extract from `${OUTPUT}.json` (the full envelope cp'd at ~line 1081, which survives the `$OUTPUT` overwrite): `type`, `subtype`, `is_error`, `error` message, `usage.inputTokens`/`outputTokens`, and any rate-limit / `duration` / request-id fields present (use `// empty` so absent fields are omitted). Include the transient-attempt count and a pointer to `${OUTPUT}.json`. Example reason: `FAILURE_REASON=cursor-empty-result: exit 0, .result empty/null after N transient retries; type=<…> subtype=<…> is_error=<…> error=<…> usage.outputTokens=<…> (full envelope: <OUTPUT>.json)`. Guard all writes with `2>/dev/null || true` (match the file's defensive sidecar style). Do not gate this capture on the retry env var — diagnostics fire even when retry is disabled.

### UPDATED: `scripts/launch-review.md`

Document, per `.claude/rules/script-md-siblings.md` (same PR): the empty-`.result` transient-retry semantics and the empty-vs-`no_issues_found` invariant; the `${OUTPUT}.diag` envelope capture and that the full envelope persists at `${OUTPUT}.json`; the two new env vars (`LARCH_CURSOR_RETRY_EMPTY_RESULT`, `LARCH_CURSOR_LAUNCH_JITTER_MS`) with defaults and `0`-disables semantics; and the classified cursor-only asymmetry (codex has no `.result` envelope — do not mirror).

### UPDATED: `scripts/test-launch-review.sh`

Mandatory same-PR harness update (`.claude/rules/launcher-argv-test-coverage.md`). Mirror the existing `SL-transient-retry-codex-7` counting-stub pattern (~lines 982-1023) with a **cursor** stub that emits an `--output-format json` envelope, and run every case with `LARCH_TRANSIENT_RETRY_DELAY=0` and `LARCH_CURSOR_LAUNCH_JITTER_MS=0` for determinism:

- **Case: retry-then-success** — stub returns an envelope with empty `.result` on attempt 1, a valid `schema_version…`-leading `.result` on attempt 2. Assert: exit 0, stub invoked exactly 2 times, final `$OUTPUT` is the valid result (not `CURSOR_EMPTY_RESPONSE`).
- **Case: retry-exhausted** — stub returns empty `.result` on every attempt. Assert: stub invoked exactly `MAX_TRANSIENT_RETRIES + 1 = 3` times, final `$OUTPUT == CURSOR_EMPTY_RESPONSE`, and `${OUTPUT}.diag` contains the captured envelope fields (e.g. `cursor-empty-result`, `is_error`, `type`).
- **Case: no-findings sentinel not retried** — stub returns `.result` = `{"no_issues_found": true}`. Assert: stub invoked exactly 1 time, no `CURSOR_EMPTY_RESPONSE`, `$OUTPUT` preserved.
- **Case: retry disabled** — `LARCH_CURSOR_RETRY_EMPTY_RESULT=0` with empty `.result`. Assert: stub invoked exactly 1 time, `$OUTPUT == CURSOR_EMPTY_RESPONSE`, and `${OUTPUT}.diag` is still written (diagnostic is independent of the retry gate).

### UPDATED: `docs/configuration-and-permissions.md`

Add `LARCH_CURSOR_RETRY_EMPTY_RESULT` and `LARCH_CURSOR_LAUNCH_JITTER_MS` to the Environment Variables section (defaults, `0`-disables semantics) so the new knobs are discoverable.

### Not modified (addressing the issue's stated surfaces)

- **`scripts/lib-external-launcher-common.sh` (`external_is_transient_infra_failure`)** — intentionally untouched. That helper keys on exit code (cursor 4/8) + empty *output file*; an exit-0 envelope with empty `.result` does not fit its contract, and bending it there would conflate "exited before producing output" with "exited 0, produced an empty result." The empty-result retry is a dedicated inline branch instead, leaving `test-lib-external-launcher-common.sh` unchanged.
- **`skills/design/scripts/dispatch-plan-review-panel.sh` / `scripts/dispatch-with-waterfall.sh`** — not modified. The issue listed the panel script as the jitter site, but the real fan-out is `launch_slot()` in the waterfall; a per-process jitter in the cursor launcher de-synchronizes the burst regardless of dispatcher and keeps #3393 off the files #3392 edits.

### Edge cases

- `.result` absent / `null` / `""` all collapse via `(.result // "")` → handled identically (retry + diagnostic).
- `{"no_issues_found": true}` and any non-empty `.result` → never retried (non-empty string).
- Malformed / non-JSON `$OUTPUT` → `jq` probe false → not retried by this branch.
- `jq` missing → retry branch and field-extraction skip (guarded by `command -v jq`); behavior degrades to today's (no retry, raw bytes preserved).
- `LARCH_CURSOR_LAUNCH_JITTER_MS` non-numeric or empty → default; `0` → no sleep. Values ≥ 1000 handled by the `sec`/`rem` split.
- Retry succeeds on a later attempt → no `.diag` written (only the terminal still-empty state writes the diagnostic).

### Failure modes

- **Retried-away a real transient but masked a systemic outage** — bounded to 2 retries and the `.diag`/`${OUTPUT}.json` capture still records the terminal envelope, so a persistent backend failure remains visible (warning: a fully-degraded panel; signal: `CURSOR_EMPTY_RESPONSE` + populated `.diag`).
- **Jitter adds latency on the happy path** — default 250 ms once per process, negligible vs. an 1800 s reviewer timeout; `0` disables.
- **`.diag` written on an exit-0 path mis-read as a launch failure** — mitigated by reusing the established KV grammar and not touching `append_launch_failure`; the slot's OK/dropped status is unchanged.

### Testing strategy

`bash scripts/test-launch-review.sh` (cases above) plus `bash scripts/relevant-checks.sh` after the edits. No new external-tool flags are introduced — the retry re-runs the existing `cursor agent -p --trust --mode ask --output-format json` invocation — so no `.claude/rules/verify-external-tool-invocations.md` re-probe is required beyond the existing harness.

### Coordination with #3392 (no hard dependency)

Different layers, no shared files; can land in either order. #3393 writes `${OUTPUT}.diag` in the existing `TOOL=`/`FAILURE_REASON=` grammar so #3392's per-slot diagnostic (which classifies `dropped: empty`) can surface the envelope *why* once it lands. If #3392 changes how `.diag` is read, keep the grammar mutually compatible.

## Acceptance

- [ ] An exit-0 cursor run whose `.result` is empty/null is retried (bounded by `MAX_TRANSIENT_RETRIES`), and a retry that returns a valid `.result` yields exit 0 with the valid result in `$OUTPUT`.
- [ ] A `.result` of `{"no_issues_found": true}` is **not** retried and is preserved unchanged.
- [ ] When all attempts return empty `.result`, `$OUTPUT` is `CURSOR_EMPTY_RESPONSE` and `${OUTPUT}.diag` records the envelope fields (`type`/`subtype`/`is_error`/`error`/`usage`) plus the attempt count, with the full envelope at `${OUTPUT}.json`.
- [ ] `LARCH_CURSOR_RETRY_EMPTY_RESULT=0` disables only the retry (diagnostic still written); `LARCH_CURSOR_LAUNCH_JITTER_MS=0` disables the launch jitter.
- [ ] No changes to `lib-external-launcher-common.sh`, `dispatch-plan-review-panel.sh`, or `dispatch-with-waterfall.sh`; the codex launcher is unchanged.
- [ ] `scripts/test-launch-review.sh` covers retry-then-success, retry-exhausted (+`.diag` assertion), sentinel-not-retried, and retry-disabled; `scripts/launch-review.md` and `docs/configuration-and-permissions.md` updated in the same PR.
- [ ] `bash scripts/relevant-checks.sh` passes.

diff_lines: 180

## Test plan
(no test plan section in plan-file)
