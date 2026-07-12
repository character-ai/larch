## Goal
Implement issue #7054: [IMPLEMENTING] contract-unification [FEATURE] unify repo-resolution copies onto gh.resolve_repo.

## Implementation Plan
## Plan

## Approach

1. Enumerate every runtime repository-discovery site in `python/larch/` before editing, including direct `gh repo view --json nameWithOwner` calls, `repo_name_with_owner_read`, `resolve_repo_gh_only`, and duplicated `origin`-remote fallback logic.
2. Centralize repository discovery in `python/larch/git/gh.py` with one detailed canonical result that preserves all observable states needed by callers:
   - Preserve `gh.resolve_repo(runner, cwd=...) -> str | None` as the normal caller API.
   - Record the source and state of discovery: valid slug, no candidate, or non-empty invalid candidate from either primary `gh` discovery or `origin` fallback.
   - Preserve the raw-or-normalized non-empty `origin` candidate long enough to classify it as invalid; do not route detailed fallback through a lossy helper that returns only valid slugs or `None`.
   - Record primary `gh repo view` failure information separately from candidate state, including nonzero failure output and `OSError`/missing-tool failure data, in a form that existing callers can safely redact and format.
   - Make canonical discovery attempt `origin` fallback whenever primary `gh` discovery is unavailable or unsuccessful, including `FileNotFoundError` and other `OSError` cases where the existing caller contract requires graceful handling.
   - Retire `resolve_repo_gh_only` after repo-wide callers are migrated and its remaining references are removed.
3. Repoint normal ambient-resolution callers to `gh.resolve_repo`, preserving explicit `--repo` or environment override precedence, caller-specific `""`/`None`/exception behavior, validation, output grammar, and `cwd`.
4. Use the detailed canonical result only where its extra information is contractually required:
   - `clarify` consumes candidate state so explicit invalid repositories and non-empty invalid ambient candidates from either `gh` or `origin` remain `_ClarifyValidationError("invalid-repo")`.
   - `report_tokens_scan` consumes the recorded primary-failure detail so unresolved ambient discovery preserves its current redacted diagnostic shape, including its dedicated `OSError` path.
   - Normal callers remain on the `resolve_repo` `str | None` adapter and continue to map unresolved or invalid ambient discovery through their existing contracts.
5. Delete redundant local JSON parsing, raw `gh repo view` argv construction, and duplicated remote fallback code. Keep named wrappers only where they are active test seams or map the canonical result to domain-specific errors or diagnostics.
6. Leave multi-field GitHub queries, non-repository `gh` commands, and filesystem path resolvers unchanged.
7. Treat already-compliant `design_step0.resolve_repo` as an audited no-op surface.

## Files to modify/create

### UPDATED: python/larch/git/gh.py

- Introduce a canonical detailed repository-resolution representation with:
  - a candidate status of valid slug, absent candidate, or non-empty invalid candidate;
  - the candidate source (`gh` primary discovery or `origin` fallback); and
  - optional primary-discovery failure detail sufficient for callers to preserve existing redacted nonzero-stderr and `OSError` diagnostics.
- Implement the detailed path once using the existing primary `gh repo view` read and `origin` remote fallback semantics; do not expose raw command construction to migrated callers.
- Make the detailed `origin` path retain a non-empty malformed remote-derived candidate instead of collapsing it to `None`. Reuse or extend the canonical Git remote parsing path so valid and invalid remote candidates are classified in one place rather than recreating parsing in `clarify`.
- Define fallback precedence precisely:
  - return a valid primary slug immediately;
  - when primary discovery is unavailable, unsuccessful, empty, or invalid, attempt canonical `origin` discovery;
  - prefer a valid `origin` slug over an invalid primary candidate;
  - if no valid slug exists, retain a non-empty invalid candidate from either source for detailed consumers, while `resolve_repo` returns `None`;
  - retain primary failure detail even when fallback is attempted, so report-token diagnostics remain available if final resolution is unresolved.
- Make `resolve_repo` delegate to that detailed path and retain its existing validating `str | None` public contract.
- Ensure primary discovery failures caused by `FileNotFoundError` or `OSError` can fall through to canonical `origin` lookup; map unavailable Git discovery to no repository result for ordinary callers rather than leaking an ambient tool failure.
- Keep enough structured failure information for `report_tokens_scan` to reproduce its current diagnostic branch and redaction behavior without issuing a second raw repository-discovery command.
- Remove `resolve_repo_gh_only` after the repo-wide migration confirms no runtime or test consumers remain.
- Keep `validate_repo_slug`, `repo_name_with_owner_read`, and unrelated multi-field query helpers intact unless a narrowly required internal refactor is needed to support the detailed canonical result.

### UPDATED: python/larch/design/clarify.py

- Change `_resolve_repo_for_clarify` to use the canonical detailed resolver rather than locally constructing a `gh repo view` request.
- Keep explicit repository validation before ambient resolution.
- Preserve `_ClarifyValidationError("invalid-repo")` for:
  - explicit invalid values;
  - non-empty invalid primary `gh` candidates; and
  - non-empty invalid `origin` candidates, including malformed remote URL or slug forms that canonical fallback can extract but cannot validate.
- Preserve `_ClarifyRepoResolutionError` only when neither canonical primary discovery nor canonical `origin` fallback yields a valid or invalid candidate.
- Pass `cwd` through unchanged.

### UPDATED: python/larch/design/design_pause.py

- Change `_resolve_repo` from `gh.resolve_repo_gh_only` to `gh.resolve_repo`.
- Keep precedence order: CLI argument, persisted `REPO`, then ambient repository resolution.
- Preserve the empty-string result when canonical resolution returns `None`.

### UPDATED: python/larch/design/design_terminal.py

- Replace the nested raw `gh repo view` subprocess call in `file_issue_after_dedup` with `gh.resolve_repo(proc)`.
- Preserve the `tier-a-current-repo-unresolved` fallback reason and all later filing behavior.
- Leave unrelated subprocess calls intact.

### UPDATED: python/larch/state/admission.py

- Import `proc` and `gh`.
- Make `_resolve_repo` return `gh.resolve_repo(proc)`.
- Preserve explicit `--repo` precedence and the current unresolved-repository admission result.
- Do not change `_run`, which remains the subprocess seam for unrelated admission commands.

### UPDATED: python/larch/state/_report.py

- Replace the raw repository lookup in the stall-recovery report path with `gh.resolve_repo(proc)`.
- Preserve `lookup-failed-open` and `current-repo-unresolved` when canonical resolution returns no repository.
- Leave the external report-helper invocation unchanged.

### UPDATED: python/larch/state/session_env.py

- Replace `_repo_from_gh_or_git`’s direct `repo_name_with_owner_read` call and CLI-mediated remote fallback with `gh.resolve_repo(runner) or ""`.
- Preserve the existing empty-string contract for unresolved repositories and missing-tool failures.
- Retain any local exception handling needed to prevent session setup from failing when the runner itself raises before canonical resolution can return.

### UPDATED: python/larch/issue/combine_issues.py

- Delete the unused `_repo` function and its duplicate JSON parsing logic.
- Keep `_resolve_repo` as the explicit-repository-or-`gh.resolve_repo(proc)` seam used by command paths.
- Remove imports that become unused after deleting the dead function.

### UPDATED: python/larch/issue/issue_block.py

- Import `gh`.
- Change `_repo` to return `gh.resolve_repo(proc) or ""`.
- Preserve existing positive-issue validation, slug validation, and unresolved-repository error text.

### UPDATED: python/larch/issue/issue_create.py

- Change `_resolve_repo` to return `gh.resolve_repo(proc) or ""`.
- Remove `_resolve_repo_for_fetch` only if a repository-wide reference search confirms it has no live caller, external import, or necessary test-seam use; otherwise repoint that wrapper to `_resolve_repo`.
- Preserve each caller’s existing empty-repository handling and output grammar.

### UPDATED: python/larch/issue/analyze_bugs.py

- Change `resolve_repo` to call `gh.resolve_repo(runner)` when no explicit repository was supplied.
- Preserve explicit repository precedence.
- Preserve `AnalyzeBugsError` and its current operator guidance when resolution fails.
- Remove parsing and error branches that duplicate canonical slug validation.

### UPDATED: python/larch/issue/analyze_issues.py

- Keep `_detect_repo` as a stable test seam, but implement it as `gh.resolve_repo(proc) or ""`.
- Remove local Git remote parsing fallback because the canonical resolver owns that behavior.
- Keep offline report behavior when canonical resolution returns an empty string.

### UPDATED: python/larch/issue/issue_wire.py

- Change `_resolve_issue_wire_repo` from `gh.resolve_repo_gh_only` to `gh.resolve_repo`.
- Preserve the existing `(None, "could not determine repo")` result for unresolved repositories and the resulting `FAILED=true` / `ERROR=` command behavior.
- Retain the `ShipError` mapping if canonical resolution can still raise through the supplied runner.

### UPDATED: python/larch/issue/tracking_issue.py

- Change `_resolve_repo_or_fail` from `gh.resolve_repo_gh_only` to `gh.resolve_repo`.
- Preserve explicit repository validation and existing `CliFailure` messages and exit codes.
- Pass `cwd` through to canonical resolution.

### UPDATED: python/larch/report/report_tokens_scan.py

- Replace ambient repository discovery from `repo_name_with_owner_read` with the canonical detailed resolver, not the lossy `gh.resolve_repo` adapter.
- Preserve `LARCH_REPORT_TOKENS_REPO` override precedence and its safe-slug validation.
- Preserve the existing `ShipError` for an invalid override.
- On canonical ambient success, use the valid slug from the detailed result.
- On unresolved ambient discovery, preserve the current repository-resolution diagnostic shape and return `None`:
  - when primary `gh` failed with a nonzero result, format the recorded primary failure through the existing redaction path and retain the current diagnostic suffix behavior;
  - when primary discovery raised `OSError`, retain the current dedicated `OSError` diagnostic behavior using the recorded failure category and detail;
  - when no primary failure detail exists, retain the existing unresolved-repository diagnostic;
  - do not rerun or locally reconstruct raw `gh repo view` discovery merely to obtain diagnostics.
- Do not weaken redaction or allow invalid ambient candidates through as repository slugs.

### UPDATED: python/larch/rendering/rendering.py

- Replace the ambient `repo_name_with_owner_read` call in diagram-comment upsert with `gh.resolve_repo(runner)`.
- Preserve explicit `--repo` precedence.
- Preserve `ShipError("could not determine repo")` for an unresolved ambient repository and the existing `UsageError` for an invalid explicit repository.
- Leave dry-run behavior and comment lookup/upsert behavior unchanged.

### UPDATED: python/tests/git/test_gh.py

- Add direct coverage for the canonical detailed-resolution states and confirm `resolve_repo` retains its `str | None` adapter contract.
- Cover:
  - valid primary `gh` discovery;
  - valid `origin` fallback;
  - missing or failed primary `gh` with valid fallback;
  - unresolved discovery;
  - invalid primary candidates;
  - malformed, non-empty `origin` candidates that are preserved as invalid rather than discarded; and
  - invalid primary candidates followed by valid fallback candidates.
- Assert the detailed result retains primary failure detail for:
  - nonzero primary results with stderr; and
  - `OSError`/missing-tool failures.
- Confirm `cwd` propagates to both primary and fallback commands.
- Confirm retired `resolve_repo_gh_only` has no remaining contract or consumers once removed.

### UPDATED: python/tests/design/test_clarify.py

- Update repository-resolution assertions to target the canonical detailed resolver contract rather than local `gh` argv construction.
- Cover successful canonical resolution, valid `origin` fallback, unresolved resolution, and explicit repository validation.
- Add regression cases where:
  - a non-empty invalid primary ambient candidate produces `ERROR=invalid-repo`; and
  - a malformed non-empty `origin` candidate produces `ERROR=invalid-repo`, rather than `could not determine repo`.
- Preserve current validation exit behavior and `cwd` handling.

### UPDATED: python/tests/design/test_design_pause.py

- Update `_resolve_repo` coverage to patch or fake `gh.resolve_repo`.
- Verify CLI and persisted repository values still bypass ambient resolution.
- Verify canonical fallback and empty-result behavior.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Adjust terminal failure-report fixtures that currently model the raw repository subprocess call.
- Verify a canonical resolved repository reaches the existing cross-repository filing helper.
- Verify an unresolved repository retains the existing Tier A fallback reason.

### UPDATED: python/tests/state/test_admission.py

- Patch `gh.resolve_repo` for admission paths that omit `--repo`.
- Verify explicit repositories bypass discovery.
- Preserve coverage for unresolved repository admission failures without coupling tests to raw `gh` argv.

### UPDATED: python/tests/state/test_stall_recovery.py

- Replace raw repository subprocess expectations with a `gh.resolve_repo` seam.
- Verify resolved and unresolved paths retain their current status and fallback `KEY=value` output.
- Keep helper subprocess assertions focused on the filing helper itself.

### UPDATED: python/tests/state/test_session_env.py

- Replace primary-`gh` and CLI remote-helper fixtures with canonical resolver fixtures.
- Verify a canonical repository is returned, unresolved discovery returns `""`, and missing-`gh` behavior remains non-fatal.
- Include a focused canonical remote-fallback case without duplicating resolver parser tests.

### UPDATED: python/tests/issue/test_combine_issues.py

- Remove stale fake responses that exist only for the deleted `_repo` JSON parser.
- Add or retain focused coverage that `_resolve_repo` honors an explicit value and delegates missing values to `gh.resolve_repo`.
- Keep existing combine-workflow tests independent of canonical resolver internals.

### UPDATED: python/tests/issue/test_issue_block.py

- Update repository-discovery setup to patch or fake `gh.resolve_repo`.
- Verify unresolved discovery still emits the current error and stops before GraphQL lookup.
- Verify explicit `--repo` bypasses discovery.

### UPDATED: python/tests/issue/test_issue_create.py

- Update tests that patch `_gh_read` or `_resolve_repo_for_fetch` solely for repository discovery.
- Patch `gh.resolve_repo` or the retained `_resolve_repo` seam instead.
- Verify create, list, fetch, and close paths retain their existing unresolved-repository output.
- Remove test references to `_resolve_repo_for_fetch` only when the wrapper is deleted.

### UPDATED: python/tests/issue/test_analyze_bugs.py

- Change repository lookup fixtures from JSON output to the plain slug or `None` contract returned by `gh.resolve_repo`.
- Verify explicit repository precedence.
- Verify resolution failure still raises `AnalyzeBugsError`.
- Include a canonical fallback acceptance case without retesting resolver parsing already covered by `python/tests/git/test_gh.py`.

### UPDATED: python/tests/issue/test_analyze_issues.py

- Keep tests that monkeypatch `_detect_repo`, since the named seam remains.
- Add focused coverage that `_detect_repo` delegates to `gh.resolve_repo` and maps `None` to an empty string.
- Preserve offline execution coverage when no repository is available.

### UPDATED: python/tests/issue/test_issue_wire.py

- Replace `resolve_repo_gh_only` fixtures with `gh.resolve_repo` fixtures.
- Verify explicit repositories bypass ambient discovery.
- Verify canonical success, canonical fallback acceptance, and unresolved resolution retain the current failed-output contract.

### UPDATED: python/tests/issue/test_tracking_issue.py

- Add or adjust focused tests for `_resolve_repo_or_fail`.
- Verify explicit valid and invalid repositories retain current behavior.
- Verify canonical fallback success and unresolved `CliFailure` behavior, including the current exit code.
- Verify `cwd` reaches `gh.resolve_repo`.

### UPDATED: python/tests/report/test_report_tokens_scan.py

- Replace raw `repo_name_with_owner_read` fixtures with detailed canonical resolver fixtures.
- Verify validated environment override precedence, canonical ambient success, unresolved diagnostic behavior, and no regression in invalid-override `ShipError` behavior.
- Add focused diagnostics regressions for final unresolved resolution after:
  - a nonzero primary `gh` failure with stderr, asserting the output retains the existing redacted diagnostic suffix and never leaks unredacted sensitive text; and
  - an `OSError` primary failure, asserting the existing dedicated diagnostic path is preserved.
- Verify a successful `origin` fallback suppresses the primary-failure diagnostic because repository resolution succeeded.
- Keep canonical discovery parsing details in `python/tests/git/test_gh.py`.

### UPDATED: python/tests/rendering/test_rendering.py

- Replace raw repository-read expectations with a `gh.resolve_repo` seam.
- Verify explicit valid repositories bypass discovery, canonical ambient resolution proceeds to existing comment behavior, unresolved ambient resolution raises the current `ShipError`, and invalid explicit repositories retain `UsageError`.

## Edge cases

- A failing or unavailable `gh repo view` may still permit a valid `origin` remote resolution; migrated callers must accept that canonical fallback where they previously performed equivalent fallback behavior.
- The canonical detailed resolver must preserve a non-empty invalid candidate from both primary `gh` discovery and `origin` fallback. In particular, a malformed remote-derived candidate must remain distinguishable from no remote candidate so `clarify` returns `invalid-repo`.
- If both sources fail to produce a valid slug, the detailed result must preserve invalid-candidate state for `clarify` and primary-failure detail for report-token diagnostics without exposing either through ordinary `resolve_repo`.
- Primary failure diagnostics must remain available after fallback failure:
  - nonzero primary stderr remains subject to the existing report-token redaction and formatting;
  - `OSError` retains its current dedicated report-token behavior;
  - successful fallback resolves the repository and must not emit an unresolved diagnostic.
- Explicit repository arguments and environment overrides must continue to outrank ambient discovery.
- Callers that validate explicit slugs must not weaken that validation merely because ambient resolution is centralized.
- Repository resolution with a caller-provided `cwd` must pass that directory through unchanged to both primary and remote discovery.
- Session setup must remain non-fatal when `gh` is unavailable and no usable Git remote exists.
- Offline analysis must continue when repository enrichment is optional.
- Removing `_resolve_repo_for_fetch` and `resolve_repo_gh_only` must not break tests, imports, or other repository consumers; search all Python sources and tests before deletion.

## Failure modes

- A detailed canonical resolver could accidentally expose an invalid candidate to callers that expect only `str | None`; keep `resolve_repo` as the validating adapter and limit detailed-result consumption to `clarify` and the diagnostic-only branch in `report_tokens_scan`.
- A lossy remote helper could collapse malformed non-empty `origin` data to absence; ensure the detailed canonical fallback preserves candidate presence and invalidity before validation.
- A caller may accidentally expose `None` where its public contract expects `""`.
- Replacing direct subprocess calls may bypass an existing test double and cause tests to invoke real `gh`; migrate tests to patch the canonical seam.
- Canonical `origin` fallback may intentionally turn a former primary-`gh` failure into success; tests must distinguish that expected change from regressions in caller-specific failure contracts.
- Routing report-token scanning through only the `str | None` adapter would discard its required failure diagnostic; consume detailed failure information there and retain existing redaction behavior.
- Broad `OSError` normalization in the shared resolver could hide a caller-required diagnostic; retain structured failure category and detail for report-token scanning while ordinary callers preserve their graceful unresolved behavior.
- Deleting a wrapper patched by tests or imported elsewhere may break a stable seam.
- Unused imports, stale suppressions, or raw resolver literals may remain after migration.

## Testing strategy

1. Run focused tests for all changed modules:
   - `python/tests/git/test_gh.py`
   - `python/tests/design/test_clarify.py`
   - `python/tests/design/test_design_pause.py`
   - `python/tests/design/test_design_lifecycle.py`
   - `python/tests/state/test_admission.py`
   - `python/tests/state/test_stall_recovery.py`
   - `python/tests/state/test_session_env.py`
   - `python/tests/issue/test_combine_issues.py`
   - `python/tests/issue/test_issue_block.py`
   - `python/tests/issue/test_issue_create.py`
   - `python/tests/issue/test_analyze_bugs.py`
   - `python/tests/issue/test_analyze_issues.py`
   - `python/tests/issue/test_issue_wire.py`
   - `python/tests/issue/test_tracking_issue.py`
   - `python/tests/report/test_report_tokens_scan.py`
   - `python/tests/rendering/test_rendering.py`
2. Run scoped Python lint and type checks on changed files through the repository’s changed-file validation flow.
3. Search all `python/larch/` source files for direct `["gh", "repo", "view", "--json", "nameWithOwner"]` construction and confirm no duplicated repository-discovery literal remains outside the canonical helper implementation in `python/larch/git/gh.py`.
4. Search all `python/larch/` and `python/tests/` Python files for `resolve_repo_gh_only`; require zero remaining references before merge.
5. Search all `python/larch/` Python files outside `python/larch/git/gh.py` for `repo_name_with_owner_read`; require zero remaining calls before merge.
6. Search all `python/larch/` for duplicated repository `origin` parsing or CLI-mediated remote-repository fallback and confirm the migrated sites delegate to the canonical resolver instead.
7. Confirm the canonical detailed resolver has focused coverage for malformed non-empty `origin` candidates and for retained primary nonzero-stderr and `OSError` failure detail.
8. Confirm report-token tests prove that unresolved ambient discovery preserves the current redacted diagnostic behavior, while successful canonical fallback produces a repository without an unresolved diagnostic.
9. Confirm excluded multi-field GitHub queries, filesystem path resolvers, and already-compliant surfaces remain unchanged.

## Acceptance

1. Run focused tests for all changed modules:
   - `python/tests/git/test_gh.py`
   - `python/tests/design/test_clarify.py`
   - `python/tests/design/test_design_pause.py`
   - `python/tests/design/test_design_lifecycle.py`
   - `python/tests/state/test_admission.py`
   - `python/tests/state/test_stall_recovery.py`
   - `python/tests/state/test_session_env.py`
   - `python/tests/issue/test_combine_issues.py`
   - `python/tests/issue/test_issue_block.py`
   - `python/tests/issue/test_issue_create.py`
   - `python/tests/issue/test_analyze_bugs.py`
   - `python/tests/issue/test_analyze_issues.py`
   - `python/tests/issue/test_issue_wire.py`
   - `python/tests/issue/test_tracking_issue.py`
   - `python/tests/report/test_report_tokens_scan.py`
   - `python/tests/rendering/test_rendering.py`
2. Run scoped Python lint and type checks on changed files through the repository’s changed-file validation flow.
3. Search all `python/larch/` source files for direct `["gh", "repo", "view", "--json", "nameWithOwner"]` construction and confirm no duplicated repository-discovery literal remains outside the canonical helper implementation in `python/larch/git/gh.py`.
4. Search all `python/larch/` and `python/tests/` Python files for `resolve_repo_gh_only`; require zero remaining references before merge.
5. Search all `python/larch/` Python files outside `python/larch/git/gh.py` for `repo_name_with_owner_read`; require zero remaining calls before merge.
6. Search all `python/larch/` for duplicated repository `origin` parsing or CLI-mediated remote-repository fallback and confirm the migrated sites delegate to the canonical resolver instead.
7. Confirm the canonical detailed resolver has focused coverage for malformed non-empty `origin` candidates and for retained primary nonzero-stderr and `OSError` failure detail.
8. Confirm report-token tests prove that unresolved ambient discovery preserves the current redacted diagnostic behavior, while successful canonical fallback produces a repository without an unresolved diagnostic.
9. Confirm excluded multi-field GitHub queries, filesystem path resolvers, and already-compliant surfaces remain unchanged.

oversize_override: operator
diff_lines: 438

## Test plan
(no test plan section in plan-file)
