## Goal
Implement issue #6164: [IMPLEMENTING] md-to-py-XII: measure realized checks-digest savings; extend to design validator loop if positive.

## Implementation Plan
## Plan

## Approach

Instrument now. Measure later.

Keep the change content-free and best-effort. Each real checks failure that writes a digest should also append one TSV row with only counts and safe identifiers. The parent checks flow must still succeed or fail exactly as it does today if telemetry cannot be written.

## Files to modify/create

### UPDATED: python/larch/implement/checks_run_relevant.py

- Add a small content-free telemetry writer at the shared digest point, `_write_failure_digest_from_redacted`.
- After the digest file is written, compute:
  - redacted log byte count
  - digest byte count
  - estimated redacted tokens
  - estimated digest tokens
  - byte and token savings
- Append one row to `checks-digest-sizes.tsv` under the active committed run tree:
  - `canonical_tmp/larch-logs/implement/<RUN_ID>/checks-digest-sizes.tsv`
  - `canonical_tmp/larch-logs/review/<RUN_ID>/checks-digest-sizes.tsv`
- Resolve the destination only when exactly one matching run directory exists. If none or more than one exists, skip telemetry.
- Use a locked TSV append with a header, matching the `panel-prompt-sizes.tsv` best-effort style.
- Store only fields like `site`, `attempt`, `redacted_bytes`, `digest_bytes`, `redacted_tokens`, `digest_tokens`, `saved_bytes`, `saved_tokens`, and `digest_truncated`. `saved_bytes` and `saved_tokens` are signed (`redacted - digest`) and may be negative when a digest is larger than a tiny redacted log; write the true signed value, do not clamp or drop negative rows.
- Do not store log text, digest text, absolute paths, prompts, commands, or failure lines.
- Catch telemetry exceptions and print a warning to stderr. Do not alter the checks result or `DIGEST_FILE` envelope.

### UPDATED: python/larch/report/tokens.py

- Add constants and row parsing for `checks-digest-sizes.tsv`.
- Add `measure_checks_digest_savings()`.
- Scan committed files under `larch-logs/implement/*/checks-digest-sizes.tsv` and `larch-logs/review/*/checks-digest-sizes.tsv`.
- Skip symlinks, malformed rows, and rows with a missing header.
- Validate `redacted_bytes`, `digest_bytes`, `redacted_tokens`, and `digest_tokens` as non-negative (unsigned) integers; skip the row if any of these are missing, non-numeric, or negative.
- Validate `saved_bytes` and `saved_tokens` as signed integers: accept negative values (parse with an optional leading `-`); do not reject or clamp negative savings, since those rows are required evidence for a no-go outcome.
- Write a stamped TSV report under `larch-logs/measure-checks-digest-savings/`.
- Report `status=insufficient-data` until at least 5 valid rows exist.
- Once at least 5 rows exist, report aggregate totals (computed from the signed per-row `saved_bytes` / `saved_tokens`, without discarding negative rows) and a recommendation:
  - positive savings: `recommendation=go-design-validator-extension`
  - zero or negative savings: `recommendation=no-go-design-validator-extension`
- Keep the output count-only. Do not read or emit log or digest contents.

### UPDATED: python/larch/report/gc_run_logs.py

- Add `"checks-digest-sizes.tsv"` to `SKILL_KEEP["implement"]` and `SKILL_KEEP["review"]` so `/gc-run-logs`'s default 90-day age-based slim does not delete telemetry rows before enough real samples accumulate for the aggregator threshold.

### UPDATED: python/larch/cli.py

- Register `python3 python/cli.py token measure-checks-digest-savings`.
- Point it at the new `tokens.py` main function.

### UPDATED: python/larch/report/run_log_batch.py

- Register `checks-digest-sizes` as a TSV run-log batch with `append` mode and `none` sanitizer.
- Keep the registry entry aligned with the committed filename `checks-digest-sizes.tsv`.

### UPDATED: python/tests/implement/test_checks.py

- Add coverage that `_write_failure_digest_from_redacted` writes the digest and appends exactly one count-only telemetry row when a unique run directory exists.
- Assert the TSV does not contain raw failure text, digest text, redacted log text, or absolute tmpdir paths.
- Add coverage that telemetry is skipped without failing digest creation when the run directory is missing or ambiguous.

### UPDATED: python/tests/report/test_tokens.py

- Add aggregator tests for:
  - fewer than 5 valid rows emits `insufficient-data`
  - 5 or more rows with positive savings emits the go recommendation
  - 5 or more rows with zero or negative savings emits the no-go recommendation
  - symlinked or malformed TSVs are skipped
  - a row with a negative `saved_bytes` / `saved_tokens` value is accepted and included in the aggregate, not skipped
  - a row with a negative `redacted_bytes`, `digest_bytes`, `redacted_tokens`, or `digest_tokens` value is skipped (those columns stay unsigned-only)
- Assert the report contains only counts, statuses, and safe identifiers.

### UPDATED: python/tests/report/test_run_logs.py

- Add or update registry coverage for the new `checks-digest-sizes` batch.
- Verify append-mode behavior is accepted for a TSV payload if existing run-log batch tests cover this pattern.

### UPDATED: python/tests/report/test_gc_run_logs.py

- Add coverage that `checks-digest-sizes.tsv` survives age-based slimming for both `implement` and `review` skill directories (present in `SKILL_KEEP` for each).

### UPDATED: docs/run-logs.md

- Document `checks-digest-sizes.tsv` in the implement and review run-log surfaces.
- State that it records only byte and estimated-token counts for redacted logs versus generated digests, and that `saved_bytes` / `saved_tokens` are signed and may be negative.
- Document `python3 python/cli.py token measure-checks-digest-savings`, its insufficient-data threshold of 5 samples, and its go/no-go rule.
- State that the design validator digest extension remains gated on a future positive measurement.
- Add `checks-digest-sizes.tsv` to the Retention section's `/implement` and `/design`-analogous `/review` keep-set description so it is not slimmed away before enough samples accrue.

### UPDATED: docs/run-log-batches.md

- Add `checks-digest-sizes` to the run-log batch registry description.
- Note that the batch is append-mode TSV and content-free.

## Edge cases

- If digest creation fails, do not write telemetry.
- If the redacted log cannot be read, keep the current `None` digest behavior.
- If no committed run-log directory has been initialized yet, skip telemetry.
- If multiple run-log directories exist under the tmpdir, skip telemetry to avoid attributing data to the wrong run.
- If a TSV has a header but bad rows, ignore bad rows and keep valid rows.
- If fewer than 5 valid samples exist, the aggregator must not issue a go/no-go recommendation.
- A row whose `saved_bytes` or `saved_tokens` is negative is valid evidence, not a malformed row; the parser must accept it.

## Failure modes

- Telemetry lock or write failure: print a warning and continue.
- Malformed committed TSV: skip the bad row or file and continue.
- Aggregator output write failure: surface the normal CLI failure.
- Negative savings can happen if a digest is larger than a tiny redacted log. Preserve that data (the parser must not treat it as malformed) and let the aggregate decide the recommendation.
- Without the GC keep-set update, historical telemetry older than the default 90-day retention window would be slimmed away, permanently losing early samples toward the 5-sample threshold.

## Testing strategy

Run targeted Python tests only:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "digest"
python3 -m pytest python/tests/report/test_tokens.py -k "checks_digest or measure_checks_digest"
python3 -m pytest python/tests/report/test_run_logs.py -k "checks_digest or batch"
python3 -m pytest python/tests/report/test_gc_run_logs.py -k "checks_digest"
```

If the touched Python files trigger broader relevant checks, run:

python3 python/cli.py checks run-relevant --site step6 --tmpdir "$IMPLEMENT_TMPDIR" --repo-root "$PWD"

## Done criteria

- Real future `/implement` and `/review` checks failures can accrue committed `checks-digest-sizes.tsv` rows.
- Those rows survive default-policy `/gc-run-logs` slimming until the aggregator has had a chance to read them.
- The new aggregator reports insufficient data until at least 5 samples exist, and computes its recommendation from the signed per-row savings once it has enough.
- The PR references #6164 but does not close it.
- No design-validator digest wiring is added in this change.

## Acceptance

Run targeted Python tests only:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "digest"
python3 -m pytest python/tests/report/test_tokens.py -k "checks_digest or measure_checks_digest"
python3 -m pytest python/tests/report/test_run_logs.py -k "checks_digest or batch"
python3 -m pytest python/tests/report/test_gc_run_logs.py -k "checks_digest"
```

If the touched Python files trigger broader relevant checks, run:

python3 python/cli.py checks run-relevant --site step6 --tmpdir "$IMPLEMENT_TMPDIR" --repo-root "$PWD"

diff_lines: 520

## Test plan
(no test plan section in plan-file)
