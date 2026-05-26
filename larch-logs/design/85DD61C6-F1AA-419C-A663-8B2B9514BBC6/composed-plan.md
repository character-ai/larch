## Plan

# Plan — Per-bucket Codex token capture (issue #2813)

## Goal

Eliminate `token-cost.sh`'s `BLENDED_WARN` (`~3-10x` overstatement) for Codex by recording per-bucket Codex token usage (`input`, `cached_input` → `cache_read`, `output`, `total`) wherever Codex is launched. Apply uniformly across all Codex launchers. **Fail-closed semantics**: when Codex JSONL events are unavailable or the parse produces zero usage, skip the token-ledger write entirely (no aggregate fallback). Cache-hit accounting must NOT double-bill: OpenAI's `usage.input_tokens` is gross (includes cached); compute the billable uncached input as `max(input_tokens - cached_tokens, 0)`.

## Approach

The three runtime Codex launchers (`scripts/launch-review.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-codex-ci.sh`) currently scrape `^tokens used$` from Codex's combined stdout/stderr sidecar and record only `total=N` to the token ledger. Replace this with a **shared helper** (`scripts/parse-codex-usage.sh`) driven by Codex's `--json` events stream. Each launcher:

1. Adds `--json` to its `codex exec` invocation so Codex emits JSONL events on stdout.
2. Splits the existing combined-stream outer redirect: stdout (JSONL events) lands in a dedicated `${OUTPUT}.events.jsonl` (or `${TRANSCRIPT_PATH}.events.jsonl`) sidecar; stderr keeps flowing to the existing `$SIDECAR` / `$SIDECAR_LOG` file (auth/transient text classification remains on stderr only — see "Auth/transient classification" below). The agent's last text response continues to land in the `--output-last-message` file unchanged.
3. Before launch, removes any stale `${OUTPUT}.events.jsonl` (or `${TRANSCRIPT_PATH}.events.jsonl`) left by an earlier attempt so the parse never observes phantom usage from a previous run.
4. After the run, invokes `scripts/parse-codex-usage.sh "$EVENTS_FILE"`. On success (exit 0, four KV lines on stdout), parses `INPUT=`, `CACHED_INPUT=`, `OUTPUT=`, `TOTAL=` and writes a per-bucket vendor row. On non-zero exit (helper failure / no usage / total == 0), writes NO token-ledger row and NO `${OUTPUT}.token-record` (fail-closed).
5. When the launcher's existing `SIDECAR == /dev/null` branch (review-codex) is active, the events sidecar is also routed to `/dev/null`; the helper sees a missing/empty file and returns 1; no ledger row. This matches the existing intent of that branch.

Downstream reporting needs no structural change. `scripts/token-report.sh:405` already sums vendor row buckets into `BUCKETS_codex.{input,cached_input,output,total}`. `scripts/render-cost-line.sh:65` already prefers per-bucket flags when their sum > 0. `scripts/token-cost.sh:217` only sets `BLENDED_WARN=true` when a vendor aggregate is > 0 with no per-bucket data — under fail-closed, the aggregate is also 0 on parse failure, so `BLENDED_WARN` does not fire on either branch.

### Auth/transient classification (resolved contract)

The redirect routes Codex stdout (now JSONL events) to `${OUTPUT}.events.jsonl` and leaves Codex stderr at the existing `$SIDECAR` / `$SIDECAR_LOG`. `external_is_auth_failure` and `external_auth_verdict` continue to inspect `$SIDECAR` / `$SIDECAR_LOG` only. **Auth/transient detection is therefore stderr-only after this change.** The plan does NOT require stdout-routed auth-failure classification (Codex CLI emits auth/quota/rate-limit text on stderr in normal failures). Launcher tests assert stderr-routed auth/transient classification still works; no stub is asked to emit auth text on stdout. The launcher .md siblings explicitly document the stderr-only contract.

### Bucket-math contract for the helper

Per OpenAI's `responses` and `chat.completions` schemas (and Codex CLI 0.125's TokenUsage event), `usage.input_tokens` is the **gross** input count and `cached_tokens` / `cached_input_tokens` is a **detail bucket within input_tokens**. The helper MUST compute:

```
uncached_input = max(input_tokens - cached_tokens, 0)
cache_read     = cached_tokens
output         = output_tokens
total          = uncached_input + cache_read + output
```

If `cached_tokens > input_tokens` (shouldn't happen, but defensive against schema drift), the helper exits 1 with stderr `parse-codex-usage.sh: cached_tokens exceeds input_tokens; fail-closed`. The four KV lines emitted on stdout use names `INPUT`, `CACHED_INPUT`, `OUTPUT`, `TOTAL` (downstream `record-vendor codex` maps `CACHED_INPUT` to its `cache_read=` parameter — the bucket the report calls `cached_input`).

### Schema-shape probes (per-field coalesce)

Codex CLI events have evolved across versions. The helper probes per-field with `//` coalesce in fixed precedence order so a single event line never double-counts when both shapes are present on the same object:

```
input_tokens   ← (.msg.usage.input_tokens   // .usage.input_tokens   // 0)
cached_tokens  ← (.msg.usage.cached_input_tokens // .msg.usage.input_tokens_details.cached_tokens
                  // .usage.cached_input_tokens  // .usage.input_tokens_details.cached_tokens // 0)
output_tokens  ← (.msg.usage.output_tokens  // .usage.output_tokens  // 0)
```

This handles three observed shapes: (a) Codex CLI 0.125 native `TokenUsage` (top-level `input_tokens`, `cached_input_tokens`, `output_tokens`, `total_tokens`); (b) OpenAI Responses-style `input_tokens_details.cached_tokens`; (c) future wrapper that nests usage under `.msg.usage`. Per-field coalesce ensures no field is summed from two paths within the same event.

## Files to modify/create

### NEW: `scripts/parse-codex-usage.sh`

Shared helper invoked by all four Codex launcher paths (three runtime launchers + the implement-launcher test harness via in-process stubs). Bash 3.2-compatible per `BASH_AUTHORING.md` §3. Uses `set -euo pipefail`; quiet by default in success path.

Interface:
- **Argv**: one positional argument — path to a Codex JSONL events file (typically `${OUTPUT}.events.jsonl`).
- **Stdout (on success)**: exactly four KV lines in fixed order: `INPUT=<n>`, `CACHED_INPUT=<n>`, `OUTPUT=<n>`, `TOTAL=<n>`. Non-negative integers; `TOTAL = INPUT + CACHED_INPUT + OUTPUT`.
- **Stdout (on failure)**: empty.
- **Exit codes**: `0` on success (parsed, ≥1 usage object summed, `TOTAL > 0`); `1` on every fail-closed branch (file missing/unreadable, `jq` missing, no usage objects, total == 0, `cached_tokens > input_tokens`); `2` on argv/usage error.
- **Implementation**: `jq -nR 'inputs | fromjson? | select(type=="object")'` (line-streaming, NOT `-s` slurp). `fromjson?` silently skips non-JSON lines (wrapper noise) — this is intentional and documented; the plan does not treat malformed JSONL as a hard fail-closed condition. For each parsed object, apply the per-field coalesce probe pattern in "Schema-shape probes" above. Accumulate `input_tokens_sum`, `cached_tokens_sum`, `output_tokens_sum` across the stream. After the loop, apply the bucket-math contract: `uncached_input = max(input_tokens_sum - cached_tokens_sum, 0)`. If `cached_tokens_sum > input_tokens_sum`, exit 1 with stderr diagnostic. If all three sums are zero, exit 1 (no usage data). Otherwise emit the four KV lines.
- **Stderr**: on failure modes, emit one short diagnostic via `larch_err` from `lib-quiet.sh` (one of: `parse-codex-usage.sh: jq not found`, `parse-codex-usage.sh: no usage events`, `parse-codex-usage.sh: events file missing`, `parse-codex-usage.sh: cached_tokens exceeds input_tokens; fail-closed`, `parse-codex-usage.sh: usage error`).

### NEW: `scripts/parse-codex-usage.md`

Sibling contract doc per `.claude/rules/script-md-siblings.md`. Documents: argv signature; stdout grammar (KV lines, exact order, INPUT/CACHED_INPUT/OUTPUT/TOTAL); exit codes; fail-closed contract; the bucket-math `max(input - cached, 0)` rationale citing OpenAI docs; per-field coalesce path order and why three shapes are probed; consumer list (the three runtime launchers + helper test harness + future Codex-CLI smoke). Includes one inline JSONL example with three event shapes.

### NEW: `scripts/test-parse-codex-usage.sh`

Offline harness. Bash 3.2-safe, hermetic. Coverage:
- **Per-bucket sum**, multiple events: input/cached/output summed across rows.
- **Cache-math**: `input_tokens=1000, cached_tokens=900, output_tokens=50` → `INPUT=100, CACHED_INPUT=900, OUTPUT=50, TOTAL=1050` (asserts subtraction).
- **Multiple shapes in one stream**: events using Codex-native `cached_input_tokens` AND events using OpenAI `input_tokens_details.cached_tokens` summed together correctly.
- **`.msg.usage` vs `.usage` per-field coalesce**: single event with both keys present — assert each field comes from one path, not two.
- **Wrapper noise interleaved with valid events**: non-JSON lines silently skipped; valid usage summed.
- **Empty events file** → exit 1, empty stdout.
- **File missing** → exit 1, empty stdout.
- **No `usage` field anywhere** → exit 1.
- **Zero total** (all fields zero) → exit 1.
- **`cached_tokens > input_tokens` defensive case** → exit 1 with diagnostic.
- **Argv error** (no positional) → exit 2.
- **`jq` missing simulation** (PATH stub) → exit 1.
- **Multi-event JSONL via `jq -nR` line streaming**: two real JSONL lines sum correctly (regression for the `jq -s` slurp bug raised in plan review).
- **Codex CLI smoke fixture**: a checked-in real `codex exec --json` output captured from Codex 0.125+ (anonymized; no secrets), proving the parser handles the actual installed CLI's event shape.
- Verify `TOTAL == INPUT + CACHED_INPUT + OUTPUT` on every success fixture.

### NEW: `scripts/test-parse-codex-usage.md`

Sibling doc documenting the harness, fixture shapes, Makefile shard registration (`test-harnesses-17` — the shard that owns token launcher / scraper tests, per `scripts/test-harness-shards-coverage.sh`).

### UPDATED: `scripts/launch-review.sh`

Codex branch only (around lines `492-560`; both `SIDECAR != /dev/null` and `/dev/null` clauses). Cursor branch untouched.

1. **Codex invocation**: add `--json` immediately before the trailing `-- "$PROMPT"`. Keep `--output-last-message "$OUTPUT"` unchanged.
2. **Output redirect**: change `>>"$SIDECAR" 2>&1` (or `>/dev/null 2>&1` in the `/dev/null` branch) to two distinct streams — stdout (JSONL events) → `${OUTPUT}.events.jsonl` (or `/dev/null` in the `/dev/null` branch); stderr → existing `$SIDECAR` (or `/dev/null`). Before the launch, `rm -f "${OUTPUT}.events.jsonl"` so stale events from a previous attempt cannot leak through.
3. **Token capture (replaces lines 556-559)**: remove the `awk '/^tokens used$/'` parse. Call `_codex_usage=$("$PLUGIN_ROOT/scripts/parse-codex-usage.sh" "${OUTPUT}.events.jsonl" 2>/dev/null) || _codex_usage=""`. Skip token-ledger write entirely when `_codex_usage` is empty. Otherwise parse the four KV lines (one shell-safe `while IFS== read -r k v` loop) and call `token-ledger.sh record-vendor codex input="$INPUT" cache_read="$CACHED_INPUT" output="$OUTPUT_T" total="$TOTAL" raw="codex_review"` (NOTE: shell variable `OUTPUT_T` to avoid clashing with the file path `$OUTPUT`).
4. The `/dev/null` branch skips parsing entirely (no events file exists in that mode).

### UPDATED: `scripts/launch-codex-implement.sh`

Lines `321-330` (codex exec invocation) and `354-357` (token capture). Same three-step change as `launch-review.sh`:

1. Add `--json` to the codex exec invocation.
2. Change `>"$SIDECAR_LOG" 2>&1` to `>"${TRANSCRIPT_PATH}.events.jsonl" 2>"$SIDECAR_LOG"`. Pre-launch `rm -f "${TRANSCRIPT_PATH}.events.jsonl"`.
3. Replace the `awk '/^tokens used$/'` + `record-vendor codex total="$N"` block with the helper-driven path. On helper success, call `token-ledger.sh record-vendor codex input=… output=… cache_read=… total=… raw="codex_implement"`. On helper failure, no record. Keep `|| true` swallow on the ledger call so the "best-effort scrape never changes launcher behavior" contract documented in `launch-codex-implement.md` continues to hold.

### UPDATED: `scripts/launch-codex-ci.sh`

Lines `192-204` (codex exec invocation) and `226-230` (token-record write). Same change plus token-record format update:

1. Add `--json` to the codex exec invocation.
2. Change `>"$SIDECAR_LOG" 2>&1` to `>"${OUTPUT}.events.jsonl" 2>"$SIDECAR_LOG"`. Pre-launch `rm -f "${OUTPUT}.events.jsonl"`.
3. Replace the `TOKENS=$(awk '/^tokens used$/ ...')` + `printf 'TOOL=codex\nTOTAL=%s\nRAW=codex_ci_fix\n'` block. On helper success, write the per-bucket KV format (consumed by `append-token-record.sh:48-56`):
   ```
   TOOL=codex
   INPUT=<n>
   OUTPUT=<n>
   CACHE_READ=<n>
   TOTAL=<n>
   RAW=codex_ci_fix
   ```
   On helper failure (no usage): leave `${OUTPUT}.token-record` zero-bytes (the file is already touched empty earlier at line 177; on the success path nothing is written so the file stays zero-bytes). Do NOT write a `TOOL=codex`-only record on failure — `append-token-record.sh` would append a zero-total Codex row, defeating fail-closed.
4. The multi-source awk argument list (`"${OUTPUT}.diag" "$OUTPUT" "$SIDECAR_LOG"`) is removed entirely; the helper reads only `${OUTPUT}.events.jsonl`.

### UPDATED: `scripts/launch-review.md`

Sibling doc for `scripts/launch-review.sh`. Update the Codex sub-section (lines 69-71 currently describe combined stdout/stderr sidecar + `tokens used` scrape). Replace with: `--json` events sidecar at `${OUTPUT}.events.jsonl`, stderr-only `$SIDECAR`, stderr-only auth/transient classification contract, fail-closed token-ledger contract (`parse-codex-usage.sh` exit 0 → record-vendor; non-zero → no record). Reference `scripts/parse-codex-usage.md`.

### UPDATED: `scripts/launch-codex-implement.md`

Sibling doc. Lines `5-8` currently say "wrapper silently scrapes the sidecar for the last `tokens used` block and records a best-effort `codex_implement` vendor total". Replace with the events-sidecar path, per-bucket record-vendor fields, and reaffirm the "best-effort scrape never changes launcher stdout or exit behavior" contract.

### UPDATED: `scripts/launch-codex-ci.md`

Sibling doc. Line ~18 currently references aggregate token capture. Update to describe the events-sidecar path and the per-bucket `${OUTPUT}.token-record` grammar (TOOL/INPUT/OUTPUT/CACHE_READ/TOTAL/RAW lines).

### UPDATED: `scripts/test-launch-review.sh`

The codex stubs in this file print `tokens used\nN\n` (lines 174, 559, 603, 618, 803, 872, 973). For each codex stub:

- Replace the `tokens used` print with a JSONL event line written to STDOUT, shaped to exercise the new helper path. Use the bucket math: e.g. `{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}` → expected `INPUT=100, CACHE_READ=900, OUTPUT=50, TOTAL=1050`.
- Still emit `--output-last-message`-style transcript content to `$OUTPUT` so existing assertions on transcript shape pass.
- Replace ledger-row assertions (`record-vendor codex total=N`) with per-bucket assertions on the codex ledger row: `input=`, `cache_read=`, `output=`, `total=` all present and consistent.
- For the SL-transient-retry stub (line 803-817), the successful attempt emits JSONL on stdout; verify the events file shows the parsed usage exactly once and that auth/transient classification still inspects only `$SIDECAR` (stderr).
- Add one new stub case asserting **stderr-routed auth-failure** detection still classifies (stub writes auth text to stderr, JSONL/nothing to stdout). Do NOT add a "stdout-routed auth text" case — stderr-only is the documented contract.

### UPDATED: `scripts/test-launch-codex-ci.sh`

Update the codex stub: emit JSONL events on stdout (matching the launcher's new redirect). Assertions:
- Success path: `${OUTPUT}.token-record` contains `TOOL=codex`, `INPUT=`, `OUTPUT=`, `CACHE_READ=`, `TOTAL=`, and `RAW=codex_ci_fix`. Run `append-token-record.sh` and verify the appended NDJSON row contains the per-bucket values.
- **Fail-closed path** (stub emits no JSONL events): assert `[[ ! -s "${OUTPUT}.token-record" ]]` (zero-byte exactly — NOT non-empty with TOOL only). Then run `append-token-record.sh` against the empty file and assert NO codex row was appended to the ledger NDJSON.
- Add a stderr-only auth-failure case asserting classification still fires.

### UPDATED: `scripts/test-token-vendor-scrapers.sh`

Two coordinated changes:

1. **Existing top-of-file `codex_scrape` unit tests** (lines 26-45): replace with parse-codex-usage.sh invocations against JSONL fixtures. Remove the legacy awk scrape — that path no longer exists in production code. (Equivalent: replace lines 26-45 with direct calls to the new helper, asserting the same coverage but against the new contract.)

2. **The `launch-codex-implement` smoke** (lines ~100-196, including the `LCI_BIN/codex` stub at ~line 116): update the stub to emit JSONL usage events on stdout (matching the launcher's new redirect), preserve `--output-last-message` transcript write, and replace the `total=7777` jq assertion with per-bucket assertions on `BUCKETS_codex.input/cached_input/output/total`.

3. **End-to-end per-bucket regression** (new): build a synthetic ledger with `record-vendor codex input=100 output=50 cache_read=900 total=1050 raw=codex_implement` rows; run `scripts/token-report.sh --full --format json`; assert `BUCKETS_codex == {input:100, cached_input:900, output:50, total:1050}`. Run `scripts/token-cost.sh` against per-bucket Codex flags; assert stderr does NOT contain `BLENDED_WARN` / `blended rate`.

4. **Existing aggregate-only Codex regression**: retain as documentation of the legacy-shape ledger row that still fires `BLENDED_WARN`. Confirm the new per-bucket path does not regress that branch.

### UPDATED: `scripts/test-token-vendor-scrapers.md`

Sibling doc. Update sections describing "Codex's last `tokens used` block selection" to describe the new `parse-codex-usage.sh`-driven path. The "aggregate-only Codex telemetry" regression description stays (legacy-shape ledger row), but mention it as legacy-only coverage.

### UPDATED: `skills/implement/scripts/test-codex-implementer.sh`

Test 10 (lines 607-666) currently stubs `printf 'tokens used\n7,777\n'` (line 632) and asserts `jq -e '... vendor=="codex" and total==7777 ...'`. Update:

- Stub emits JSONL usage event on stdout matching the new helper path (e.g. `{"msg":{"usage":{"input_tokens":7777,"cached_input_tokens":0,"output_tokens":0}}}`). Still write `--output-last-message` transcript content for downstream assertions that depend on the transcript file.
- Assert `--json` is present in argv shape if the existing test inspects argv (it does in some assertions).
- Replace `total==7777` with per-bucket assertions: `input==7777, cache_read==0, output==0, total==7777`.
- Add a separate fail-closed sub-case where the stub emits no JSONL events; assert NO codex ledger row was appended.

### UPDATED: `Makefile`

Per `scripts/test-harness-shards-coverage.sh` (lines 213-219), every `test-*` target must appear in exactly one `test-harnesses-N` shard. Register:

- Add `test-parse-codex-usage:` recipe (invokes `bash scripts/test-parse-codex-usage.sh`).
- Add `test-parse-codex-usage` to `.PHONY`.
- Add `test-parse-codex-usage` to the `test-harnesses-17` shard prerequisite list (the shard that already owns `test-token-vendor-scrapers`, `test-launch-codex-ci`, `test-launch-review`). Confirm `test-harness-shards-coverage.sh` passes with the new target listed.

### UPDATED: `docs/linting.md`

Brief update to the harness/lint table mentioning `test-parse-codex-usage` and the new per-bucket Codex coverage in `test-token-vendor-scrapers`. Single row addition — discoverability polish.

## Edge cases

- **Codex CLI without `--json` support**: codex exec errors out at startup; stderr → SIDECAR; existing auth/transient detection sees a non-auth, non-transient error; the events sidecar is empty/absent; helper returns 1; no ledger row. Operator sees NO Codex cost line (rather than an inflated aggregate).
- **`jq` missing**: helper exits 1 with stderr diagnostic; launcher writes no ledger row. (jq is a documented hard dependency in `docs/installation-and-setup.md`; this path is informational only.)
- **Mixed-shape JSONL stream** (events with both `.msg.usage` and `.usage` keys, or both `cached_input_tokens` and `input_tokens_details.cached_tokens`): per-field coalesce ensures one value per event per field.
- **Multiple usage events per run** (Codex emits one per `responses` API call): summed across events.
- **`.msg.usage` and `.usage` present on the same event**: per-field `//` coalesce takes the first non-null in the documented precedence; no double-count within an event.
- **Wrapper noise on stdout** (rare under `--json`): `fromjson?` silently skips non-JSON lines; usage events still summed. Plan does NOT classify malformed JSONL as a hard fail-closed condition (the simpler defensive behavior — accept noise, surface only at the "no usage / zero total" boundary).
- **`/dev/null` branch in launch-review.sh** (review-codex with disabled sidecar): events sidecar also routed to `/dev/null`; helper sees missing file; exits 1; no ledger row.
- **Concurrent codex runs**: each launcher allocates its own `${OUTPUT}.events.jsonl` (or `${TRANSCRIPT_PATH}.events.jsonl`); OUTPUT paths are per-task tmpdir-namespaced.
- **`cached_tokens > input_tokens`** (schema-drift defensive case): helper exits 1; no ledger row.
- **Newer Codex schema introducing additional buckets** (e.g. `reasoning_output_tokens`): not in scope. The helper records `output_tokens` only for the OUTPUT bucket; future expansion is a separate issue.

## Failure modes (top 3)

1. **JSONL event-stream shape drift across Codex CLI versions** — the helper probes three known shapes via per-field coalesce, but a future Codex version could rename or move fields further. Earliest warning: `test-parse-codex-usage.sh` Codex-smoke fixture starts failing on a Codex CLI upgrade. Mitigation: fail-closed degrades to "no usage" rather than crashing; backstop test catches drift via the checked-in real-Codex JSONL fixture. A monthly Codex CLI version probe in CI could lift this from "silent" to "loud" but is out of scope.

2. **Stderr-only auth classification misses a future auth-on-stdout regression** — earliest warning: review-loop or implement-loop runs start showing unclassified launcher errors. Mitigation: launcher tests assert stderr-routed auth-failure detection still works. The launcher .md siblings document the stderr-only contract explicitly so future contributors don't reintroduce stdout-merging via `2>&1`. If Codex CLI ever begins routing auth text to stdout under `--json`, fix is to tee non-JSON stdout lines into SIDECAR (a follow-up issue, not this one).

3. **Existing run-log scrape consumers in unrelated tooling** — any other script that grepped sidecar logs for `tokens used` would silently stop finding it. Mitigation verified by the Step 2b codebase probe (only the three runtime launchers and the four test files in scope match). The `codex_scrape` awk function in `test-token-vendor-scrapers.sh:26-45` is the last in-repo consumer; this plan removes it.

## Testing strategy

1. **Helper unit tests** (`test-parse-codex-usage.sh`): all helper success / failure / fail-closed paths, including the cache-math regression, the `jq -nR` line-streaming regression for multi-event JSONL, the per-field coalesce regression, and the checked-in real-Codex JSONL smoke.
2. **End-to-end token-pipeline test** (`test-token-vendor-scrapers.sh` extension): synthetic per-bucket Codex ledger → token-report → token-cost; assert no `BLENDED_WARN` for per-bucket rows and still-fires for legacy aggregate-only rows.
3. **Launcher integration tests** (`test-launch-review.sh`, `test-launch-codex-ci.sh`, `test-codex-implementer.sh`): updated codex stubs emit JSONL; assert per-bucket fields populated on success; assert zero-byte token-record / no ledger row on fail-closed; assert stderr-routed auth/transient classification still fires.
4. **Manual smoke** (operator-level, before merging): run `/design` or `/implement` on any small issue against the real Codex CLI; verify the final-summary cost line no longer shows `BLENDED_WARN` and that `BUCKETS_codex.{input,cached_input,output}` are non-zero in the committed `token-report.json`. Compare against pre-change baseline.
5. **Existing tests** continue to pass: `make lint`, `make test-harnesses-17` (the shard that owns the new helper + all four updated test files), `test-token-ledger`, `test-token-report`, `test-token-cost-per-bucket`, `test-codex-implementer`. The `test-harness-shards-coverage.sh` check passes with `test-parse-codex-usage` registered in `test-harnesses-17`.

## Acceptance

- All three runtime Codex launchers (`scripts/launch-review.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-codex-ci.sh`) emit JSONL events via `codex exec --json` and call `scripts/parse-codex-usage.sh` to record per-bucket Codex tokens (input/cache_read/output/total). On parse failure: no token-ledger row (fail-closed).
- New `scripts/parse-codex-usage.sh` with sibling `scripts/parse-codex-usage.md` and offline harness `scripts/test-parse-codex-usage.sh` (+ sibling `.md`); harness registered in `Makefile` `test-harnesses-17` shard.
- Bucket math: `uncached_input = max(input_tokens - cached_tokens, 0)`; cached tokens are NOT double-billed.
- Per-field coalesce probes both `.msg.usage` and `.usage` paths plus both `cached_input_tokens` and `input_tokens_details.cached_tokens` schemas; jq invocation uses `jq -nR 'inputs | fromjson? | select(type=="object")'` (line-streaming, NOT slurp).
- Existing test harnesses updated: `scripts/test-launch-review.sh`, `scripts/test-launch-codex-ci.sh`, `scripts/test-token-vendor-scrapers.sh` (+ sibling `.md`), `skills/implement/scripts/test-codex-implementer.sh`. Codex stubs emit JSONL usage events instead of `tokens used` text; assertions check per-bucket ledger fields.
- Auth/transient classification is stderr-only after this change; launcher `.md` siblings (`launch-review.md`, `launch-codex-implement.md`, `launch-codex-ci.md`) document the new contract.
- End-to-end regression in `test-token-vendor-scrapers.sh`: per-bucket Codex ledger row → token-report → token-cost does NOT emit `BLENDED_WARN`.
- `docs/linting.md` lists `make test-parse-codex-usage` and per-bucket Codex coverage in `test-token-vendor-scrapers`.

diff_lines: 540
