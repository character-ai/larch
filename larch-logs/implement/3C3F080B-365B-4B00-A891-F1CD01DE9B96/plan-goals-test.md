## Goal
Implement issue #4547: [IMPLEMENTING] Eliminate reviewer result-quality retry (ns-retry); warn + tally, no retry.

## Implementation Plan
## Plan

## Approach

- Treat result-quality validation failure (`STATUS=NOT_SUBSTANTIVE`) as **terminal**: warn, tally, drop output, continue. No ns-retry, no voter parse-rate relaunch, no alt-tool waterfall or Claude replacement for content-shape failure.
- Keep **launch-level** retries only: empty output, transient-network diagnostics, auth-startup.
- Ensure `NOT_SUBSTANTIVE` records reach `_emit_records` and downstream tally paths (`COLLECT_FAILURE_COUNT`, `NOT_SUBSTANTIVE_SLOTS`, `effective_judges`) without being upgraded by raw-output heuristics.
- Gate `/review` findings ingestion on collector `STATUS=OK`; skip `NOT_SUBSTANTIVE` narrative files even when still present on disk.
- Gate `/design` plan-review collection the same way in the embedded `plan-review-loop.sh` body: build paths-file / external parse sets from collector `STATUS=OK` only; count `NOT_SUBSTANTIVE` in `COLLECT_FAILURE_COUNT`; write `round-summary.env` from collector evidence, not raw output paths alone.
- **Remove plan-review waterfall first-line format gating** (FINDING_4): do not pass `--require-first-line-pattern` from the embedded `dispatch-plan-review-panel.sh` body. Narrative-first reviewer output must reach collector `--structured-reviewer-validation`, which emits terminal `NOT_SUBSTANTIVE`, instead of triggering phase-2/Claude waterfall fallback that masks result-quality failure.
- Harden round-2+ combined `codex-plan-generic` prompt against narrative output (collector remains authoritative for format failure).
- **Require** `parse_rate_retry_main` as a classify-only compatibility wrapper (FINDING_8): keep the registered `voting parse-rate-retry` CLI entry, accept existing retry args and `--ctx`, ignore retry-only launch data, print bare status, exit 0.
- **Demote retry-only argparse flags to optional no-ops** (FINDING_2): after `dispatch-code-voters.sh` drops `--launch-mode`, `--retry-prefix-kind`, and per-slot `--prompt-file` from classify-only `VPR_ARGS`, `parse_rate_retry_main` must not require them. Make those flags optional with ignored defaults; legacy callers that still pass them must continue to work.
- **Carve `NOT_SUBSTANTIVE` out of Runtime Timeout Fallback / Claude relaunch** (FINDING_1): research and validation must not treat substantive/structured validation failure like a launch failure. For `NOT_SUBSTANTIVE` only: emit warning, map lane status to `fallback_runtime_failed` with sanitized `FAILURE_REASON`, drop output from synthesis/merge eligibility, continue without Claude replacement. Reserve runtime fallback for launch-class failures only (`TIMED_OUT`, `SENTINEL_TIMEOUT`, `EMPTY_OUTPUT`, `FAILED`, `CURSOR_EMPTY_RESPONSE`).
- **Embedded plan-review scripts are gzip blobs only** (FINDING_1 / FINDING_5): `skills/design/scripts/plan-review-loop.sh`, `skills/design/scripts/dispatch-plan-review-panel.sh`, and `scripts/dispatch-plan-voters.sh` have **no on-disk source** in this repo. They live only in `python/plan_review.py` `_LEGACY_ASSETS` (listed in `_RETIRE_DESIGN_SKIPS` / `_RETIRE_ROOT_SKIPS`). Runtime Step 3 executes decoded blob bytes, not standalone paths under `skills/design/scripts/`. All embedded-script edits must be decode → edit → re-encode into `_LEGACY_ASSETS`; `python/test_plan_review.py` string pins are the lint backstop.
- **Research/validation downstream synthesis and merge gating** (FINDING_3): after collection, only `STATUS=OK` external lane outputs (plus pre-launch or launch-class-runtime Claude fallback outputs that legitimately replaced a failed lane) may feed Step 1.5 synthesis or Step 2.4 validation findings merge. `NOT_SUBSTANTIVE` lanes are terminal: lane-status records `fallback_runtime_failed`, narrative files stay on disk for diagnostics but are **omitted** from synthesis `<lane_N_output_path>` tags and validation merge inputs; use an explicit dropped-lane marker in orchestrator prose (e.g. `[lane dropped: collector NOT_SUBSTANTIVE]`) so the synthesis subagent and inline fallback do not Read narrative junk.

### Embedded `_LEGACY_ASSETS` edit workflow (mandatory for plan-review shell)

1. Decode the target asset with `plan_review.legacy_asset_bytes("<rel-path>")` (or equivalent `gzip.decompress(base64.b64decode(...))` against the `_LEGACY_ASSETS` entry).
2. Edit the decoded bash in a temp file. **Do not** create new standalone files under `skills/design/scripts/` expecting runtime to pick them up.
3. Re-encode only the changed entries back into `python/plan_review.py` `_LEGACY_ASSETS` using the existing byte-stable contract: `base64.b64encode(gzip.compress(body, compresslevel=9, mtime=1781390774)).decode("ascii")`, split across string literals per surrounding style. Leave unrelated `_LEGACY_ASSETS` keys untouched.
4. Verify with `PYTHONPATH=python pytest python/test_plan_review.py -k embedded` (or the focused tests named below). Lint cannot see inside gzipped blobs.

**Assets in scope for re-embed this change:**

| `_LEGACY_ASSETS` key | Change |
|---|---|
| `skills/design/scripts/plan-review-loop.sh` | STATUS-gated collection / `round-summary.env` counts |
| `skills/design/scripts/dispatch-plan-review-panel.sh` | Remove `--require-first-line-pattern`; harden `codex-plan-generic` prompt |
| `scripts/dispatch-plan-voters.sh` | Classify-only `voting parse-rate-retry`; no `*plan-voter-prompt-retry.txt` artifacts; drop retry-only argv from classify calls |

## Files to modify/create

### UPDATED: `python/collect_results.py`

- Remove the ns-retry execution stage from `collect_results()`:
  - delete `_collect_ns_retry_plans(...)`
  - delete `_launch_retry_plan(..., strong_prompt=True)` use for `NOT_SUBSTANTIVE`
  - delete `_wait_retry_plans(...)` for ns-retry plans
  - delete `_apply_ns_retry_results(...)`
- Keep `_validate_substantive(...)` and `_validate_structured(...)`.
- Keep the initial launch retry path:
  - `_build_initial_records(...)`
  - `_retry_output_path(output)` default retry suffix
  - `_apply_empty_retry_results(...)`
- Remove dead ns-retry-only helpers once unreferenced:
  - `_COLLECTOR_NS_STRONG_HEADER`
  - `first_pass_sidecar_path`
  - `preserve_and_publish_ns_retry`
  - `_collect_ns_retry_plans`
  - `_apply_ns_retry_results`
  - the `"ns-retry"` call site of `_retry_output_path`
- Keep `derive_ns_retry_reason(...)` if existing audit fields still depend on `NS_RETRY_REASON`.
- Add a small diagnostic helper for `NOT_SUBSTANTIVE` records after validation:
  - emit one warning per dropped reviewer
  - include basename, tool, `NS_RETRY_MODE`, `NS_RETRY_REASON`, and sanitized `FAILURE_REASON`
  - do not mutate the record back to `OK`

### UPDATED: `python/test_collect_results.py`

- Replace `test_non_substantive_retry_publishes_first_pass` with a substantive no-retry test:
  - first-pass narrative output remains unchanged
  - no `*-ns-retry*` output is created
  - no `*-first-pass*` sidecar is created
  - collector emits `STATUS=NOT_SUBSTANTIVE`
  - `NS_RETRY_MODE` and `NS_RETRY_REASON` remain present
  - stderr contains the new warning
- Add `test_structured_validation_not_substantive_no_retry` (FINDING_6):
  - reviewer passes substantive checks but fails structured validation on first pass
  - assert `STATUS=NOT_SUBSTANTIVE`, no `*-ns-retry*` artifacts, no sidecar promotion, stderr warning
  - mirror the substantive narrative fixture pattern
- Keep launch retry tests unchanged.
- Update `test_retry_output_path_non_txt_uses_txt_suffix` to cover only launch retry suffix behavior.

### UPDATED: `python/voting.py`

- Remove voter result relaunch behavior from `parse_rate_retry_main`.
- **Require** `parse_rate_retry_main(...)` remain registered and behave as a classify-only compatibility wrapper (FINDING_8 / FINDING_2):
  - accept existing `parse-rate-retry` arguments including `--ctx` and legacy retry-only args
  - **demote retry-only flags to optional no-ops** (FINDING_2):
    - change `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode` from `required=True` to optional with ignored defaults
    - classify-only callers need only `_parse_rate_common_parser` fields plus `--slot` / `--voter-file` / `--voter-tool`
    - when legacy callers still pass `--prompt-file`, `--retry-prefix-kind`, or `--launch-mode`, accept and ignore them (no argparse error, no relaunch)
  - run only `check_voter_parse_rate(...)`
  - ignore retry-only launch data (no second voter launch, no prompt/output artifacts) regardless of whether optional retry flags are present
  - print bare status (e.g. `NOT_SUBSTANTIVE`) and exit 0
  - do **not** delete the `("voting", "parse-rate-retry")` CLI entry in `python/cli.py`
- Remove retry-only helpers once unreferenced:
  - `VOTER_PARSE_RATE_RETRY_PREFIX_CODE`
  - `VOTER_PARSE_RATE_RETRY_PREFIX_PLAN`
  - `_extract_ctx` (only if unused after wrapper slim-down; keep if still needed to swallow legacy `--ctx` pairs without error)
  - `make_voter_retry_prompt_file`
  - `_retry_output_path` (voter retry variant)
  - `_first_pass_path`
  - `launch_voter_retry`
- Keep `check_voter_parse_rate(...)`.
- Keep parse-rate diagnostics and execution-issues warning append.
- Ensure `NOT_SUBSTANTIVE` means the voter stays in the path file but is excluded from `effective_judges(...)`.

### UPDATED: `scripts/dispatch-code-voters.sh`

- Slim `VPR_ARGS` to classify-only fields (FINDING_2):
  - keep: `--ballot-file`, `--id-grammar`, `--review-tmpdir`, `--plugin-root`, `--dispatch-label`, and optional `--ctx` pairs
  - remove from base `VPR_ARGS`: `--retry-prefix-kind`, `--launch-mode`
- Replace the three `voting parse-rate-retry` calls with classify-only calls:
  - invoke `voting parse-rate-retry` (wrapper) with slim `VPR_ARGS` plus per-slot `--slot`, `--voter-file`, `--voter-tool` only
  - do **not** pass `--prompt-file`, `--retry-prefix-kind`, or `--launch-mode` on classify-only paths
  - extract `PARSE_RATE_STATUS=<status>` safely into `VOTER_N_PARSE_RATE_STATUS` from bare stdout (e.g. `NOT_SUBSTANTIVE`)
- Keep degraded-panel math:
  - parse-rate `NOT_SUBSTANTIVE` must reduce `effective_judges`
  - skipped missing-binary externals must not count as degradation
- Do not remove original narrative voter output.
- Do not write `*-parse-retry*` or `*-first-pass*` artifacts.

### UPDATED: `scripts/test-dispatch-code-voters.sh`

- Rewrite retry sections as no-retry parse-rate sections.
- For prior success fixtures:
  - expect `VOTER_N_PARSE_RATE_STATUS=NOT_SUBSTANTIVE`
  - expect exactly one launch attempt, not two
  - expect original narrative output preserved
  - expect parse-rate diag retained
  - expect no `*-parse-retry*` and no `*-first-pass*`
  - assert classify-only `voting parse-rate-retry` invocations omit `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode`
- Update section names and comments if helpful.
- Keep degraded-panel assertions for failed parse-rate voters.

### UPDATED: `python/test_voting.py`

- Rewrite `parse-rate-retry` success tests unconditionally (FINDING_8):
  - assert parse-rate failure no longer launches a second voter
  - assert command exits 0
  - assert stdout is bare `NOT_SUBSTANTIVE` (or bare status token per contract)
  - assert original voter file is unchanged
  - assert retry prompt/output artifacts are absent
- Add `test_parse_rate_retry_classify_only_dispatch_shaped_argv` (FINDING_2):
  - invoke `voting parse-rate-retry` with dispatch-shaped argv: common parser fields, `--slot`, `--voter-file`, `--voter-tool`, optional `--ctx` pairs
  - omit `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode`
  - narrative voter fixture → exit 0, stdout bare `NOT_SUBSTANTIVE`, no retry artifacts
- Add legacy-argv compatibility test (FINDING_2):
  - same narrative fixture but include `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode`
  - assert identical classify-only behavior (exit 0, bare `NOT_SUBSTANTIVE`, no relaunch, no artifacts)
- Keep `parse-rate-check` tests for diagnostic emission.

### UPDATED: `python/plan_review.py`

**Sole runtime authority** for embedded plan-review loop, panel dispatch, and plan-voter dispatch scripts (FINDING_1 / FINDING_5). On-disk paths under `skills/design/scripts/` for these names do not exist and are not materialized at runtime.

Regenerate gzip/base64 `_LEGACY_ASSETS` payloads for **three** touched embedded scripts via the mandatory decode-edit-reembed workflow above:

1. **`skills/design/scripts/plan-review-loop.sh`** (STATUS-gated collection / `round-summary.env` counts):
   - After `agent collect-results` with `--substantive-validation --validation-mode --structured-reviewer-validation`, persist collector stdout to `collector-results.env` (or equivalent round-local collector record file already used by the loop).
   - Build a `REVIEWER_FILE` → `STATUS` index from collector records (mirror `collect-findings.sh` / `check-reviewer-failure-threshold.sh` parsing).
   - When constructing the round paths-file and external findings parse set:
     - include only outputs whose collector record is `STATUS=OK` (preserve existing `cap_hit` handling if applicable)
     - skip `NOT_SUBSTANTIVE` and all other non-OK externals even when narrative output remains on disk
     - log skipped non-OK records (same spirit as `append_non_ok_collector_results_from_file`)
   - Do not run findings parsers (`parse_output_tsv` / aggregation inputs) on skipped `NOT_SUBSTANTIVE` externals.
   - Compute and write `round-summary.env` counts from collector evidence:
     - `COLLECT_OK_COUNT` = OK slots only
     - `COLLECT_FAILURE_COUNT` increments for each non-OK collector record, including `NOT_SUBSTANTIVE`
   - Keep Claude both-absent generic path behavior unchanged except ensure any collector-emitted `NOT_SUBSTANTIVE` follows the same STATUS-gated ingestion rule.
   - Do not change dispatch topology, voter dispatch, or waterfall fallback rules here; collection/tally ingestion only.

2. **`skills/design/scripts/dispatch-plan-review-panel.sh`** (FINDING_4):
   - **Remove** `--require-first-line-pattern` from the `agent dispatch-waterfall` argv. Plan-review must not pre-drop or waterfall-relaunch narrative-first outputs before collector validation.
   - Harden the `codex-plan-generic` prompt line:
     - combined reviewer must output only the shared TSV header block or JSON no-issues sentinel
     - do not write lens summaries, process narration, or prose before the contract output
   - Apply the same generic prompt hardening to the both-externals-absent Claude generic prompt only if it uses the same fragile combined wording.
   - Do not change dispatch topology or launch-class fallback rules (`--no-fallback` round-1 matrix, round-2+ generic Codex slot, both-absent Claude generic reviewer).

3. **`scripts/dispatch-plan-voters.sh`** (plan-review voter parse-rate classify-only):
   - Replace parse-rate **relaunch** with classify-only `voting parse-rate-retry` (or equivalent classify path through the slimmed wrapper).
   - Slim classify argv the same way as `dispatch-code-voters.sh` (FINDING_2): drop `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode` from classify-only invocations; keep common parser fields plus per-slot `--slot` / `--voter-file` / `--voter-tool`.
   - Remove retry-only args and stop rendering `*plan-voter-prompt-retry.txt` / `*-parse-retry*` / `*-first-pass*` artifacts.
   - Preserve original narrative voter output on disk for diagnostics; exclude parse-rate-failed voters from effective judge math downstream.
   - Keep primary plan-voter prompt rendering (`codex-plan-voter-prompt.txt`, `cursor-plan-voter-prompt.txt`) unchanged aside from removing retry-artifact generation.

- Leave unrelated `_LEGACY_ASSETS` entries untouched.
- No native in-process port of the loop body in this change; `run_plan_review_round()` continues executing the embedded loop.

### UPDATED: `python/test_plan_review.py`

- Extend `test_embedded_plan_review_loop_uses_migrated_collector` (or add sibling) for FINDING_3:
  - decoded `plan-review-loop.sh` still calls `agent collect-results`
  - decoded body gates external parse / paths construction on collector `STATUS=OK`
  - decoded body references `COLLECT_FAILURE_COUNT` / `NOT_SUBSTANTIVE` handling (string pins on the embedded source)
- Extend `test_embedded_waterfall_dispatchers_call_agent_verb` / add focused invariant for `dispatch-plan-review-panel.sh` (FINDING_4):
  - assert generic codex prompt contains `codex-plan-generic`
  - assert output-only TSV/sentinel instruction and no-narrative / no-lens-summary instruction
  - assert decoded waterfall invocation does **not** contain `--require-first-line-pattern`
- Add decode-and-assert coverage for embedded `scripts/dispatch-plan-voters.sh`:
  - decoded body invokes classify-only parse-rate path (no `launch_voter_retry` / no `*plan-voter-prompt-retry*` generation)
  - decoded classify-only `voting parse-rate-retry` calls omit `--prompt-file`, `--retry-prefix-kind`, and `--launch-mode` (FINDING_2)
  - decoded body still renders primary plan-voter prompts
- Add regression test stubbing collector stdout with one `NOT_SUBSTANTIVE` record (FINDING_2 / FINDING_3):
  - assert `round-summary.env` and/or `.step3-review-result.env` records `COLLECT_FAILURE_COUNT=1` (and `COLLECT_OK_COUNT` reflects only OK slots)
  - assert the `NOT_SUBSTANTIVE` slot is omitted from paths-file / findings ingestion when applicable
- Keep existing waterfall dispatcher invariants (`agent dispatch-waterfall`, no retired `dispatch-with-waterfall.sh` path).

### UPDATED: `python/legacy_review_shell/collect-findings.sh`

- After collector success, build the external parse set from `collector-results.env` (FINDING_1):
  - index `REVIEWER_FILE` → `STATUS` from collector records
  - parse only files with `STATUS=OK` (preserve existing `cap_hit` rules if applicable)
  - skip `NOT_SUBSTANTIVE` and other non-OK externals even when narrative remains on disk
  - keep `append_non_ok_collector_results_from_file` logging for skipped records
- Do not run `parse_output_tsv` / `parse_output` on skipped `NOT_SUBSTANTIVE` externals.
- Claude path unchanged except ensure parity if Claude can emit collector `NOT_SUBSTANTIVE`.

### UPDATED: `python/legacy_review_shell/check-reviewer-failure-threshold.sh`

- In the second pass over `--reviewer-output-files`, do not upgrade a basename that already has collector `STATUS=NOT_SUBSTANTIVE` (or other non-OK) via `output_file_is_success` heuristics (FINDING_7):
  - when `counted_status_for_base` is already non-success, skip raw-file upgrade to `OK`
  - preserve `NOT_SUBSTANTIVE_SLOTS` / `FAILED_SLOTS` counts
- Keep first-pass collector parsing unchanged.

### UPDATED: `python/legacy_review_shell/tally-code-votes.sh`

- Verify existing diag-based filtering still counts parse-rate failed voters.
- Adjust comments or warning wording only if they still imply a retry.
- Keep `VOTER_PARSE_FAILED_COUNT` and `EFFECTIVE_VOTERS` behavior.

### UPDATED: `python/test_review_pipeline.py`

- Add/adjust harness coverage for FINDING_1 and FINDING_7:
  - `collect-findings`: narrative external + collector `NOT_SUBSTANTIVE` → logged, absent from findings TSV
  - `check-reviewer-failure-threshold`: collector `NOT_SUBSTANTIVE` + non-empty narrative file → stays failed, not upgraded to `OK`

### UPDATED: `skills/design/references/plan-review.md`

- Document collector behavior:
  - validation failures are warned, counted, and dropped
  - no ns-retry
  - no alt-tool waterfall fallback for result-quality failure
- Distinguish launch fallback (empty/transient/auth) from collector validation (substantive/structured → terminal `NOT_SUBSTANTIVE`).
- Document embedded `plan-review-loop.sh` (via `_LEGACY_ASSETS`) STATUS-gated paths-file / findings ingestion and `COLLECT_FAILURE_COUNT` / `COLLECT_OK_COUNT` semantics.
- Note plan-review dispatch no longer passes `--require-first-line-pattern`; format/result-quality enforcement is collector-side (`NOT_SUBSTANTIVE`), not waterfall pre-gate + relaunch.
- Mention the hardened combined `codex-plan-generic` prompt.
- Note `NOT_SUBSTANTIVE` increments `COLLECT_FAILURE_COUNT`.
- Note embedded scripts are edited only through `python/plan_review.py` `_LEGACY_ASSETS` regeneration, not absent on-disk paths.
- Note plan-voter parse-rate classify calls use slim argv (no `--prompt-file` / `--retry-prefix-kind` / `--launch-mode`); `voting parse-rate-retry` accepts legacy retry flags as optional no-ops.

### UPDATED: `skills/research/references/research-phase.md`

- Update `--substantive-validation` behavior:
  - `NOT_SUBSTANTIVE` is terminal for that lane: warn, tally, drop output from synthesis eligibility, continue
  - map to `fallback_runtime_failed` with sanitized `FAILURE_REASON`; do **not** launch Claude replacement
- Mirror validation-phase collector cleanup (FINDING_2):
  - remove `-ns-retry.txt` and non-substantive-retry sidecar candidate bullets
  - keep only launch-level `${fixed%.txt}-retry.txt` in sidecar candidate expansion
  - remove ingestion language for ns-retry / first-pass promotion artifacts
- Restrict **Runtime-timeout replacement** (FINDING_1):
  - apply only to launch-class collector failures (`TIMED_OUT`, `SENTINEL_TIMEOUT`, `EMPTY_OUTPUT`, `FAILED`, `CURSOR_EMPTY_RESPONSE`)
  - for `NOT_SUBSTANTIVE`: emit warning, set `RESEARCH_*` to `fallback_runtime_failed`, continue without Claude relaunch
- **Synthesis input gating** (FINDING_3):
  - after collection, build per-slot eligibility from collector `STATUS` indexed by `REVIEWER_FILE` / fixed slot path
  - only `STATUS=OK` Codex lane files (or successful launch-retry `*-retry.txt` promoted to OK) may appear in `SYNTHESIS_PROMPT` `<lane_N_output_path>` tags and inline-synthesis Read list
  - for `NOT_SUBSTANTIVE` slots: do **not** pass the narrative fixed-path file to the synthesis subagent; substitute an explicit dropped-lane marker in orchestrator prose (e.g. `[lane dropped: collector NOT_SUBSTANTIVE — <angle name>]`) and exclude that angle from inline-synthesis Read inputs
  - pre-launch Claude fallback outputs and launch-class runtime Claude replacements remain eligible when lane-status shows a legitimate fallback replacement, not `NOT_SUBSTANTIVE`
  - reduced-diversity banner math unchanged: `NOT_SUBSTANTIVE` counts as `fallback_runtime_failed`, incrementing `N_FALLBACK`
- Keep the existing lane-status table row for `NOT_SUBSTANTIVE` → `fallback_runtime_failed`.

### UPDATED: `skills/research/references/validation-phase.md`

- Mirror research-phase wording for validation lanes (FINDING_3):
  - **remove** ns-retry path/sidecar bullets (`*-ns-retry.txt` candidate expansion, non-substantive-retry ingestion)
  - restate `NOT_SUBSTANTIVE` as terminal collector validation (warn + drop + tally)
  - keep only launch-level `-retry.txt` in sidecar candidate expansion
- Restrict **Runtime-timeout replacement** (FINDING_1):
  - apply only to launch-class collector failures (`TIMED_OUT`, `SENTINEL_TIMEOUT`, `EMPTY_OUTPUT`, `FAILED`, `CURSOR_EMPTY_RESPONSE`)
  - for `NOT_SUBSTANTIVE`: emit warning, set `VALIDATION_*` to `fallback_runtime_failed`, continue without Claude relaunch
- **Validation findings merge gating** (FINDING_3):
  - step 4 merge includes only external reviewer outputs whose collector record is `STATUS=OK` (preserve `cap_hit` if applicable)
  - skip `NOT_SUBSTANTIVE` narrative files even when present on disk; log via the same non-OK collector logging spirit as `/review`
  - pre-launch Claude fallback findings and launch-class runtime Claude replacement findings remain merge-eligible
  - negotiation tracks (`codex-negotiation-*`, `cursor-negotiation-*`) run only for OK externals that produced parseable findings
- Keep existing lane status mapping: `NOT_SUBSTANTIVE` → `fallback_runtime_failed` with sanitized `FAILURE_REASON` (no content relaunch).

### UPDATED: `scripts/test-research-structure.sh`

- Remove the `contains` pin at line 249 requiring `-ns-retry.txt` in `validation-phase.md` (FINDING_5), aligned with validation doc cleanup.
- Add pin that `validation-phase.md` documents terminal `NOT_SUBSTANTIVE` and does **not** list `-ns-retry.txt` as an ingest candidate.
- Add pins for `research-phase.md` (FINDING_2):
  - sidecar candidate expansion includes `-retry.txt` but not `-ns-retry.txt`
  - documents terminal `NOT_SUBSTANTIVE` (warn + tally + drop; no ns-retry)
  - runtime-timeout replacement excludes `NOT_SUBSTANTIVE` from Claude relaunch
- Add pins for synthesis/merge gating (FINDING_3):
  - `research-phase.md` documents that `NOT_SUBSTANTIVE` lanes are omitted from synthesis `<lane_N_output_path>` inputs
  - `validation-phase.md` documents that `NOT_SUBSTANTIVE` externals are omitted from validation findings merge

### UPDATED: `skills/shared/external-reviewers.md`

- Update the collector contract:
  - default collector still retries launch-level empty/transient failures
  - `--substantive-validation` and `--structured-reviewer-validation` do not relaunch for content-shape failures
  - `STATUS=NOT_SUBSTANTIVE` is emitted for downstream tally/fallback logic
  - downstream parsers must consult collector `STATUS`, not raw file heuristics alone
- Carve `NOT_SUBSTANTIVE` out of **Runtime Timeout Fallback** / **Runtime Waterfall Fallback** (FINDING_1):
  - split the "any other status" bullet: launch-class failures follow runtime fallback; `NOT_SUBSTANTIVE` is warned, counted, dropped, and does **not** trigger Claude replacement or alt-tool waterfall
  - list launch-class statuses explicitly (`TIMED_OUT`, `SENTINEL_TIMEOUT`, `EMPTY_OUTPUT`, `FAILED`, `CURSOR_EMPTY_RESPONSE`)
- Note plan-review dispatch no longer uses waterfall `--require-first-line-pattern`; format misses surface as collector `NOT_SUBSTANTIVE`, not pre-collector relaunch.
- Note research synthesis and validation merge must gate on collector `STATUS=OK`; `NOT_SUBSTANTIVE` narrative files are diagnostic-only.
- Note `voting parse-rate-retry` is classify-only; retry-only CLI flags are optional no-ops for backward compatibility.

### UPDATED: `docs/external-reviewers.md`

- Update Output Validation:
  - distinguish launch retry from result-quality validation failure
  - remove the statement that `NOT_SUBSTANTIVE` is treated identically to timeout / Claude-subagent fallback
  - note that `NOT_SUBSTANTIVE` is warned, counted as failure/degraded, not retried, excluded from findings ingestion and synthesis/merge inputs, and **not** eligible for Runtime Timeout Fallback / Claude replacement
  - reserve runtime fallback for launch-class collector failures only
- Document plan-review collection STATUS gating (embedded `plan-review-loop.sh` in `_LEGACY_ASSETS`) and removal of waterfall first-line pre-gate for plan review.
- Document `_LEGACY_ASSETS` as the sole edit surface for embedded plan-review shell scripts.
- Document classify-only `voting parse-rate-retry`: dispatch callers omit `--prompt-file` / `--retry-prefix-kind` / `--launch-mode`; wrapper accepts legacy argv without relaunching.

### UPDATED: `scripts/test-prompt-template-invariants.sh`

- Update the `plan-review voter-dispatch` smoke section for classify-only parse-rate behavior (FINDING_3):
  - remove the assertion that `*plan-voter-prompt-retry.txt` must be rendered during voter-dispatch smoke
  - assert primary plan-voter prompts (`codex-plan-voter-prompt.txt`, `cursor-plan-voter-prompt.txt`) still carry `Verify silently` and `Output ONLY vote lines`
  - assert voter-dispatch smoke does **not** create `*plan-voter-prompt-retry.txt` or other parse-rate retry artifacts
- Update section comments to reflect classify-only `voting parse-rate-retry` contract.

### UPDATED: `scripts/test-prompt-template-invariants.md`

- Update the `plan-review voter-dispatch` row:
  - drop `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX` / `make_plan_voter_retry_prompt_file` as required invariants for voter-dispatch smoke
  - document the no-retry-prompt-artifact expectation instead

## Edge cases

- A reviewer can pass substantive validation and fail structured validation; it must become `NOT_SUBSTANTIVE`, not retry.
- A reviewer with missing/invalid retry metadata after empty output must still fail closed through the existing launch retry path.
- Cursor degraded sentinel responses must keep using `CURSOR_EMPTY_RESPONSE`, not `NOT_SUBSTANTIVE`.
- Voter output with parse-rate failure must remain available for diagnostics but excluded from effective quorum.
- Missing-binary voter slots remain `skipped`, not failed.
- Round-2+ plan review still uses one generic Codex slot when both vendors are present.
- Narrative still on disk after `NOT_SUBSTANTIVE` must not be parsed into findings (`collect-findings.sh`, embedded `plan-review-loop.sh`) or upgraded to `OK` (`check-reviewer-failure-threshold.sh`).
- Narrative-first external output that previously failed `--require-first-line-pattern` and waterfall-salvaged/relaunched must now collect once and surface as terminal `NOT_SUBSTANTIVE` (FINDING_4).
- `voting parse-rate-retry` callers passing legacy retry argv (`--prompt-file`, `--retry-prefix-kind`, `--launch-mode`, `--ctx`) must continue to work via classify-only wrapper with no relaunch (FINDING_2 / FINDING_8).
- Dispatch-shaped classify-only argv without `--prompt-file`, `--retry-prefix-kind`, or `--launch-mode` must exit 0 and print bare `NOT_SUBSTANTIVE`, not argparse error (FINDING_2).
- Research/validation lanes with `NOT_SUBSTANTIVE` must update lane-status to `fallback_runtime_failed` but must **not** trigger Runtime Timeout Fallback or Claude replacement (FINDING_1).
- Sidecar ingestion may still read launch-retry outputs (`-retry.txt`) but must not hunt dead `-ns-retry.txt` paths (FINDING_2).
- A research lane with `NOT_SUBSTANTIVE` must not have its narrative file Read by the synthesis subagent or inline fallback; dropped-lane marker only (FINDING_3).
- A validation external with `NOT_SUBSTANTIVE` must not enter findings merge or negotiation even when narrative remains on disk (FINDING_3).
- Editing nonexistent `skills/design/scripts/plan-review-loop.sh` on disk ships no runtime fix; only `_LEGACY_ASSETS` regeneration in `python/plan_review.py` matters (FINDING_1 / FINDING_5).

## Failure modes

- If `NOT_SUBSTANTIVE` no longer reaches collector stdout, downstream failure-threshold checks will undercount failures.
- If `collect-findings.sh` still parses all `EXTERNAL_OUTPUT_FILES`, narrative junk findings will reappear after ns-retry removal.
- If embedded `plan-review-loop.sh` still builds paths-file from raw output paths without STATUS gating, `COLLECT_FAILURE_COUNT` stays 0 and narrative findings re-enter aggregation (#4016 class) (FINDING_3).
- If `check-reviewer-failure-threshold.sh` upgrades collector `NOT_SUBSTANTIVE` from raw file heuristics, tally masking returns (#4016 class).
- If embedded `dispatch-plan-review-panel.sh` still passes `--require-first-line-pattern`, narrative-first outputs trigger waterfall fallback instead of collector `NOT_SUBSTANTIVE`, reintroducing masked relaunches (FINDING_4).
- If `parse_rate_retry_main` still requires `--launch-mode`, `--retry-prefix-kind`, or `--prompt-file` after dispatch slimming, classify-only calls argparse-fail before printing `NOT_SUBSTANTIVE` and voter tally degrades silently (FINDING_2).
- If parse-rate diagnostics are deleted too early, `tally-code-votes.sh` may count a dead voter as effective.
- If embedded plan-review assets are changed without regenerating `_LEGACY_ASSETS`, runtime plan review will still use the old loop/dispatch behavior (FINDING_1 / FINDING_5).
- If an implementer creates new on-disk `skills/design/scripts/*.sh` files without re-embedding, tests may pass on live copies while runtime still executes stale blobs.
- If retry helper removal deletes launch retry code, empty/transient reviewer failures will regress.
- If research/validation docs still mandate Runtime Timeout Fallback for `NOT_SUBSTANTIVE`, operators will relaunch Claude on content-quality failure and mask tally (FINDING_1).
- If synthesis/merge docs omit STATUS gating, orchestrators may still Read `NOT_SUBSTANTIVE` narrative files into synthesis or validation merge (FINDING_3).
- If `validation-phase.md` drops ns-retry bullets but `test-research-structure.sh` still pins them, `make lint` fails on `test-harnesses-7`.
- If `research-phase.md` still documents `-ns-retry.txt` candidates, operators will hunt dead artifacts (FINDING_2).
- If `test-prompt-template-invariants.sh` still requires `*plan-voter-prompt-retry.txt`, `make lint` fails after classify-only voter changes (FINDING_3).
- If `parse-rate-retry` CLI is removed instead of slimmed, external compatibility breaks.
- If embedded `dispatch-plan-voters.sh` is not re-encoded, plan-review voter parse-rate relaunch persists despite `dispatch-code-voters.sh` fix.

## Testing strategy

- Run targeted Python tests:
  - `PYTHONPATH=python pytest python/test_collect_results.py python/test_voting.py python/test_plan_review.py python/test_review_pipeline.py`
  - include FINDING_2 coverage: `pytest python/test_voting.py -k "parse_rate_retry_classify_only or parse_rate_retry"`
- Run targeted shell harnesses:
  - `bash scripts/test-dispatch-code-voters.sh`
  - `bash scripts/test-prompt-template-invariants.sh`
  - `bash scripts/test-research-structure.sh`
- Run required repo checks:
  - `make lint`
  - `make py-lint`
  - `make py-test`
- For manual smoke, inspect a collector block from a narrative reviewer and confirm:
  - `STATUS=NOT_SUBSTANTIVE`
  - warning emitted
  - no `*-ns-retry*`
  - `COLLECT_FAILURE_COUNT` increments in plan-review `round-summary.env`
  - narrative file not ingested as findings
  - plan-review waterfall did not relaunch on first-line format miss
  - research/validation lane does not launch Claude replacement on `NOT_SUBSTANTIVE`
  - research synthesis prompt omits `NOT_SUBSTANTIVE` lane file paths
  - validation merge omits `NOT_SUBSTANTIVE` external findings
  - `/review` voter dispatch: slim `voting parse-rate-retry` argv exits 0 with bare `NOT_SUBSTANTIVE` (no argparse error)

## Acceptance

- A reviewer whose first-pass output fails substantive or structured validation is not re-launched. The collector emits `STATUS=NOT_SUBSTANTIVE`, prints a warning, and drops the output.
- `NOT_SUBSTANTIVE` counts as a reviewer failure: `COLLECT_FAILURE_COUNT` increments in plan-review `round-summary.env`; `check-reviewer-failure-threshold.sh` counts the slot and does not upgrade it to `OK`; the slot is excluded from findings ingestion and from research synthesis / validation merge inputs.
- Launch-level retries still work unchanged: empty output, transient-net signatures, and auth-startup re-launch as before.
- Code voters: `voting parse-rate-retry` is classify-only (no second launch). A parse-rate-failed voter stays on disk for diagnostics but is excluded from `effective_judges`. Legacy retry argv (`--prompt-file`, `--retry-prefix-kind`, `--launch-mode`, `--ctx`) is accepted as optional no-ops, exiting 0 with a bare status token.
- `/research` and `/review` do not Claude-relaunch on `NOT_SUBSTANTIVE`; Runtime Timeout Fallback is reserved for launch-class statuses (`TIMED_OUT`, `SENTINEL_TIMEOUT`, `EMPTY_OUTPUT`, `FAILED`, `CURSOR_EMPTY_RESPONSE`).
- The combined round-2+ `codex-plan-generic` prompt requires structured TSV or the no-issues sentinel only; plan-review dispatch no longer passes `--require-first-line-pattern`.
- Embedded plan-review scripts (`plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, `dispatch-plan-voters.sh`) are edited only via `python/plan_review.py` `_LEGACY_ASSETS` regeneration; no phantom on-disk files are created.
- All checks pass: `make lint`, `make py-lint`, `make py-test`, plus the targeted tests `python/test_collect_results.py`, `python/test_voting.py`, `python/test_plan_review.py`, `python/test_review_pipeline.py`, `scripts/test-dispatch-code-voters.sh`, `scripts/test-prompt-template-invariants.sh`, and `scripts/test-research-structure.sh`.

diff_lines: 1465

## Test plan
(no test plan section in plan-file)
