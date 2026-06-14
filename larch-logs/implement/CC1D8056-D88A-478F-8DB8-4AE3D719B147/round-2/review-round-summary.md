# Review Round 2

- Mode: `diff`
- 10 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Budget expiry and timeout cleanup misclassify finished workers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When the global citation-fetch budget expires, the poll loop exits without a final reap of active subprocesses. Cleanup then assigns `UNKNOWN(timeout)` to every remaining worker without checking whether a process already exited with a valid result file. A fetch that completes just after the last poll can be terminated and recorded as timeout; bash only backfilled keys with no result file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Poll active processes once more before breaking on deadline; in cleanup decode completed procs before assigning timeout; only backfill keys missing from results.
  - From cursor-specialist-correctness-output.txt: Check proc.poll() and decode successful results before timeout backfill.


### FINDING_10: Missing render-findings-batch non-regular report path test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `render-findings-batch` exit 2 is only tested for missing files, not directories or other non-regular paths required by plan. A future `is_file()` loosening could accept directories and corrupt `/issue` batch parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Test directory report path returns exit 2 with ERROR: report file not found wording.


### FINDING_11: Missing git-root-unavailable and out-of-tree symlink citation tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Plan-required `git-root-unavailable` and out-of-tree symlink file-line token cases are untested. SSRF/path-containment regressions in `check_fileline()` would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monkeypatch git rev-parse failure and add escaping-symlink fixture; assert reason tokens.
  - From dyn-test-replacement-output.txt: Add focused unit tests using existing seams (`git_root=None` / missing root, injected resolver with sleep, `max_claims=6` with a 10-claim fixture, duplicate URL in report, two identical runs diffing sidecars, connector returning 410, env `HTTP_PROXY` with connector spy).


### FINDING_12: render-findings-batch pytest coverage far below retired harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Findings rendering tests cover numbered lists only. The retired `test-render-findings-batch.sh` contract covered bulleted vs paragraph heuristics, planner `#### Subquestion` flushing, fence-aware extraction, tab-prefixed `###` escaping, nested numbered sublists, empty-title fallback, and more. `rendering.split_finding_items` has little direct fixture coverage, so heuristic regressions can break `/research` Step 3 issue batches without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port bash harness fixtures per rendering mode with issue parse-input round-trip.
  - From dyn-test-replacement-output.txt: Port the retired harness fixtures into parametrized tests in `python/test_research.py` (or a dedicated `TestRenderFindingsBatch` class), asserting exit codes, `COUNT=`, sidecar shape, and `issue parse-input` `ITEMS_TOTAL` / no `MALFORMED` for each case from the old `test-render-findings-batch.md` ledger.


### FINDING_13: validate-research-output provenance and validation-mode tests are thin
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: URL-only and extensionless provenance marker tests are plan-required but absent. The retired `test-validate-research-output.sh` had dozens of boundary cases (#473 false positives, extensionless `Makefile`, invalid colon/slash refs, validation-mode uncited-at-30-words, false JSON sentinels). Current pytest keeps only a handful of happy-path checks; drift in `voting.FILE_LINE_REGEXES` or validation-mode short-circuit logic would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pass/fail fixtures for https URL, Makefile:line, and extensionless path alone.
  - From dyn-test-replacement-output.txt: Add parametrized provenance and validation-mode cases mirroring the old harness matrix (at minimum: extensionless marker, empty fence non-provenance, 2–3 #473 false-positive rejections, invalid colon/slash refs, `FINDING_1: EXONERATE`, and validation-mode uncited failure at the 30-word default).


### FINDING_2: Header-only structured TSV passes validation modes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: `_validate_structured_tsv()` treats a lone schema header as success (`len(out) == 1`). In `--validation-mode` and structured-reviewer mode, a header-only payload short-circuits to exit `0`, bypassing word-count and provenance checks. That can let collectors accept effectively empty reviewer output as substantive, unlike the bash contract that required at least one data row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require at least one validated TSV data row before returning normalized output; return empty/falsy when only the header matched.
  - From dyn-research-parity-output.txt: Require at least one validated data row before treating TSV as a validation-mode pass (for example, return success only when `len(out) > 1`, or add an explicit row-count check).


### FINDING_4: Failed or empty DNS resolution falls through to unpinned HTTPS connect
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: After `_resolve_public_ips()` returns an empty IP list (with or without `network-error`) or fails without a handled reason, `fetch_url()` can still open an unpinned `HTTPSConnection` to the hostname. That triggers a second OS DNS lookup, skips the resolved-IP private-range gate, and weakens the SSRF fail-closed contract from the bash port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat empty resolved IP sets as UNKNOWN(network-error) or UNKNOWN(timeout) rather than connecting without a pinned public IP.
  - From dyn-research-parity-output.txt: Fail closed before connect when `resolve_reason` is `network-error` or when `ips` is empty (return `UNKNOWN(network-error)` or `UNKNOWN(timeout)` as appropriate). Only proceed to `_PinnedHTTPSConnection` when a checked public IP exists.


### FINDING_7: Degraded citation path emits SUMMARY before quiet_init
- **Reviewer(s)**: dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: On invalid numeric flags (`--budget-seconds`, `--per-fetch-timeout`, `--max-claims`), `validate_citations_main()` writes the degraded sidecar and calls `_emit_summary()` before `logging_util.quiet_init()`. With quiet routing enabled, contract `SUMMARY=...` can land on stdout instead of fd 3, breaking the degraded-path stream contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Call `quiet_init()` before writing the degraded sidecar and emitting `SUMMARY`, or route that summary through the same fd-3 contract path used on the success path.


### FINDING_8: DNS ThreadPoolExecutor can block past per-fetch timeout
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_resolve_public_ips` uses `future.result(timeout=timeout)`, but the `ThreadPoolExecutor` context manager waits for the DNS worker during `__exit__` after a timeout. A hanging resolver can make `--per-fetch-timeout 1` block until DNS returns or the outer budget kills the worker, breaking the bounded-DNS fail-soft contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Avoid the executor context manager here. On timeout, call `shutdown(wait=False, cancel_futures=True)` before returning, or run DNS only inside a subprocess that the parent can terminate on the per-fetch deadline.


### FINDING_9: Missing --max-claims truncation regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Plan-required `--max-claims` truncation coverage is absent despite implementation in `research.py`. A regression in claim ordering or truncation could drop citations silently while `SUMMARY` still passes and citation tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a mixed-claim fixture with max_claims cap; assert ledger rows and truncation advisory.
  - From dyn-test-replacement-output.txt: Add focused unit tests using existing seams (`git_root=None` / missing root, injected resolver with sleep, `max_claims=6` with a 10-claim fixture, duplicate URL in report, two identical runs diffing sidecars, connector returning 410, env `HTTP_PROXY` with connector spy).


