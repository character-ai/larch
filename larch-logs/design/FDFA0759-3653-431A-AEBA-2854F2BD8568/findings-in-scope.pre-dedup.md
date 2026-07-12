### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:22-32,34-40
- **Concern**: The detailed resolver contract does not define how an invalid `origin` candidate is preserved for `clarify`. Scenario: `remote_repo()` currently returns only a valid parsed slug or `None`, so a malformed but non-empty origin URL is discarded as “no candidate.” `clarify` would emit `could not determine repo` instead of the required `invalid-repo`, despite the plan requiring both primary and origin invalid candidates to map to `invalid-repo`.
- **Proposed resolution**: Specify and implement a detailed origin-resolution result that preserves a non-empty invalid candidate, or explicitly narrow the contract and add the corresponding no-repro rationale. Add a focused test for malformed non-empty origin discovery and its `invalid-repo` mapping.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/report_tokens_scan.py:63-78
- **Concern**: [ALREADY_ADDRESSED] Ambient failure diagnostics are not carried by `gh.resolve_repo`. Scenario: The plan requires preserving the current unresolved diagnostic, and failure modes warn about OSError normalization, but the `report_tokens_scan.py` update only swaps `repo_name_with_owner_read` for `gh.resolve_repo(runner)`. That adapter returns `None` with no stderr/stdout or `OSError` detail, so operators lose the redacted `: <detail>` suffix and the dedicated `OSError` message path even when the generic prefix remains.
- **Proposed resolution**: In `gh.py`, extend the detailed resolution result with optional failure detail (or add a report-tokens-only wrapper) and spell out in `report_tokens_scan.py` that unresolved ambient paths must print the same diagnostic shape as today before returning `None`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1901-1906
- **Concern**: Detailed resolver must not retry `origin` after a non-empty invalid primary `gh` candidate. Scenario: The plan adds a detailed canonical state for clarify but does not lock evaluation order. `resolve_repo` today skips `origin` when primary `gh` returns a non-empty invalid slug; clarify maps that case to `ERROR=invalid-repo`. If the detailed path retries `origin` after primary validation fails, malformed primary output could resolve via `origin` or collapse to `could not determine repo`, regressing the round-1 clarify contract.
- **Proposed resolution**: In `python/larch/git/gh.py`, document and implement: after primary `gh`, if stdout is non-empty and fails `validate_repo_slug`, record `invalid` and stop; attempt `origin` only when primary produced no usable candidate (failed or empty). Add a `test_gh.py` case for non-empty invalid primary with a valid `origin` remote. ### 1. [risk-integration] `python/larch/report/report_tokens_scan.py:63-78` — Ambient failure diagnostics are not carried by `gh.resolve_repo` The plan states that unresolved report-token scanning must keep today's operator diagnostic and calls out OSError normalization as a failure mode, but the proposed `report_tokens_scan.py` change only replaces `repo_name_with_owner_read` with `gh.resolve_repo(runner)`. The adapter returns `None` without stderr, stdout, or exception text. Today's path prints a redacted `: <detail>` suffix and a separate `OSError` message; that richer contract is not achievable through the bare adapter alone. **Suggested revision:** Extend the detailed resolution result (or add a narrow report-tokens wrapper) with optional failure detail, and state explicitly in the `report_tokens_scan.py` plan step that unresolved ambient paths must emit the same diagnostic shape as today before returning `None`. ### 2. [correctness] `python/larch/git/gh.py:1901-1906` — Detailed resolver must not retry `origin` after a non-empty invalid primary `gh` candidate The plan introduces detailed states for clarify but does not pin evaluation order. Current `resolve_repo` only falls back to `origin` when the primary candidate is empty. Clarify must map a non-empty invalid primary slug to `ERROR=invalid-repo`, not `could not determine repo` and not silent success via `origin`. Without an explicit rule, an implementer could retry `origin` after primary validation fails and change clarify's public error mapping. **Suggested revision:** In `gh.py`, specify and test: non-empty invalid primary output records `invalid` and does not attempt `origin`; `origin` runs only when primary produced no candidate. Add `test_gh.py` coverage where primary returns a non-empty invalid slug but `origin` would succeed.



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_scan.py:63-78
- **Concern**: The plan cannot preserve the required unresolved diagnostic through `gh.resolve_repo`, which returns only `str | None` and discards the primary failure detail. Scenario: When `gh repo view` fails with useful stderr and the origin fallback also fails, `_repo_slug` receives only `None` and cannot emit the current redacted diagnostic suffix mandated by the plan
- **Proposed resolution**: Include redacted primary failure detail in the planned detailed-resolution result and let `_repo_slug` consume that result, or retain a canonical helper that returns the command result without rebuilding discovery logic locally



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_scan.py:63-78
- **Concern**: The plan cannot preserve the required repository-resolution diagnostic through the `gh.resolve_repo` adapter. Scenario: When primary discovery returns stderr or raises `OSError` and the origin fallback also fails, `gh.resolve_repo` returns only `None`. `_repo_slug` therefore loses the redacted failure detail that it currently appends to its diagnostic, despite the plan explicitly requiring that behavior
- **Proposed resolution**: Allow the canonical detailed result to carry failure detail and let `_repo_slug` consume it, then test both nonzero primary stderr and `OSError` diagnostics; keep ordinary callers on `gh.resolve_repo`



