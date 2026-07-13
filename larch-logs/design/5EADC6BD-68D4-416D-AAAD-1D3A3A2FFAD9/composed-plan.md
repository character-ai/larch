## Plan

## Approach

Extend the scan-only engine with two baseline projections and one guarded comparison/write pipeline.

1. Support exact JSON row shapes:
   - Generic: `path`, `line`, `rule_id`, `message`, and non-empty `reason`.
   - Symbol metric: `path`, `rule_id`, `qualified_symbol`, non-negative `metric`, and non-empty `reason`.
2. Derive generic identity from `(path, line, rule_id, message)`. Derive symbol-metric identity from `(path, rule_id, qualified_symbol)`.
3. In baseline-active check or write modes, project rows before deduplication, reject mixed row shapes and duplicate projected live or baseline identities, and preserve distinct symbol identities. Retain the current scan-only first-win dedupe and rendering behavior when no baseline option is supplied.
4. In check mode:
   - Keep current no-baseline scan behavior unchanged.
   - Treat matching generic rows and symbol metrics at or below baseline as baselined.
   - Treat new identities and metric growth as findings.
   - When `paths=` is supplied, scope baseline matching and stale detection to baseline rows selected by the same file/directory selector semantics as the filtered scan; ignore out-of-scope baseline rows.
   - Emit in-scope stale-row warnings without changing the ordinary finding exit code.
   - Return exit `2` for in-scope stale rows under `strict_stale`.
5. In write mode:
   - Preserve reasons from matching baseline identities.
   - Apply a validated initial reason only to new identities.
   - Refuse the write when any live row lacks a reason.
   - Drop stale rows and serialize live rows in canonical order with a trailing newline.
6. Route baseline reads through `larch.io.read_trusted_text`. Route writes through `larch.io.trusted_atomic_write`, confined to the validated repository root.
7. Re-read the published file through the guarded reader. Re-parse it and require the records and canonical bytes to match the intended baseline. On post-publication validation failure, return an error without attempting rollback.
8. Keep the module unregistered. Do not alter production rules, committed baselines, CLI dispatch, Makefile targets, or CI.

## Files to modify/create

### UPDATED: python/larch/lint/engine.py

- Add typed baseline row and projection helpers for the generic and symbol-metric schemas.
- Validate exact keys, field types, single-line strings, required reasons, and coherent `qualified_symbol` and `metric` use.
- Require generic `line` values to be non-boolean integers greater than or equal to `1`; require symbol metrics to be non-boolean, non-negative integers.
- Parse only a top-level JSON array. Convert JSON, UTF-8, missing-file, unsafe-path, and schema failures into deterministic `ScanError` diagnostics.
- In baseline-active modes, project live findings according to their schema before deduplication or indexing, reject mixed shapes, and detect duplicate projected identities. Keep the existing no-baseline dedupe and sort path unchanged.
- Detect duplicate baseline identities before indexing.
- Compare generic rows by exact identity. Compare symbol-metric rows by stable symbol identity and treat metric growth as a regression.
- For filtered baseline checks, apply the existing path-selector rules to baseline rows before matching and stale comparison, including directory descendants; do not warn or fail for stale rows outside that scope.
- Sort projected rows and diagnostics deterministically.
- Extend `run_rule` with keyword options for the baseline path, write mode, initial reason, and strict stale handling.
- Validate flag combinations before scanning or writing:
  - write mode requires a baseline path;
  - strict stale requires check mode and a baseline;
  - initial reason is write-only and must be non-empty and single-line;
  - reject partial-path baseline regeneration so a filtered scan cannot truncate the full baseline.
- Preserve current `run_rule(rule, root, runner, paths=...)` behavior when no baseline option is supplied.
- Buffer scan and comparison results so validation, strict-stale, or write failures cannot leave partial finding output.
- Emit ordinary findings on stdout and warnings or errors on stderr in stable order.
- Preserve exit codes: `0` for clean or fully baselined results, `1` for new or regressed findings, and `2` for invalid flags, malformed state, strict stale failures, or operational errors.
- Validate baseline paths lexically against the repository root. Reject escapes, symlinked parents or targets, missing parent directories, and non-regular destinations.
- Use `larch.io.trusted_atomic_write` for publication. Then use `larch.io.read_trusted_text` to verify the exact post-write content and parsed records; report read-back failures as exit `2` without rollback.

### UPDATED: python/tests/lint/test_lint_engine.py

- Extend invocation helpers to pass the new `run_rule` keyword options and capture repository state around write tests.
- Cover generic baseline loading, matching, new findings, stale rows, malformed records, required reasons, canonical ordering, and duplicate baseline or live identities.
- Cover generic line validation, including rejecting zero, negative, and boolean values with exit `2`.
- Cover symbol-metric loading and comparison:
  - equal and reduced metrics remain baselined;
  - increased metrics return `1`;
  - missing or invalid symbols and metrics return `2`;
  - duplicate symbol identities return `2`.
- Verify baseline-active projection does not collapse symbol-metric findings that share path, line, rule, or message but have distinct `qualified_symbol` values.
- Verify duplicate live projection identities fail only when a baseline option is active, while existing scan-only duplicate dedupe behavior remains unchanged.
- Verify baseline reasons do not affect identity matching.
- Verify filtered baseline checks scope matching and stale detection to the selected file or directory paths, so an out-of-scope baseline row remains silent and cannot trigger strict-stale failure.
- Verify write mode preserves reasons for matching identities, uses the initial reason only for new identities, removes stale rows, and writes canonical JSON.
- Verify missing reasons abort before publication and leave an existing baseline unchanged.
- Test invalid combinations involving absent baseline paths, strict stale with write mode, initial reasons outside write mode, and filtered writes.
- Pin stale behavior:
  - default mode prints deterministic in-scope warnings but does not fail solely for stale rows;
  - strict mode returns `2`;
  - new findings plus stale rows obey the documented error precedence and stream contract.
- Test guarded write-path failures for:
  - paths outside the repository;
  - `..` escapes;
  - symlinked parent directories;
  - symlink destinations;
  - directory destinations;
  - missing or non-directory parents;
  - post-write read-back mismatch or parse failure.
- Verify pre-publication failures do not modify the prior baseline or leave temporary artifacts. Verify post-publication read-back failures return `2` and do not attempt rollback.
- Verify a successful write creates or replaces only the requested regular baseline file and passes guarded read-back validation.
- Retain the existing scan-only tests to prove backward compatibility.

## Edge cases

- An empty live result may make every in-scope baseline row stale. Warn by default and fail only under strict stale.
- An empty write produces `[]` while dropping old rows.
- Metric changes preserve the reason because symbol identity excludes the metric.
- A valid JSON array with duplicate projected identities is invalid even when duplicate rows are byte-identical.
- A filtered check may use a full baseline: rows outside its selected file or directory scope are ignored for matching and stale detection. Filtered regeneration remains forbidden.
- Atomic publication is followed by guarded read-back validation; a read-back failure reports exit `2` without claiming the prior baseline was restored.

## Failure modes

- Invalid flags, unsafe paths, malformed JSON, invalid schemas, duplicate baseline-active identities, and missing reasons return `2`.
- Strict stale failures return `2` without writing.
- Atomic publication or read-back failure returns `2` and reports the baseline path on stderr.
- New or increased findings return `1` only after the full scan and baseline comparison validate.
- No-baseline scans retain the existing `0`/`1`/`2` behavior and duplicate-dedupe semantics.

## Testing strategy

1. Run `python3 -m pytest python/tests/lint/test_lint_engine.py -q`.
2. Run `(cd python && ruff check larch/lint/engine.py tests/lint/test_lint_engine.py)`.
3. Run `(cd python && ruff format --check larch/lint/engine.py tests/lint/test_lint_engine.py)`.
4. Run the strict pyright check for `larch/lint/engine.py` and `tests/lint/test_lint_engine.py`.
5. Confirm the diff contains only the two firm headings.
6. Confirm no CLI registration, production rule, committed baseline, Makefile target, or CI workflow changed.

## Acceptance

1. Run `python3 -m pytest python/tests/lint/test_lint_engine.py -q`.
2. Run `(cd python && ruff check larch/lint/engine.py tests/lint/test_lint_engine.py)`.
3. Run `(cd python && ruff format --check larch/lint/engine.py tests/lint/test_lint_engine.py)`.
4. Run the strict pyright check for `larch/lint/engine.py` and `tests/lint/test_lint_engine.py`.
5. Confirm the diff contains only the two firm headings.
6. Confirm no CLI registration, production rule, committed baseline, Makefile target, or CI workflow changed.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 750
diff_deleted: 40
mechanical_churn: false
diff_lines: 790
