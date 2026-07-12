### FINDING_1: Invalid `origin` candidates are discarded
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The detailed resolver contract does not define how a malformed but non-empty `origin` candidate is preserved for `clarify`. If `remote_repo()` returns only a valid parsed slug or `None`, `clarify` may emit `could not determine repo` instead of the required `invalid-repo`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify and implement a detailed origin-resolution result that preserves a non-empty invalid candidate, or explicitly narrow the contract and add the corresponding no-repro rationale. Add a focused test for malformed non-empty origin discovery and its `invalid-repo` mapping.


### FINDING_2: Repository-resolution failure diagnostics are lost
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Replacing the existing report-token repository discovery with `gh.resolve_repo(runner)` loses primary failure details because the adapter returns only `str | None`. When primary discovery returns stderr or raises `OSError` and the `origin` fallback also fails, `_repo_slug` cannot preserve the current redacted diagnostic suffix or dedicated `OSError` message path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `gh.py`, extend the detailed resolution result with optional failure detail (or add a report-tokens-only wrapper) and spell out in `report_tokens_scan.py` that unresolved ambient paths must print the same diagnostic shape as today before returning `None`.
  - From Codex-Pragmatic: Include redacted primary failure detail in the planned detailed-resolution result and let `_repo_slug` consume that result, or retain a canonical helper that returns the command result without rebuilding discovery logic locally
  - From Codex-Requirements: Allow the canonical detailed result to carry failure detail and let `_repo_slug` consume it, then test both nonzero primary stderr and `OSError` diagnostics; keep ordinary callers on `gh.resolve_repo`


