## Plan

## Approach

- Keep the fix small: one behavioral change in `write_tally_main` for code-review header validation.
- Treat code-review tally body header validation as **best-effort only** for unrecognized headers (`rc == 4`).
- Preserve fatal body-file pre-checks from `_validate_tally_args` (missing file, symlink).
- Preserve fatal `rc == 3` (body read error during header scan) and any other unexpected non-zero validation codes.
- Route ignored-header warnings through `_plain_diagnostic` on **stderr only** (never `logging_util.emit` / stdout KV).
- Preserve `plan-review` behavior unchanged (body required and stored in JSON).
- Keep `review-findings-full.jsonl` composition unchanged.
- Rely on existing cumulative derivation from `_derive_code_review_tally()` over the composed findings file.
- Root cause: round 2+ `flush_review_batches` calls `voting write-tally`, which dies on disallowed `## …` lines copied into `code-review-tally-body.md` by `_build_tally_body()`; round 1 tally lands in the committed log, later flushes fail silently. PR #4584 already aligned one producer source (`## Round` → `# Review Round` in `write_rejected_findings_aggregate`), reducing but not eliminating the freeze; the gate remains fatal for any other disallowed body header, so this change is the complementary writer-side softening (no further producer edits in scope).
- **Test split (accepted review finding):** `flush_review_batches` relays `tally_result.stderr` only when `write-tally` exits non-zero (`review_and_fix.py` ~916–919). After the fix, `write-tally` returns `0` and the warning stays on subprocess stderr only. Verify the warning in `test_voting.py` (direct `write-tally`); do **not** assert stderr in the `flush_review_batches` integration test and do **not** add production stderr relay on success.

## Files to modify/create

### UPDATED: python/voting.py

- In `write_tally_main`, change only the `args.phase == "code-review" and args.body_file` validation branch after `_validate_code_review_headers`:
  - Keep calling `_validate_code_review_headers`.
  - When `rc == 4` (unrecognized section header): emit a compact warning via `_plain_diagnostic`, for example:
    - `WARNING=code-review body header validation ignored: unrecognized section header: ## Foo`
  - Do **not** call `_die` for `rc == 4`.
  - Continue to `compose_tally_record(args)` and the existing `run-log write` path.
  - **Do not** emit the warning through `logging_util.emit`, `logging_util.emit_kv`, or any stdout channel. `write_tally_main` re-emits `run-log write` stdout as `KEY=value` lines; stdout must stay KV-only.
- When `rc == 3` (read error during header scan) or any other unexpected non-zero `rc`, keep the existing `_die` paths unchanged.
- Do not change `_validate_tally_args`.
- Do not change `compose_tally_record` body omission for code-review (`body` stays out of `code-review-tally.json`).
- Do not relax `plan-review` body requirements.

### UPDATED: python/test_voting.py

- Update `test_write_tally_header_validation_and_logger_kv_reemission` or split into focused tests.
- **Invalid code-review body case** (`## Foo` disallowed header):
  - Expect return code `0` (not `2`).
  - Expect the ignored-header warning on **stderr** (match substring like `unrecognized section header: ## Foo`).
  - Expect **empty stdout** aside from re-emitted `LOG_WRITTEN=true` KV from the stub logger (no warning text on stdout).
  - Expect `code-review-tally.json` written under the log root.
  - Assert the JSON record has `schema_version: 2`, `phase: "code-review"`, `batch: "code-review-tally"`, and **no** `body` key.
- Keep a valid code-review write-path assertion (no warning, tally written).
- Keep plan-review coverage proving plan-review writes still include `body`.
- Optionally add or extend quiet-mode coverage confirming `_plain_diagnostic` routing (consistent with `test_quiet_parent_diagnostic_stays_off_stdout` expectations: diagnostic off stdout).
- **This file owns all stderr warning assertions** for the ignored-header path.

### UPDATED: python/test_review_and_fix.py

- Add a Step 5 flush regression test around `flush_review_batches` that exercises the **production** `_build_tally_body` → `write-tally` path (not a direct `compose-tally-record` unit test).
- Suggested shape:
  1. Create an implement tmpdir with `larch-logs/implement/<run_id>/` and `round-1/`, `round-2/` directories.
  2. Stub or monkeypatch the `voting write-tally` / `run-log write` subprocess path only if needed; prefer calling real `flush_review_batches` so `_build_tally_body` and `write_tally_main` both run.
  3. **Round 1 setup:**
     - Write `round-1/review-round-summary.md` with only allowed headers (e.g. `# Review Round 1`, `## Accepted Findings`, `### FINDING_1: …`).
     - Write minimal `round-1/voting-tally.md` (allowed headers only).
     - Create `round1.jsonl` cumulative source with one accepted code-review finding.
     - Call `flush_review_batches(..., rounds=1, composed_findings_source=round1_jsonl)`.
     - Assert success; read `larch-logs/implement/<run_id>/code-review-tally.json`:
       - `rounds == 1`
       - `accepted_count == 1`
       - `rejected_count == 0`
       - no `body` key.
  4. **Round 2 setup (after round-1 flush succeeds):** seed fixtures `_build_tally_body` actually copies into `code-review-tally-body.md`:
     - Write `round-2/review-round-summary.md` containing a **disallowed** header the validator rejects, e.g. a line `## Round 2` (not in `_ALLOWED_CODE_REVIEW_HEADERS` and not matching `# Review Round N`).
     - Write minimal `round-2/voting-tally.md` with allowed headers.
     - Optionally call `write_rejected_findings_aggregate()`; do **not** rely on cumulative JSONL alone to trip the gate (JSONL does not populate the tally body).
  5. Create `round2.jsonl` cumulative source with **two** accepted and **one** rejected code-review finding.
  6. Call `flush_review_batches(..., rounds=2, composed_findings_source=round2_jsonl)`.
  7. Assert (**no stderr warning assertion here** — `flush_review_batches` only forwards `tally_result.stderr` when `write-tally` exits non-zero; post-fix the subprocess succeeds and the warning is not relayed to the caller):
     - Return value is `True` (pre-fix code would return `False` here with `write-tally` rc `2` and leave `rounds: 1`).
     - Final `code-review-tally.json`:
       - `rounds == 2`
       - `accepted_count == 2`
       - `rejected_count == 1`
       - no `body` key.
     - `review-findings-full.jsonl` in the same log dir contains the cumulative records from `round2.jsonl`.
     - Two `round-*` directories remain present under the implement tmpdir.
- Do **not** add a `capsys` / captured-stderr assertion for the ignored-header warning on this path.
- Do **not** change `flush_review_batches` to relay subprocess stderr on success solely to satisfy a test.
- Avoid adding a standalone `/review` integration test.

### UPDATED: docs/run-logs.md

- **Shared tally envelope paragraph** (the block comparing `plan-review-tally.json` and `code-review-tally.json`): clarify that `body` is **phase-dependent**:
  - `plan-review-tally.json` **includes** `body` (plan-review voting prose).
  - `code-review-tally.json` **omits** `body`; the body file is validation input only at write time.
- Rewrite `### code-review-tally.json` to document:
  - Envelope fields: `schema_version`, `phase`, `batch`, `mode`, `rounds`, `accepted_count`, `rejected_count`, `exonerated_count` — **no** `body`.
  - `rounds` is the total number of completed code-review rounds for the run; for normal multi-round `/implement`, it should match the committed `round-*` directory count.
  - `accepted_count` and `rejected_count` are **cumulative across all code-review rounds**, derived from the composed `review-findings-full.jsonl` code-review rows (not round-1-only totals).
  - `exonerated_count` semantics unchanged (informational sub-count of `rejected_count`).
  - Remove or correct prose implying the JSON record stores round-by-round body markdown or rejected-finding prose (that content lives in per-round artifacts and `review-findings-full.jsonl`, not in `code-review-tally.json`).
- Leave `### plan-review-tally.json` body semantics intact.
- Do not change historical committed log behavior; do not require backfills.

## Edge cases

- Missing or symlinked `--body-file` remains fatal through `_validate_tally_args`.
- Unrecognized code-review body headers (`rc == 4`) warn via `_plain_diagnostic` and still write the tally.
- Body read errors during header scan (`rc == 3`) remain fatal.
- Valid code-review bodies write without warning.
- `plan-review` unchanged: body stored in JSON.
- Self-review mode remains accepted for `code-review`.
- Warnings must never appear on stdout KV stream.
- `flush_review_batches` success path does not surface `write-tally` stderr to callers; warning observability is via direct `write-tally` tests only.

## Failure modes

- Emitting the warning on stdout breaks callers parsing `KEY=value` stdout from `write-tally`.
- Removing validation entirely loses diagnostics for unexpected body shapes.
- A test that only calls `compose-tally-record` misses the `write-tally` + `run-log write` failure mode.
- A test that only supplies cumulative JSONL without seeding `round-*/review-round-summary.md` (or other `_build_tally_body` inputs) passes on both pre-fix and post-fix code and does not catch frozen-at-round-1 behavior.
- Asserting ignored-header stderr on `flush_review_batches` fails spuriously post-fix or forces unnecessary production stderr relay on the success path.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_voting.py -k tally` (stderr warning coverage)
  - `python3 -m pytest python/test_review_and_fix.py -k flush_review_batches` (cumulative tally rewrite; no stderr assertion)
- Then run Python validation:
  - `make py-lint`
  - `make py-test`
- Final repository check:
  - `make lint`

## Acceptance

- For a 2+ round regular `/implement` run whose tally body carries a disallowed header, the committed `code-review-tally.json` has `rounds` equal to the committed `round-*` directory count and cumulative `accepted_count` / `rejected_count` across all rounds (not round-1-only).
- `voting write-tally --phase code-review` with an unrecognized body header exits `0`, writes `code-review-tally.json` (no `body` key), and emits the ignored-header warning on stderr only; stdout stays `KEY=value`-only.
- `voting write-tally --phase code-review` still exits non-zero on `rc == 3` body read errors and on `_validate_tally_args` failures (missing / symlinked body file).
- `plan-review-tally` behavior is unchanged: body required and stored in the JSON record.
- `docs/run-logs.md` documents code-review `rounds` = round-dir count, cumulative accepted/rejected semantics, and `code-review-tally.json` body omission; `plan-review-tally.json` body semantics left intact.
- New regression coverage in `python/test_voting.py` (non-fatal ignored header) and `python/test_review_and_fix.py` (multi-round cumulative rewrite) is present and passes.
- `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 3
diff_added: 94
diff_deleted: 21
mechanical_churn: false
diff_lines: 115
