### FINDING_1: Clarify loses invalid-ambient-repository error mapping
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-dyn-Repo Resolution Contract Auditor
- **Severity**: major
- **Concern**: Replacing clarify’s local resolution with a bare `gh.resolve_repo` call collapses two distinct cases—an unavailable repository and a non-empty but invalid resolved slug—into `None`. As a result, malformed ambient discovery would produce `_ClarifyRepoResolutionError` (`ERROR=could not determine repo`, exit 2) instead of the required `_ClarifyValidationError` (`ERROR=invalid-repo`, exit 1), contrary to the stated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After repointing, an ambient gh stdout like bad..repo would change operator-visible ERROR and exit code even though explicit --repo bad..repo still returns invalid-repo. Spell out clarify resolution steps: validate explicit slug; read gh stdout and raise _ClarifyValidationError before fallback when gh returned a non-empty invalid slug; then apply origin fallback (remote_repo or resolve_repo); raise _ClarifyRepoResolutionError only when still empty. Add a test that ambient invalid gh output keeps ERROR=invalid-repo.
  - From Cursor-Innovation: Assemble candidate the same way as gh.resolve_repo (repo_name_with_owner_read then remote_repo), then raise _ClarifyRepoResolutionError when candidate is empty and _ClarifyValidationError when non-empty candidate fails validate_repo_slug; only use the resolved slug when validation passes. Update test_clarify.py accordingly instead of asserting raw gh argv.
  - From Codex-Pragmatic: Amend the plan to define the intended mapping and tests, or preserve the distinction through an explicit canonical resolver result; do not promise preservation that the proposed API cannot provide
  - From Cursor-dyn-Repo Resolution Contract Auditor: Spell clarify implementation: after None from gh.resolve_repo probe whether a non-empty gh candidate failed validate_repo_slug and raise _ClarifyValidationError before _ClarifyRepoResolutionError or narrow the plan contract to allow collapsing invalid ambient slugs into repo-resolution failure


### FINDING_2: Four live repository-resolution sites are omitted from the migration
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Repo Resolution Contract Auditor, Codex-dyn-Repo Resolution Contract Auditor
- **Severity**: major
- **Concern**: The firm file list omits `python/larch/issue/issue_wire.py`, `python/larch/state/session_env.py`, `python/larch/report/report_tokens_scan.py`, and `python/larch/rendering/rendering.py`. These callers will continue using `resolve_repo_gh_only`, `repo_name_with_owner_read`, or duplicated Git fallback logic, leaving repository resolution inconsistent, preventing completion of the stated unification, and potentially failing adoption-lint. Their existing explicit-override, empty-result, error, and missing-`gh` contracts also need to be preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these production files and their focused tests to the firm plan, or document a concrete scope exclusion for each site with preserved semantics
  - From Cursor-Innovation: Add ### UPDATED entries for issue_wire.py (_resolve_issue_wire_repo → gh.resolve_repo), session_env.py (_repo_from_gh_or_git → gh.resolve_repo(proc) or "" with existing FileNotFoundError handling), report_tokens_scan.py (_repo_slug ambient path), and rendering.py (diagrams upsert ambient repo), each preserving current error/empty contracts, explicit --repo precedence, plus focused test updates in python/tests/issue/test_issue_wire.py, python/tests/state/test_session_env.py, and any rendering/report_tokens tests that assert argv shapes.
  - From Codex-Innovation: Add these files to the firm change set, route their ambient resolution through gh.resolve_repo while preserving each caller's error and return contract, and add focused tests for the affected seams
  - From Cursor-Pragmatic: Add ### UPDATED entries for those four modules (delegate to gh.resolve_repo, preserve each caller's error/empty contract and explicit --repo precedence) plus focused tests: python/tests/issue/test_issue_wire.py, python/tests/state/test_session_env.py, python/tests/report/test_report_tokens_scan.py, and python/tests/rendering/test_rendering.py.
  - From Codex-Pragmatic: Include these modules in the plan and repoint their ambient repository discovery to gh.resolve_repo, preserving each caller's explicit override and failure contract; add focused tests where their fallback or error behavior changes
  - From Codex-Requirements: Add these four runtime surfaces to the firm file set, replace their discovery calls with gh.resolve_repo while preserving each caller's error/output contract, and add focused tests for canonical success and remote-fallback behavior where applicable
  - From Cursor-dyn-Repo Resolution Contract Auditor: Add ### UPDATED: python/larch/issue/issue_wire.py (switch _resolve_issue_wire_repo to gh.resolve_repo) and ### UPDATED: python/tests/issue/test_issue_wire.py; extend plan step 5 search beyond the named module list or explicitly enumerate issue_wire
  - From Codex-dyn-Repo Resolution Contract Auditor: Include `python/larch/issue/issue_wire.py` in the firm update set, switch this helper to `gh.resolve_repo`, and preserve its `could not determine repo` exception and `FAILED=true`/`ERROR=` behavior
  - From Codex-dyn-Repo Resolution Contract Auditor: Include this file in the migration, use `gh.resolve_repo(runner)`, map `None` to the existing empty-string result, and preserve the current missing-`gh` handling
  - From Codex-dyn-Repo Resolution Contract Auditor: Include this file in the firm update set, call `gh.resolve_repo(runner)`, preserve explicit `args.repo` precedence, and retain the existing `ShipError` and slug-validation behavior
  - From Codex-dyn-Repo Resolution Contract Auditor: Include this file and its tests, delegate discovery to `gh.resolve_repo(runner)`, map `None` to the existing `None` result, and preserve explicit override validation plus current error output


### FINDING_3: Verification and focused tests do not enforce repo-wide resolver adoption
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The proposed audit and testing strategy limits checks for `resolve_repo_gh_only` and `repo_name_with_owner_read` to named in-scope modules. Because the omitted live sites are outside that list, verification can pass while duplicate resolution paths remain. The testing plan also does not cover the retained or repointed surfaces’ fallback, unresolved, explicit-override, and caller-specific error contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add tests for each retained or repointed site, including explicit override precedence where applicable, unresolved behavior, and the canonical remote-fallback contract
  - From Cursor-Innovation: Change step 5 to search all python/larch (excluding python/larch/git/gh.py internals and documented multi-field queries) for repo_name_with_owner_read and resolve_repo_gh_only call sites outside gh.py, and require zero hits before merge.
  - From Cursor-Pragmatic: Extend step 5 (and the Approach item 5 search) to all of python/larch/, or require zero matches repo-wide before merge; keep test_gh.py as the sole owner of resolver parsing internals.


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


