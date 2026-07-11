## Plan

### Approach

Fix the classifier-only regression that turns an already-merged post-merge cleanup stall into a reship attempt.

1. Do not add the proposed `ship_pr.py` healthy-completion branch. The accepted review findings establish that the branch keyed only to `REFRESH_SKIP_PRETERMINAL_OUTCOME` is not reliably reachable from the real `flush_logs_post()` skip contract, so it would not fix the reported production route and could obscure the distinction between benign and real post-merge failures.
2. Add a narrowly scoped classifier guard for the specific expected cleanup route:
   - an active stall exists;
   - the normal no-stall short-circuit did not already decide the result;
   - `phase == "postmerge"`;
   - `stall_step == "postmerge-flush"`;
   - durable merged state contains a canonical terminal merge result;
   - evidence contains `config.REFRESH_SKIP_PRETERMINAL_OUTCOME`;
   - evidence contains none of the known unexpected post-merge flush failure markers: `redaction-failed`, `post-merge-refresh-failed`, `manifest-recovery-failed`, or `commit-failed`.
3. Return `operator-action` / `none` / `postmerge-flush-expected` only for that exact combination, before `_classify_text()` can invoke `_ship_refresh_preterminal_stall()`. Unexpected failure evidence takes precedence over this expected-cleanup guard, including when stale `preterminal-outcome` text is also present.
4. Preserve the guard’s explicit `RESUME_HINT=none` through the later resume-hint resolution. The current generic `_resume_hint_for()` path can map an `operator-action` result in `postmerge` back to `step8-shippr`; restructure the classifier result flow so this exact guard bypasses that recomputation rather than merely returning an intermediate `none` value.
5. Preserve normal text classification for post-merge `commit-failed`, `redaction-failed`, `post-merge-refresh-failed`, manifest/recovery failures, missing merge evidence, different stall steps, and all pre-push guideline-refresh stalls.
6. Ensure repeated classification cannot convert the expected post-merge classification into `same-cause-repeat`.
7. Add the new pattern to the output-token allowlist and cover the positive, mixed-evidence negative, other negative, resume-hint, and repeated-attempt routes with state-classifier tests.

## Files to modify/create

### UPDATED: python/larch/state/_classify.py

- Import or reuse the canonical terminal merge-result authority rather than duplicating `merged`, `admin_merged`, and `already_merged`.
- Add a dedicated helper or local predicate for the expected post-merge cleanup route. It must require all of:
  - `any_stall` is true;
  - `phase == "postmerge"`;
  - `stall_step == "postmerge-flush"`;
  - merged state contains a canonical terminal `MERGE_RESULT`;
  - evidence contains `config.REFRESH_SKIP_PRETERMINAL_OUTCOME`;
  - evidence does **not** contain any known unexpected flush-failure marker: `redaction-failed`, `post-merge-refresh-failed`, `manifest-recovery-failed`, or `commit-failed`.
- Keep the unexpected-failure exclusion list local to this expected-cleanup predicate, using the same evidence normalization used by the classifier. The guard must fail closed: unrecognized or real failure evidence continues to normal text classification rather than being treated as expected cleanup.
- Apply this predicate only after the existing no-stall short-circuit has had a chance to return and before `_classify_text()` processes evidence. Structure the ordering so the effective decision is equivalent to:
  - existing `short_circuit`;
  - then the narrow expected-postmerge guard;
  - then normal `_classify_text()` classification.
- Return exactly for the matched guard:
  - `FAILURE_CLASS=operator-action`
  - `RESUME_HINT=none`
  - `MATCHED_CLASSIFIER_PATTERN=postmerge-flush-expected`
- Carry an explicit indication that the expected-postmerge guard supplied a final resume hint, or otherwise structure the result flow so `_resume_hint_for()` is not called for that route. Do not allow the generic `operator-action`/`postmerge` fallback to replace `none` with `step8-shippr`.
- Keep `_ship_refresh_preterminal_stall()` unchanged. Its pre-push `pr-create-guideline-outcome-refresh` behavior must remain available for genuine recoverable stalls.
- Preserve the expected `operator-action` classification through same-cause attempt handling: do not rewrite this guard’s result to `same-cause-repeat` when the same post-merge signature is classified again.
- Keep the guard intentionally evidence-sensitive. A terminal merge result alone, or terminal merge state plus stale `preterminal-outcome` alongside a flush failure, must not suppress classification of a real post-merge flush failure.

### UPDATED: python/larch/state/_tokens.py

- Add `postmerge-flush-expected` to the matched-classifier-pattern allowlist.
- Preserve the explicit pattern in classifier stdout and persisted classification output rather than allowing it to normalize to `redacted`.

### UPDATED: python/tests/state/test_stall_recovery.py

- Add a regression fixture representing the reported false-positive route:
  - `PHASE=postmerge`;
  - active stall tracking;
  - `STALL_STEP=postmerge-flush`;
  - terminal `MERGE_RESULT`, including `admin_merged`;
  - evidence containing `REASON=preterminal-outcome`.
- Assert the result is exactly `operator-action` / `none` / `postmerge-flush-expected`.
- Assert the result is not `transient-infra`, does not emit `step8-shippr`, and retains `RESUME_HINT=none` after the classifier’s normal resume-hint resolution.
- Parameterize or otherwise cover every canonical terminal merge result: `merged`, `admin_merged`, and `already_merged`.
- Add a repeated-classification regression using the same expected post-merge signature and prior-attempt state. Assert it remains `operator-action` / `none` / `postmerge-flush-expected`, rather than being rewritten to `same-cause-repeat`.
- Add negative cases proving the guard does not hide real failures:
  - `PHASE=postmerge`, `STALL_STEP=postmerge-flush`, terminal merge result, and evidence for each unexpected flush failure marker—`commit-failed`, `redaction-failed`, `post-merge-refresh-failed`, and `manifest-recovery-failed`—must continue through normal classification;
  - add a mixed-evidence regression containing both `preterminal-outcome` and `redaction-failed`; assert the expected-cleanup guard does not match and normal failure classification remains in control;
  - `PHASE=postmerge` with `preterminal-outcome` evidence but no terminal merge result must continue through normal classification;
  - a terminal merge result with a different stall step must not trigger the guard.
- Retain the existing pre-push tests that require `transient-infra` / `step8-shippr` for `pr-create-guideline-outcome-refresh`.

## Edge cases

- `preterminal-outcome` is only benign for the exact confirmed-merge, `postmerge-flush` route and only when evidence has no known unexpected flush-failure marker; stale text alone is insufficient.
- `commit-failed`, `redaction-failed`, `post-merge-refresh-failed`, manifest/recovery failures, and future unexpected post-merge flush reasons remain visible to normal stall classification.
- A `postmerge` phase and terminal merge result are insufficient without both the `postmerge-flush` stall step and expected evidence.
- `already_merged` receives the same protection as `merged` and `admin_merged`.
- The no-stall classifier path retains its existing result and is never recategorized as expected post-merge cleanup.
- The expected route’s explicit `none` hint must survive the generic resume-hint logic; it must never fall through to `step8-shippr`.
- Repeated classification of the expected route must not re-enable terminal failure reporting through `same-cause-repeat`.

## Failure modes

- A broad phase-and-merge-only guard would hide genuine post-merge log-flush failures; require the exact stall step, `preterminal-outcome` evidence, and absence of known flush-failure evidence.
- Treating any mixed evidence containing `preterminal-outcome` as benign would suppress real errors; known unexpected failure markers must take precedence over the expected-cleanup guard.
- Returning `none` from the guard without changing later resume-hint handling would still permit `_resume_hint_for()` to produce `step8-shippr`; make the guard’s hint final for this exact route.
- Placing the guard before the existing no-stall short-circuit would misclassify calls without active stall tracking; apply it only when an active stall remains undecided.
- Leaving same-cause conversion enabled for the expected classification could restore terminal reporting after a retry; preserve `operator-action` for this guard.
- Omitting the token allowlist update would reduce the diagnostic pattern to `redacted`, weakening both observability and regression coverage.
- Adding a ship-driver `Outcome.OK` branch for a skip reason not consistently emitted by the live post-merge flush contract would create misleading coverage without fixing the classifier route; keep this change scoped to classification.

## Testing strategy

Run only the changed Python test file:

- `python3 -m pytest python/tests/state/test_stall_recovery.py`

Then run the repository’s documented changed-file Python lint and type checks for:

- `python/larch/state/_classify.py`
- `python/larch/state/_tokens.py`
- `python/tests/state/test_stall_recovery.py`

Verify these acceptance outcomes:

- A confirmed terminal merge plus `postmerge-flush` and only expected `preterminal-outcome` evidence emits `operator-action`, `none`, and `postmerge-flush-expected`.
- The classifier does not emit `step8-shippr` for that route, including after generic resume-hint processing, so no spurious reship is attempted.
- Mixed `preterminal-outcome` plus `redaction-failed` evidence does not match the expected-cleanup guard and remains on a normal failure-classification path.
- Each listed unexpected post-merge flush marker remains on a normal classification path even when terminal merge state is present.
- Repeated classification of the expected route remains non-resumable and does not become `same-cause-repeat`.
- Pre-push guideline-refresh recovery remains `transient-infra` / `step8-shippr`.
- The new pattern remains visible in stdout and persisted classifier output.

## Acceptance

Run only the changed Python test file:

- `python3 -m pytest python/tests/state/test_stall_recovery.py`

Then run the repository’s documented changed-file Python lint and type checks for:

- `python/larch/state/_classify.py`
- `python/larch/state/_tokens.py`
- `python/tests/state/test_stall_recovery.py`

Verify these acceptance outcomes:

- A confirmed terminal merge plus `postmerge-flush` and only expected `preterminal-outcome` evidence emits `operator-action`, `none`, and `postmerge-flush-expected`.
- The classifier does not emit `step8-shippr` for that route, including after generic resume-hint processing, so no spurious reship is attempted.
- Mixed `preterminal-outcome` plus `redaction-failed` evidence does not match the expected-cleanup guard and remains on a normal failure-classification path.
- Each listed unexpected post-merge flush marker remains on a normal classification path even when terminal merge state is present.
- Repeated classification of the expected route remains non-resumable and does not become `same-cause-repeat`.
- Pre-push guideline-refresh recovery remains `transient-infra` / `step8-shippr`.
- The new pattern remains visible in stdout and persisted classifier output.

review_status: complete
rounds_completed: 2
difficulty: HARD
mechanical_churn: false
diff_lines: 125
