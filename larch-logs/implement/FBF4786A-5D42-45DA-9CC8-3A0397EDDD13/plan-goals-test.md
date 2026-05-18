## Goal
Add dynamic reviewer archetypes to /review: scout-driven, Cursor-primary, max 4 dynamic specialists per run

## Implementation Plan
## Implementation Plan: Dynamic Reviewer Archetypes for /review (scout-driven, Cursor-only, max 4)

### Overview

Add opt-in dynamic specialist reviewer archetypes to `/review`. A Claude Sonnet scout reads the diff once per round dispatch, proposes 0-4 dynamic specialists as JSON, and the panel manifest is extended with Cursor-primary `prompt_file` slots. Default is off (N=0). Static panel behavior is fully preserved when flag/env is absent.

### Files to Create

**`scripts/scout-dynamic-archetypes.sh`**
New script. Claude Sonnet subprocess wrapper:
- Flags: `--mode diff|description` (required), `--diff-file <path>` (required when mode=diff), `--scope-files <path>` (required when mode=description), `--description-text <text>` (required when mode=description), `--plan-file <path>` (optional), `--max-archetypes <N>` (required, 0-4), `--output <path>` (required), `--session-env-path <path>` (optional), `--timeout <seconds>` (optional, default 180).
- Builds scout prompt with `<reviewer_diff>`, `<reviewer_file_list>`, and optional `<reviewer_plan>` wrapping untrusted input; writes to a temp prompt file.
- **Invokes `scripts/launch-claude-subprocess.sh`** (not raw `claude`) with `--model claude-sonnet-4-6`, `--prompt-file`, `--output`, `--timeout`. Uses the existing hardened subprocess wrapper for path validation, read-only preamble, context-file size caps, timing ledger integration, and dirty-tree sidecar. (FINDING_4 fix)
- Parses returned JSON with `jq`; validates schema per rules below.
- On validation failure: writes `{"archetypes":[]}` to `--output`, emits `SCOUT_STATUS=parse-failed`, writes parse error snippet to `${output}.parse-error`.
- Validation rules:
  - `archetypes` array length ≤ 4 (>4 = parse-failed)
  - Each `name` matches `^[a-z][a-z0-9-]{2,40}$` AND is NOT in reserved slugs
  - Duplicate `name` values within one JSON response: reject the duplicate archetype(s), emit WARN, keep first occurrence (FINDING_2 note)
  - `focus_area` must be one of: `code-quality`, `risk-integration`, `correctness`, `architecture`, `security`
  - `weight` is integer ≥ 1 and ≤ 8
  - `rationale` non-empty
  - `prompt_body` non-empty, must not contain any line that is exactly `---` (to avoid corrupting synthesized agent frontmatter — FINDING_8/prompt_body fix), must not contain literal `</reviewer_` closing tags
- Emits KV via `emit_kv`: `SCOUT_STATUS`, `SCOUT_OUTPUT`, `SCOUT_ARCHETYPE_COUNT`, `SCOUT_LATENCY_MS` (from launch-claude-subprocess.sh ELAPSED output). Token counts (`SCOUT_TOKENS_INPUT`, `SCOUT_TOKENS_OUTPUT`) are dropped from the contract — `launch-claude-subprocess.sh` does not emit them. (FINDING_4 resolution)
- Follows `set -euo pipefail`, `source lib-quiet.sh`, `larch_quiet_init` pattern
- Script: `scripts/scout-dynamic-archetypes.sh`

**`scripts/scout-dynamic-archetypes.md`**
Sibling contract doc. Covers: purpose, primary callers (only `dispatch-panel.sh`), invariants (max-4 cap, JSON validation, scout failure non-fatal, dynamic archetypes are EPHEMERAL and bypass `agent-sync` CI job, uses `launch-claude-subprocess.sh` not raw `claude`), harness path, edit-in-sync rules.

**`scripts/test-scout-dynamic-archetypes.sh`**
Regression harness covering:
- Successful scout call with mocked Claude output (4 valid archetypes) → SCOUT_STATUS=ok
- Scout returns >4 archetypes → SCOUT_STATUS=parse-failed
- Scout returns duplicate name → first kept, duplicate rejected, WARN emitted
- Scout returns malformed JSON → SCOUT_STATUS=parse-failed
- Claude subprocess failure → SCOUT_STATUS=claude-failed
- Scout returns 0 archetypes → SCOUT_STATUS=empty
- Scout returns archetype with reserved slug → reject, emit WARN
- Scout returns archetype with invalid `focus_area` → reject
- Scout returns archetype with empty `prompt_body` → reject
- Scout returns `prompt_body` with standalone `---` line → reject that archetype
Mock Claude via fake-claude-output mechanism.

**`scripts/test-scout-dynamic-archetypes.md`**
Sibling stub pointing to `scripts/scout-dynamic-archetypes.md` as primary.

### Files to Modify

**`skills/review/scripts/dispatch-panel.sh`**

1. Add flag: `--dynamic-archetypes <N>` (int 0-4). When absent, also check `LARCH_DYNAMIC_ARCHETYPES_MAX` env; default to 0. Validate: both flag and env must match `^[0-4]$` (digits-only, range 0-4); non-numeric, negative, or values >4 → exit 2 with clear error. The explicit `--dynamic-archetypes` flag overrides `LARCH_DYNAMIC_ARCHETYPES_MAX`. (FINDING_7 fix)
2. Initialize `DYNAMIC_ARCHETYPES=0`, `SCOUT_STATUS=na`, `DYNAMIC_SLOTS=0`, `SCOUT_MANIFEST=`, `STATIC_SLOT_COUNT=0`.
3. Rename `slot_count` to track static-only slots; emit `STATIC_SLOT_COUNT` for static slots and `SLOT_COUNT` as the total (static + dynamic) at the end. (FINDING_8 fix)
4. Add early-exit classifier: if `MODE=diff` and diff file is non-empty, call `${PLUGIN_ROOT}/scripts/classify-diff-mode.sh "$DIFF_FILE"` to get `DIFF_MODE`. If `DIFF_MODE` is `docs-only`, `test-only`, or `generated-only`, skip scout (set `SCOUT_STATUS=skipped-${DIFF_MODE}`, 0 dynamic slots).
5. After existing static slot queuing loops, when `DYNAMIC_ARCHETYPES > 0` and scout not skipped:
   - Check for existing sentinel `$REVIEW_TMPDIR/scout-manifest.json` (once-per-round-dispatch enforcement).
   - If not found: invoke `${PLUGIN_ROOT}/scripts/scout-dynamic-archetypes.sh` with appropriate args; parse `SCOUT_STATUS`, `SCOUT_OUTPUT`, `SCOUT_ARCHETYPE_COUNT` from stdout.
   - For each valid archetype: synthesize ephemeral agent `.md` at `$REVIEW_TMPDIR/dynamic-archetypes/reviewer-dyn-<name>.md`. Run through `render-specialist-prompt.sh`. Queue as Cursor-only `prompt_file` slot:
     ```
     {"slot":"dyn-<name>","tool":"cursor","output":"$REVIEW_TMPDIR/dyn-<name>-output.txt","prompt_file":"<rendered>","weight":<weight>,"focus_area":"<focus_area>"}
     ```
   - Increment dynamic slot counter per queued archetype; add to `SLOT_COUNT` total.
6. Emit at end: `emit_kv SCOUT_STATUS "$SCOUT_STATUS"`, `emit_kv DYNAMIC_SLOTS "$DYNAMIC_SLOTS"`, `emit_kv STATIC_SLOT_COUNT "$static_slot_count"`, `emit_kv SLOT_COUNT "$((static_slot_count + DYNAMIC_SLOTS))"`, and when scout ran: `emit_kv SCOUT_MANIFEST "$REVIEW_TMPDIR/scout-manifest.json"`.
7. `mkdir -p "$REVIEW_TMPDIR/dynamic-archetypes"` before synthesis.

**`skills/review/scripts/dispatch-panel.md`**
Update: document `--dynamic-archetypes`, `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `STATIC_SLOT_COUNT`, `SLOT_COUNT`, `SCOUT_MANIFEST` KV outputs, once-per-round-dispatch sentinel behavior.

**`skills/review/scripts/test-dispatch-panel.sh`**
Extend with:
- `--dynamic-archetypes 0` → baseline manifest unchanged
- `--dynamic-archetypes 4` + mocked scout returning 4 archetypes → 4 additional `prompt_file` slots; `SLOT_COUNT=16` (hard panel), `STATIC_SLOT_COUNT=12`
- `--dynamic-archetypes 4` + mocked scout returning 0 → `SCOUT_STATUS=empty`, no additional slots
- Scout failure → no additional slots, SCOUT_STATUS records failure
- `--dynamic-archetypes 5` → exit 2
- `--dynamic-archetypes -1` → exit 2
- `--dynamic-archetypes abc` → exit 2 (FINDING_7 tests)

**`skills/review/scripts/review-core.sh`**

1. Parse `--dynamic-archetypes <N>` flag. Validate: both flag and env must match `^[0-4]$`; non-numeric, negative, >4 → exit 2. Default 0. Explicit flag overrides env. (FINDING_7 fix)
2. Pass `--dynamic-archetypes "$DYNAMIC_ARCHETYPES"` to `dispatch-panel.sh` in `dispatch_args`.
3. After `dispatch-panel.sh` returns, immediately read `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST` from `dispatch_out` via `kv_get` and store in local variables.
4. **Emit `SCOUT_STATUS` and `DYNAMIC_SLOTS` on ALL post-dispatch exit paths** (zero-findings, panel-failed, main-agent-vote-required, normal end). This means moving the `emit_kv SCOUT_STATUS`/`emit_kv DYNAMIC_SLOTS` calls before the first early exit check, or include them in each exit branch. (FINDING_6 fix)
5. **Persist `scout-status.env`**: after reading `SCOUT_STATUS`/`DYNAMIC_SLOTS` from dispatch, write `$REVIEW_TMPDIR/scout-status.env` with those values so later rounds can read the scout status even when the sentinel manifest is reused.
6. Remove the "log-phase integration" section — `review-core.sh` does NOT call `log-phase.sh`. Instead emit `SCOUT_MANIFEST` and `YIELD_TSV_FILE` as KVs for the wrapper to consume. (FINDING_1 fix)

**`skills/review/scripts/review-core.md`**
Update: document `--dynamic-archetypes` flag; confirm `log-phase.sh` is NOT called from `review-core.sh` (run-log batches remain wrapper-owned); document `DYNAMIC_SLOTS`, `SCOUT_STATUS` in emitted KVs.

**`skills/review/SKILL.md`**

1. Add `--dynamic-archetypes [N]` to the argument-hint frontmatter and flag-parsing prose.
2. Document: once-per-round-dispatch (sentinel file), Cursor-only primary with standard waterfall fallback, max 4, default off, Sonnet scout via `launch-claude-subprocess.sh`, skipped on docs-only/test-only/generated-only diffs.
3. **Add `review-scout-manifest` to Step 4's ordered batch list** (`log-phase.sh` call after tally). The wrapper Step 4 calls `log-phase.sh --batch review-scout-manifest` guarded by `[[ -n "$RUN_ID" ]]` and `[[ -n "$SCOUT_STATUS" && "$SCOUT_STATUS" != "na" ]]`. The wrapper reads `SCOUT_MANIFEST`, `SCOUT_STATUS`, `DYNAMIC_SLOTS`, and `YIELD_TSV_FILE` from `review-core.sh`'s output KVs, assembles a JSON payload, and calls `log-phase.sh`. (FINDING_1 fix)
4. Note: dynamic archetypes are EPHEMERAL and bypass `agent-sync` CI job.

**`skills/review/scripts/tally-code-votes.sh`** (FINDING_2 fix)

1. Add `--manifest-file <path>` optional flag. When provided, read panel manifest NDJSON to build a `basename_to_archetype` mapping keyed by output basename (not slot ID):
   - For each manifest row: `basename(manifest.output)` → `{archetype_name, focus_area, weight}`.
   - For static rows, archetype_name is the basename (e.g. `cursor-specialist-structure-output.txt`). Map to human-readable slug: strip `cursor-specialist-`/`codex-specialist-` prefix and `-output.txt` suffix to get `structure`, `correctness`, etc. Map static slugs to focus_area: `structure`→`code-quality`, `correctness`→`correctness`, `testing`→`risk-integration`, `security`→`security`, `edge-cases`→`correctness`, `plan-fidelity`→`architecture`.
   - For dynamic rows, archetype_name is the `dyn-<name>` slug; weight and focus_area come from the manifest.
   - For simple-panel generalist: `codex-generalist-output.txt` → archetype `generic`, focus_area `code-quality`, weight 1.
   - **Normalize fallback basenames**: when looking up a basename, strip `-phase2`/`-phase3`/`-retry` suffixes before lookup (e.g. `dyn-foo-output-phase2.txt` → `dyn-foo-output.txt` → `dyn-foo`).
2. After the `score_rows` TSV is populated (after the main for-block loop), emit `$REVIEW_TMPDIR/scout-archetype-yield.tsv` when `--manifest-file` is provided:
   - Schema: `archetype_name\tfocus_area\tweight\tfindings_total\tfindings_accepted\tfindings_rejected\tyield_ratio`
   - Group `score_rows` by normalized basename. Static archetypes get `weight=1`. Dynamic archetypes use scout-assigned weight.
   - `yield_ratio = findings_accepted / findings_total` or `n/a` when total=0.
3. Emit `YIELD_TSV_FILE="$REVIEW_TMPDIR/scout-archetype-yield.tsv"` in KV output when written.

**`skills/review/scripts/tally-code-votes.md`**
Update: document `--manifest-file` flag, yield TSV emission, and basename normalization logic.

**`skills/review/scripts/test-tally-code-votes.sh`**
Extend: yield TSV fixture with 1 static + 1 dynamic archetype; test fallback basename normalization (e.g. `dyn-foo-output-phase2.txt` normalizes correctly); test `codex-generalist-output.txt` row.

**`skills/review/scripts/review-core.sh`** (tally integration)
Pass `--manifest-file "$(kv_get "$dispatch_out" PANEL_MANIFEST)"` to `tally-code-votes.sh`.

**`skills/review/scripts/log-phase.sh`**
Register new batch slug `review-scout-manifest` in the `case "$BATCH" in` statement.

**`scripts/larch-log-batches.sh`**

Add `review-scout-manifest .json replace json-object` to the `LARCH_LOG_BATCHES` table. (FINDING_3 fix: use `json-object` sanitizer, not `none`)

**`scripts/larch-log-batches.md`**
Update to document `review-scout-manifest` batch and its single-JSON-object payload schema.

**`scripts/test-larch-logs-batches.sh`**
Add `review-scout-manifest` to the hardcoded sorted `expected` batch list. (FINDING_5 fix)

**`skills/review/scripts/log-phase.md`**
Update: document `review-scout-manifest` batch.

**`skills/review/SKILL.md`** (wrapper Step 4 log-phase call)
In the Step 4 wrapper (which owns `log-phase.sh` calls), add the `review-scout-manifest` batch write after the existing tally batch:
```bash
if [[ -n "$RUN_ID" && "${SCOUT_STATUS:-na}" != "na" ]]; then
  # Assemble JSON payload from scout KVs
  scout_payload_file="$REVIEW_TMPDIR/scout-log-payload.json"
  jq -n \
    --arg status "$SCOUT_STATUS" \
    --argjson dynamic_slots "${DYNAMIC_SLOTS:-0}" \
    --arg manifest_path "${SCOUT_MANIFEST:-}" \
    --arg yield_tsv_path "${YIELD_TSV_FILE:-}" \
    '{"status": $status, "dynamic_slots": $dynamic_slots, "manifest_path": $manifest_path, "yield_tsv_path": $yield_tsv_path}' \
    > "$scout_payload_file"
  skills/review/scripts/log-phase.sh \
    --run-id "$RUN_ID" \
    --batch review-scout-manifest \
    --action write \
    --payload-file "$scout_payload_file"
fi
```

**`scripts/dispatch-with-waterfall.sh`**

Confirm (via a harness test fixture) that optional `weight` and `focus_area` fields already pass jq slot validation without code change. If they do, add only a test case asserting this and make no code change. If validation fails, add explicit typed validation for optional `weight` (integer ≥ 1) and `focus_area` (string). This is verify-first per the nit finding.

**`scripts/test-dispatch-with-waterfall.sh`**
Add test: slot with optional `weight`/`focus_area` fields validates and dispatches identically to slot without those fields.

### Approach

The integration point is the existing NDJSON panel manifest in `dispatch-panel.sh`. Dynamic archetypes are appended after static slots as `prompt_file`-based Cursor slots. The waterfall applies normally (Phase 1 = Cursor, Phase 2 = Codex fallback, Phase 3 = Claude fallback).

The scout is invoked synchronously in `dispatch-panel.sh` via `scripts/launch-claude-subprocess.sh`. This ensures all subprocess hardening (path validation, preamble, timing, dirty-tree sidecar) is applied consistently.

Per-archetype yield TSV is computed in `tally-code-votes.sh` using output basenames as the join key (normalized to strip phase/retry suffixes), with mapping to archetype metadata from the manifest.

`review-core.sh` does NOT call `log-phase.sh`. Run-log batch writing remains wrapper-owned (SKILL.md Step 4). `review-core.sh` emits KVs (`SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, `YIELD_TSV_FILE`) that the wrapper consumes. DYNAMIC_SLOTS/SCOUT_STATUS are emitted on all post-dispatch exit paths.

`review-scout-manifest` is a JSON object batch (`json-object` sanitizer) containing status, dynamic_slots, manifest_path, and yield_tsv_path fields. The three separate files (manifest JSON, status env, yield TSV) remain on disk in `REVIEW_TMPDIR`; the larch-log batch captures a summary reference.

Once-per-round-dispatch: `dispatch-panel.sh` checks for `$REVIEW_TMPDIR/scout-manifest.json`. Under `/implement`, `REVIEW_TMPDIR` changes per round (new `round_dir`), so the scout re-runs each round. This is intentional: the diff changes after fixes, so fresh scout analysis is appropriate. Document this in `dispatch-panel.md`.

### Edge Cases

1. **Empty diff** (mode=diff): classify-diff-mode returns `generic`, scout runs normally.
2. **Doc-only diff**: `SCOUT_STATUS=skipped-docs-only`, 0 dynamic slots.
3. **Scout returns 0 archetypes**: `SCOUT_STATUS=empty`, static panel only.
4. **Scout JSON parse failure**: `SCOUT_STATUS=parse-failed`, empty manifest, panel proceeds.
5. **Scout subprocess failure or timeout**: `SCOUT_STATUS=claude-failed` or `timeout`, panel proceeds.
6. **N > 4 or non-numeric/negative**: Hard exit 2 from both `review-core.sh` and `dispatch-panel.sh`.
7. **Dynamic slot output paths**: named `$REVIEW_TMPDIR/dyn-<name>-output.txt`, matching `*-output.txt` pattern for `collect-findings.sh` and `recover_dirty_tree`.
8. **Fallback output basenames**: `tally-code-votes.sh` normalizes `-phase2`/`-phase3`/`-retry` suffixes before manifest lookup.
9. **Reviewer failure threshold**: `review-core.sh` passes `--launched-slots` as total of static + dynamic launched slots. However, `check-reviewer-failure-threshold.sh` hardcodes intended sizes (12/7). Document that the threshold denominator is anchored to static baseline and dynamic slots are excluded from the denominator — filed as OOS_4 for a follow-up decision.
10. **Zero-findings / panel-failed**: `SCOUT_STATUS` and `DYNAMIC_SLOTS` emitted on all exit paths.

### Failure Modes

1. **Scout failure cascades to panel**: Non-fatal. `SCOUT_STATUS=<error>`, 0 dynamic slots, static panel runs normally.
2. **Injected frontmatter via prompt_body**: Validation rejects any `prompt_body` containing a standalone `---` line, preventing YAML frontmatter corruption in synthesized agent files.
3. **launch-claude-subprocess.sh dirty-tree**: scout runs during an active review session; the subprocess wrapper checks dirty-tree via sidecar before running Claude, consistent with other subprocess calls.

### Testing Strategy

1. `scripts/test-scout-dynamic-archetypes.sh`: scout validation matrix.
2. `skills/review/scripts/test-dispatch-panel.sh`: N=0/4/5/-1/abc, mocked scout with 0/4 archetypes, SLOT_COUNT accuracy.
3. `skills/review/scripts/test-tally-code-votes.sh`: yield TSV, fallback basename normalization, generalist mapping.
4. `scripts/test-dispatch-with-waterfall.sh`: optional field tolerance.
5. `skills/review/scripts/test-log-phase.sh`: `review-scout-manifest` batch registration.
6. `scripts/test-larch-logs-batches.sh`: `review-scout-manifest` in expected sorted list.
7. Manual end-to-end smoke test in PR description.

### Dialectic Resolution Notes

- **DECISION_1** (voted, CHOSEN): Cursor-primary with standard waterfall fallback.
- **DECISION_2** (voted, ALTERNATIVE): Per-archetype yield TSV in `tally-code-votes.sh`.
- **DECISION_3** (fallback-to-synthesis, CHOSEN): Sentinel-file check for once-per-round-dispatch.

### Plan Review Finding Resolutions

- **FINDING_1**: Moved `log-phase.sh` calls to `/review` SKILL wrapper Step 4. `review-core.sh` emits only KVs.
- **FINDING_2**: Manifest-to-archetype mapping uses output basenames with phase/retry suffix normalization; generalist mapping added.
- **FINDING_3**: `review-scout-manifest` uses `json-object` sanitizer; wrapper assembles JSON payload before calling `log-phase.sh`.
- **FINDING_4**: Scout uses `scripts/launch-claude-subprocess.sh`; token count KVs dropped.
- **FINDING_5**: `scripts/test-larch-logs-batches.sh` added to test plan.
- **FINDING_6**: `SCOUT_STATUS`/`DYNAMIC_SLOTS` emitted on all post-dispatch exit paths; `scout-status.env` persisted after dispatch.
- **FINDING_7**: Both flag and env validated as `^[0-4]$`; tests for -1/abc/empty/boundary values.
- **FINDING_8**: Dynamic slots increment total `SLOT_COUNT`; static count tracked separately.

diff_lines: 720

## Test plan
(no test plan section in plan-file)
