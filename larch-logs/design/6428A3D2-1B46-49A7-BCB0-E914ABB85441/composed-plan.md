## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Use the approved outline and discussion resolutions as scope.
- Keep the shared validation path fail-closed for `classify` and `compose-report`.
- Make `--failure-detail-log` strictly optional on `record-escalation`: validation misses must never abort the escalation ledger.
- Branch `record_escalation` on a classifier helper before any attachment decision:
  - Valid log: attach tmpdir-relative path as today.
  - Oversize: best-effort truncate into a tmpdir-local sidecar; attach the sidecar on success.
  - Any other invalid cause, or oversize sidecar materialization failure: record the ledger => row with an empty `failure_detail_log` and a `detail_log_skipped=failure-detail-log-<cause>` field naming the specific reason.
- Reserve `hard_fail(...)` only for cases where escalation evidence cannot be recorded at all:
  - Token validation failures (`site`, `trigger`, `step`, `phase`).
  - Unsafe or unwritable ledger, fallback, or marker paths (`ledger-path-invalid`, `fallback-path-invalid`).
  - Total recording failure after the canonical-ledger append raises `OSError` **and** fallback/marker writes cannot proceed.
  - Never call `hard_fail` for optional detail-log validation misses.
- **Do not change the canonical-ledger fallback success path.** When `_append_ledger_row_atomic` fails or the ledger is not writable, the existing `except OSError` block must still write the record-failure marker and fallback TSV row, emit `ESCALATION_RECORDED=false` / `ESCALATION_FALLBACK_WRITTEN=true`, and **return `0`**. A canonical-ledger append failure is not a `hard_fail` case when fallback succeeds.
- Remove the generic `failure-detail-log-invalid` token from the `record-escalation` path.
- Keep `classify` and `compose-report` soft-skip behavior unchanged: invalid or oversize detail logs are omitted from classification output and Tier A report sections without changing exit semantics.
- Keep `checks.py` containment fixes so lint-fix never emits an outside-tmpdir `ledger_failure_detail_log` in the first place.

## Files to modify/create

### UPDATED: `python/larch/state/stall_recovery.py`

- Add `classify_failure_detail_log(*, tmpdir: Path, path: Path) -> str`.
  - Return `""` when the path is attachable as-is (absolute, inside tmpdir, regular file, not symlink, readable, size `<= MAX_OPTIONAL_EVIDENCE_BYTES`).
  - Return specific suffix tokens for misses:
    - `non-absolute`
    - `symlink`
    - `outside-tmpdir`
    - `missing`
    - `not-regular-file`
    - `oversize`
    - `unreadable`
  - Preserve existing stderr text byte-compatible where current tests assert it. Factor message printing into shared helpers so `validate_failure_detail_log` and the classifier stay aligned.
- Keep `validate_failure_detail_log(...) -> bool` as a thin wrapper over the classifier.
  - Print the same messages currently used by `classify` and `compose-report`.
  - Return `False` on any non-empty classifier suffix, including oversize.
- Keep `_read_validated_failure_detail_log(...)` soft-skip behavior unchanged.
  - `classify` still exits 0 and omits `FAILURE_DETAIL_LOG` for invalid detail logs.
  - `compose-report` still omits the validated detail-log section for oversize or otherwise invalid logs.
- Add a small sidecar helper used only from `record_escalation` for oversize logs.
  - Read source with no-follow semantics where available.
  - Copy only the first `MAX_OPTIONAL_EVIDENCE_BYTES`.
  - Write under `tmpdir` with a stable unique name, such as a digest of source path plus size.
  - Re-verify the sidecar is inside tmpdir, not a symlink, regular, and within the cap before returning its relative path.
  - Return `None` on any materialization or re-verification failure (best-effort only).
- Update `record_escalation(...)`.
  - When `--failure-detail-log` is absent or empty: keep current behavior (`failure_detail_log=` empty, no skip field).
  - When present:
    1. Call `classify_failure_detail_log`.
    2. If classifier returns `""`: resolve and record the tmpdir-relative source path in `failure_detail_log`; leave `detail_log_skipped` absent/empty.
    3. If classifier returns `oversize`: call the sidecar helper.
       - On success: record the sidecar relative path in `failure_detail_log`; leave `detail_log_skipped` absent/empty.
       - On failure: leave `failure_detail_log` empty; set `detail_log_skipped=failure-detail-log-truncate-failed`.
    4. For every other classifier suffix: leave `failure_detail_log` empty; set `detail_log_skipped=failure-detail-log-<suffix>`.
  - Build the ledger row (including optional `detail_log_skipped=<token>` only when a skip occurred) **before** the existing canonical-ledger append attempt.
  - Remove the `validate_failure_detail_log(...) -> hard_fail("failure-detail-log-invalid")` gate entirely.
  - **Leave the existing `try` / `except OSError` canonical-ledger fallback block unchanged in structure and success semantics:**
    - On successful canonical append: emit `ESCALATION_RECORDED=true` and return `0`.
    - On `OSError` (non-writable or append failure): validate fallback and marker paths; if invalid, `hard_fail("fallback-path-invalid")`; otherwise write marker + fallback row, emit `ESCALATION_RECORDED=false` / `ESCALATION_FALLBACK_WRITTEN=true`, and return `0`.
  - Do not read, open, or attach unsafe paths for detail-log evidence.
- Do not rename or backfill historical committed run-log tokens.

### UPDATED: `python/checks.py`

- Ensure every `ledger_failure_detail_log` emitted by lint-fix code is canonical and under the same `allowed_tmpdir` passed to `record-escalation`.
- Prefer a small helper at the point where `log_path` is resolved.
  - Resolve against `Path(allowed_tmpdir).resolve()` when `allowed_tmpdir` is present.
  - Reject or fail with the existing `checks-log-invalid` outcome if the log cannot resolve under that root.
  - Do not emit an outside path in `FixOutcome.ledger_failure_detail_log`.
- Apply the helper to all `main-agent-required` return sites in `_run_lint_fix_impl`.
- Preserve existing `checks repair-loop` and `checks lint-fix` stdout key names.

### UPDATED: `python/test_stall_recovery.py`

- Add `record-escalation` coverage proving optional detail-log misses are non-fatal.
  - Non-absolute path: return code `0`; ledger row written; `failure_detail_log` empty; `detail_log_skipped=failure-detail-log-non-absolute`; no `Tool Failure: record-escalation` entry.
  - Symlink path: same contract with `failure-detail-log-symlink`.
  - Outside-tmpdir path: same contract with `failure-detail-log-outside-tmpdir`.
  - Missing or non-regular path: same contract with the specific token chosen in code (`failure-detail-log-missing` or `failure-detail-log-not-regular-file`).
  - Unreadable path: same contract with `failure-detail-log-unreadable`.
- Add oversize coverage.
  - Create a log larger than `MAX_OPTIONAL_EVIDENCE_BYTES`.
  - Call `record_escalation_main(... --failure-detail-log <oversize>)`.
  - Assert return code `0`.
  - Assert no `Tool Failure: record-escalation` entry.
  - Assert ledger row has a tmpdir-relative sidecar path in `failure_detail_log`, not the original oversize file.
  - Assert sidecar exists, is regular, is not a symlink, and is at most `MAX_OPTIONAL_EVIDENCE_BYTES`.
  - Assert sidecar content matches the truncated prefix.
- Add oversize sidecar materialization failure coverage.
  - Force sidecar write or re-verification to fail (for example by making `tmpdir` read-only after classifier success, or by monkeypatching the helper).
  - Assert return code `0`, ledger row written, `failure_detail_log` empty, `detail_log_skipped=failure-detail-log-truncate-failed`, and no `Tool Failure` entry.
- **Keep `test_record_escalation_nonwritable_ledger_writes_fallback` unchanged** (or adjust only if row-format changes require it): canonical ledger append failure must still return `0`, emit `ESCALATION_RECORDED=false` / `ESCALATION_FALLBACK_WRITTEN=true`, and must not emit `Tool Failure: record-escalation`.
- Keep existing hard-fail coverage for true total-recording failures (for example symlinked canonical ledger path combined with invalid fallback paths) unchanged.
- Keep or adjust existing `classify` and `compose-report` oversize tests so they prove no contract change:
  - `test_classify_rejects_oversize_failure_detail_log`
  - `test_compose_report_tier_a_skips_oversize_detail_log`

### UPDATED: `python/test_checks.py`

- Add or update lint-fix tests so `ledger_failure_detail_log` is always under `allowed_tmpdir`.
- Cover a normal no-tools `main-agent-required` path.
  - Use a checks log inside the session tmpdir.
  - Assert `outcome.ledger_failure_detail_log` is the canonical tmpdir-contained path.
- Cover the containment failure path.
  - Use a checks log outside `allowed_tmpdir`.
  - Assert the outcome remains `failed`.
  - Assert `failure_reason == "checks-log-invalid"`.
  - Assert no outside `ledger_failure_detail_log` is emitted.
- Update existing assertions only if canonicalization changes string form.

### UPDATED: `python/stall-recovery-report.md`

- Update the `record-escalation` subcommand contract.
  - State that `--failure-detail-log` is optional evidence and never blocks ledger recording.
  - State that structural invalid detail-log paths are skipped with specific `detail_log_skipped=failure-detail-log-*` tokens on the ledger row; escalation still succeeds.
  - State that oversize detail logs are truncated to the optional-evidence cap and attached through a tmpdir-local sidecar when materialization succeeds; on truncation failure the escalation still succeeds with `detail_log_skipped=failure-detail-log-truncate-failed`.
  - State that `hard_fail` / `Tool Failure: record-escalation` is reserved for token validation failures, unsafe ledger/fallback/marker paths, and **total** recording failure when canonical append fails and fallback/marker cannot be written. Canonical-ledger append failure alone is **not** a Tool Failure when fallback evidence is written successfully (return code `0`, `ESCALATION_FALLBACK_WRITTEN=true`).
  - Keep the note that append failures can write fallback evidence or the record-failure marker.

## Edge cases

- A symlink can appear after initial validation.
  - Use no-follow reads for sidecar materialization.
  - Re-check the opened file with `fstat`.
- A sidecar path can collide with a prior escalation.
  - Use a stable unique suffix, such as a digest of the source path plus size.
- A log can be exactly `MAX_OPTIONAL_EVIDENCE_BYTES`.
  - Treat it as valid and attach directly; no sidecar.
- A log can be one byte over the cap.
  - Classify as `oversize`; attempt sidecar truncation.
- A path can resolve inside tmpdir but be a directory.
  - Skip with `failure-detail-log-not-regular-file`; still record escalation.
- A missing file inside tmpdir should classify as `missing`, not `outside-tmpdir`.
- If the operator passes a relative path, skip with `failure-detail-log-non-absolute` without opening the path.
- A non-writable canonical ledger must still follow the existing fallback path and return `0` when fallback/marker writes succeed, regardless of detail-log skip or attach outcome.

## Failure modes

- If the oversize sidecar cannot be written or re-verified, record escalation without attachment and set `detail_log_skipped=failure-detail-log-truncate-failed`; do not emit `Tool Failure`.
- If `checks.py` cannot prove the lint-fix log is tmpdir-contained, keep `checks-log-invalid` on the lint-fix outcome; do not emit an outside ledger path.
- If helper stderr text changes, existing `classify` tests may fail. Preserve those messages unless the test is intentionally updated.
- If canonical ledger append raises `OSError` but fallback and marker writes succeed, preserve return code `0` and do not emit `Tool Failure`. Only emit `Tool Failure` when fallback/marker paths are invalid or their writes also fail after canonical append failure.
- If the canonical ledger path itself is invalid before any write attempt, preserve existing `ledger-path-invalid` hard-fail behavior.

## Testing strategy

- Run targeted unit tests:
  - `python3 -m pytest python/test_stall_recovery.py -k "failure_detail_log or record_escalation or compose_report_tier_a_skips_oversize or nonwritable_ledger"`
  - `python3 -m pytest python/test_checks.py -k "lint_fix and ledger"`
- Run targeted lint for changed Python files:
  - `python3 python/cli.py lint py-files python/larch/state/stall_recovery.py python/checks.py python/test_stall_recovery.py python/test_checks.py`
- If the doc change triggers markdown lint, run the repo's documented markdown lint target for `python/stall-recovery-report.md`.

## Acceptance

- `record-escalation` no longer emits the generic `failure-detail-log-invalid` token. An invalid non-oversize `--failure-detail-log` (non-absolute, symlink, outside-tmpdir, missing, not-regular-file, unreadable) records the escalation with `failure_detail_log` empty and a specific `detail_log_skipped=failure-detail-log-<cause>` field on the ledger row, returns `0`, and writes no `Tool Failure: record-escalation` entry.
- An oversize `--failure-detail-log` is truncated to `MAX_OPTIONAL_EVIDENCE_BYTES` into a tmpdir-local sidecar; the ledger row's `failure_detail_log` references the sidecar after re-verification (inside tmpdir, regular file, not a symlink, within the cap). On sidecar materialization or re-verification failure the escalation still returns `0` with `detail_log_skipped=failure-detail-log-truncate-failed`.
- `classify` and `compose-report` behavior is unchanged: `test_classify_rejects_oversize_failure_detail_log` and `test_compose_report_tier_a_skips_oversize_detail_log` still pass, and existing stderr assertions remain byte-compatible.
- `hard_fail` fires only for token-validation failures, unsafe or unwritable ledger/fallback/marker paths, and total recording failure; the canonical-ledger `OSError` fallback path still returns `0` with `ESCALATION_RECORDED=false` / `ESCALATION_FALLBACK_WRITTEN=true`.
- `python/checks.py` lint-fix never emits an outside-tmpdir `ledger_failure_detail_log`; a non-contained checks log keeps the existing `checks-log-invalid` outcome.
- New coverage in `python/test_stall_recovery.py` and `python/test_checks.py` exercises the specific-reason, oversize-truncate, sidecar-failure, and containment paths; targeted lint passes for the changed Python files.

review_status: complete
rounds_completed: 3
diff_lines: 325

