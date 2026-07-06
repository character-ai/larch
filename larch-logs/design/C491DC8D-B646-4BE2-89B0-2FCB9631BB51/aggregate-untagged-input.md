### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py:538-541
- **Concern**: The UPDATED finalize.py section is empty even though `_rename_issue` still calls `runner.run(["gh", "issue", "view", ...])` outside `larch.git.gh`.. Scenario: Round 1 FINDING_6 called out finalize.py; the revised plan lists the file but gives no migration steps, so A5 still leaves a bounded read path without wrapper timeout/retry and the new `runner.run(["gh", ...])` lint will keep failing after other files move.
- **Proposed resolution**: Add finalize.py steps: route `_rename_issue` through an existing `_issue_view_read`/`issue_view_field_read` helper (or a small `title,state` wrapper), preserve `check=False` branching on non-zero reads, and delete the direct `runner.run` call.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py
- **Concern**: A3 writer discovery only counts direct `.write_text`/`.open`/shell patterns, but most seeded run-log artifacts are produced via `run_log_batch._LARCH_LOG_BATCHES` slug→`{slug}{ext}` writes (`batch="token-report"` → `token-report.json`, same for `timing-report`, `review-findings-full`, `oos-issues`, `run-statistics`, etc.).. Scenario: With the current seed list, the first `lint wire-artifact-pairing` run will report reader-without-writer for most run-log rows even though `_write_batch` is the real producer, forcing a large bogus baseline or blocking `py-lint-checks-fast`.
- **Proposed resolution**: Teach writer discovery to treat `_LARCH_LOG_BATCHES` plus `_write_batch`/`run-log append --batch <slug>` call sites as writers for `{slug}{extension}`, or temporarily drop batch-produced basenames from the initial manifest until that mapping exists.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:210-230
- **Concern**: The ci_monitor migration text points at `gh.pr_checks_text_read`, but `_gh_pr_checks` and `_read_pr_checks_text` use the JSON `--json name,state,bucket,link` path (and optional `--required`), not text output.. Scenario: Swapping to `pr_checks_text_read` changes the checks observation contract; leaving `_gh_pr_checks` as `runner.run(argv, ...)` also evades the static `runner.run(["gh", ...])` lint because argv is dynamic.
- **Proposed resolution**: Extend `gh.pr_checks_read` with `timeout` and `required` parameters, migrate `_gh_pr_checks`/`_read_pr_checks_text` to that helper, and remove the local `runner.run` gh argv builder.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/promote_release.py
- **Concern**: The MAY_UPDATE audit targets `python/larch/issue/promote_release.py`, but the only `promote_release.py` in-tree is `python/larch/release/promote_release.py` with multiple `proc.run(["gh", ...])` calls.. Scenario: An implementer following the plan path will skip the real module, leaving release promotion gh bypasses unaudited despite the MAY_UPDATE intent.
- **Proposed resolution**: Repoint the MAY_UPDATE entry to `python/larch/release/promote_release.py` and keep the dynamic-argv baseline note there.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py
- **Concern**: A3 writer detection omits Python touch writers. Scenario: The seed includes `.completed/step-5c-terminal` and `.completed/step-final-summary`, but existing runtime writers use `_touch(...)` and `Path.touch()` rather than `.write_text`, `.open`, or `atomic_write`; the new lint can report seeded live artifacts as missing writers or force bogus baseline rows.
- **Proposed resolution**: Count `Path.touch()` and the local `_touch(...)` wrapper as Python writer evidence when the artifact path is present.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py
- **Concern**: A3 production-only exclusion still lets test harnesses satisfy writer evidence. Scenario: The plan excludes only `python/tests/`, `python/test_fixtures/`, and `__pycache__`, while this repo also has flat and nested `test_*.py` files plus shell harnesses such as `scripts/test-hook-bg-poll-guard.sh` that write seeded sentinels; a missing runtime writer can be masked by test-only evidence.
- **Proposed resolution**: Exclude flat and nested Python test/helper files plus shell test harnesses from reader and writer evidence, and make the test-only-writer case cover both Python and shell tests.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py:538-540
- **Concern**: finalize.py is listed as UPDATED but has no migration steps. Scenario: _rename_issue still calls runner.run(["gh", "issue", "view", ...]) without a bounded timeout or gh wrapper, so A5 leaves a direct gh read in scope and the subprocess-via-runner lint will fail after other files migrate
- **Proposed resolution**: Add finalize.py bullets: route _rename_issue through gh.issue_view_state_url_read or gh.issue_view_title_body_read with default CI_STATUS_QUERY_TIMEOUT_SEC and preserve stalled-title skip behavior

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/tracking_issue.py:666-678,850-852
- **Concern**: tracking_issue migration covers only the issue-body gh api call. Scenario: The plan names one api body read, but tracking_issue.py also does paginated comments fetch and _fetch_issue_title via direct runner.run gh calls; after A5 those sites stay on unwrapped gh and fail lint
- **Proposed resolution**: Expand tracking_issue.py steps to migrate all three read sites to existing gh.issue_view_body/issue_comments_list_read/issue_view_field_read helpers (or thin api wrappers) with preserved CliFailure behavior

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:729-825
- **Concern**: ci_monitor pr checks --required path has no gh wrapper target. Scenario: pr_checks_read and pr_checks_text_read omit --required, while ci_monitor.py uses gh pr checks --required in both JSON (_gh_pr_checks) and text (_read_pr_checks_text) modes; routing only through current helpers would drop --required semantics
- **Proposed resolution**: Add optional required: bool = False to pr_checks_read and pr_checks_text_read (append --required to argv when true), document in gh.py UPDATED, and migrate ci_monitor call sites to those helpers

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:284-289
- **Concern**: A3 writer discovery does not cover run-log batch slug writes. Scenario: Many seeded artifacts (token-report.json, review-panel-manifest.ndjson, etc.) are produced via _batch_path f"{batch}{extension}" and _write_batch(batch=...), not literal basename strings in write_text/atomic_write calls; literal-only writer scan will mark them reader-only and force bogus baselines
- **Proposed resolution**: In lint_wire_artifact_pairing.py, treat _LARCH_LOG_BATCHES keys plus static batch= arguments to run-log write helpers as writers for matching {slug}{extension} manifest rows

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/release/promote_release.py
- **Concern**: MAY_UPDATE promote_release path is wrong. Scenario: The plan points at python/larch/issue/promote_release.py, which does not exist; the real module is python/larch/release/promote_release.py with multiple proc.run(["gh", ...]) calls, so the audit step is skipped
- **Proposed resolution**: Fix the MAY_UPDATE path to python/larch/release/promote_release.py and note proc.run gh literals there need gh-wrapper migration or a subprocess-via-runner-gh baseline row

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py (planned writer scan)
- **Concern**: A3 writer discovery omits real writer shapes for seeded artifacts. Scenario: The plan only lists write_text/open/atomic_write plus shell redirects. Seeded sentinels are written with Path.touch or _touch, for example python/larch/design/design_terminal.py:894 and python/larch/design/design_step5c.py:518. Run-log artifacts such as review-scout-manifest.json are also written through --batch review-scout-manifest plus _LARCH_LOG_BATCHES extensions, not full filename literals. The lint will miss real writers and either fail or force bogus baseline rows.
- **Proposed resolution**: Count touch/_touch file creation and map run-log batch names plus extensions to manifest artifact names. Add focused tests for a touched relative_path sentinel and a run-log batch artifact.

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/tracking_issue.py:666-851
- **Concern**: A5 tracking_issue migration leaves direct gh reads. Scenario: The plan only names the issue-body gh api call, but the same path also reads comments at lines 669-676 and _fetch_issue_title uses gh issue view at 850-851. After the planned lint lands, these runner.run(["gh", ...]) literals outside larch/git/gh.py still fail subprocess-via-runner and bypass the default read timeout.
- **Proposed resolution**: Expand the tracking_issue.py step to migrate the body, comments, and title reads through larch.git.gh helpers while preserving cwd and return-code behavior.

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py:538-541
- **Concern**: FINDING_6 fix is incomplete: `finalize.py` is listed under `### UPDATED:` with no migration steps.. Scenario: `_rename_issue` still calls `runner.run(["gh", "issue", "view", ...])` directly. After A5, that remains a bypass unless migrated, and the subprocess lint will keep failing on a file the plan names but never specifies.
- **Proposed resolution**: Add a `finalize.py` bullet: route `_rename_issue` read-only `gh issue view` through `larch.git.gh` (new or existing helper), preserve `CommandResult` branching and `check=False` semantics, and thread the default read timeout.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:210-230
- **Concern**: FINDING_2 fix targets the wrong gh helper for the JSON-first PR-checks path.. Scenario: `ci_monitor._gh_pr_checks` uses `gh pr checks ... --json name,state,bucket,link` and `_resolve_checks_observation` classifies from JSON. The plan routes PR-check sites through `gh.pr_checks_text_read`, which omits `--json` and would force the text fallback path, changing classification and run-id extraction.
- **Proposed resolution**: Migrate `_gh_pr_checks` to `gh.pr_checks_read` (extend it with `timeout=` and `required=` if needed), keep JSON stdout parsing unchanged, and delete the local `runner.run(["gh", ...])` builder.

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:1000-1028
- **Concern**: `collect_failed_logs` migration path is underspecified and mismatched to `gh.run_logs_failed`.. Scenario: `collect_failed_logs` tails the last `CI_MONITOR_LOG_TAIL_LINES` lines and uses a different pointer string. `gh.run_logs_failed` returns the full `--log-failed` stream with another pointer. A naive swap changes CI-fix log excerpts and in-progress handling.
- **Proposed resolution**: Specify migration explicitly: either add a bounded `gh.run_logs_failed_tail(..., tail_lines=...)` helper that preserves current tail semantics, or document why full-log behavior is acceptable and update callers/tests accordingly.

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/wire-artifact-manifest.json
- **Concern**: A3 writer discovery will false-fail several seeded run-log artifacts.. Scenario: The plan matches writers only to listed write APIs (`.write_text`, `.open("w"|"a")`, `atomic_write`) plus shell redirects. Many seeded rows (`token-report.json`, `timing-report.json`, `review-panel-manifest.ndjson`, `review-scout-manifest.json`, and similar) are produced via `_write_batch` / `run_log_batch.BATCHES` using batch keys plus suffixes, not literal `*.json` paths in those APIs. Readers already reference the final basenames, so the first lint run will report missing writers or force bogus baselines.
- **Proposed resolution**: Extend writer discovery to treat `run_log_batch.BATCHES` keys combined with `BatchInfo` suffixes (and `_write_batch` / `_atomic_write` call sites) as writers for `{batch}{suffix}` filenames, or drop those rows from the initial manifest until that discovery exists; add a unit test with a `batch="token-report"` write and a `token-report.json` reader.

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py (planned); scripts/test-hook-bg-poll-guard.sh:463-474
- **Concern**: A3 shell writer discovery still counts test harness writers. Scenario: The planned shell writer scope includes all of scripts/, so test harness forgery examples like touch and printf to .completed/step-3-terminal can satisfy the writer side for seeded artifacts even if the production writer is missing. That preserves the defect class the lint is meant to catch.
- **Proposed resolution**: Exclude shell test harnesses and fixtures such as scripts/test-*.sh from writer evidence, or otherwise mark only production scripts as writer-eligible. Add a shell test-only writer fixture to the lint tests.

### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py:538-540; python/larch/issue/tracking_issue.py:669-679,849-852
- **Concern**: A5 runner.run gh sweep is incomplete for lint-hit sites. Scenario: The plan leaves finalize with an empty update section and only names one tracking_issue gh api body read. The new runner.run(["gh", ...]) lint would still fail on finalize _rename_issue, tracking_issue comments fetch, and tracking_issue title fetch, or those reads would keep bypassing the timeout wrapper.
- **Proposed resolution**: Explicitly migrate these remaining runner.run gh reads through larch.git.gh helpers, preserving cwd, return-code, and caller branching behavior.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/finalize.py:538-541
- **Concern**: `### UPDATED: python/larch/state/finalize.py` has no migration steps while `_rename_issue` still calls `runner.run(["gh", "issue", "view", ...])` outside `_retry_read`.. Scenario: Round-1 FINDING_6 listed `finalize.py`; the revised plan leaves the section empty. A5 default timeouts, `GhReadTimeout` routing, and `lint subprocess-via-runner` gh findings will still fire on stall/issue rename reads.
- **Proposed resolution**: Add finalize steps: route `_rename_issue` through a `larch.git.gh` read helper (or `_retry_read` with default `CI_STATUS_QUERY_TIMEOUT_SEC`), preserve `CommandResult` branching, and note any other gh reads in this file.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:1000-1029
- **Concern**: `collect_failed_logs` migration is underspecified: `gh.run_logs_failed` / `gh.run_log_read` differ from the local helper (tail to `CI_MONITOR_LOG_TAIL_LINES`, `redact.redact`, `LogCollectResult` states).. Scenario: Routing `collect_failed_logs` through existing gh helpers as written would change log volume, redaction, and in-progress handling in the CI poll loop (#5066 class) even if a timeout is added.
- **Proposed resolution**: Keep `collect_failed_logs` and thread `_retry_read`/`_gh` with default timeout inside it (or add a gh helper that matches tail+redaction+`LogCollectResult`); do not alias to `run_logs_failed` without a parity contract.

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:449-453
- **Concern**: Required PR-check reads still use literal `runner.run(["gh", "pr", "checks", ...])` and are not covered by the `pr_checks_text_read` migration text.. Scenario: After the A5 lint extension, this site is a hard failure; today it already bypasses centralized gh read policy while non-required checks use `gh.pr_checks_text_read`.
- **Proposed resolution**: Extend `gh.pr_checks_text_read` with a `required: bool` (or add a sibling helper) and switch `_read_pr_checks_text`/`_gh_pr_checks` call sites to it with the default timeout.

### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py
- **Concern**: A3 pairing rule text says "Fail when a basename has at least one reader..." but the seed manifest includes `kind=relative_path` rows (`.completed/*`, dotted env sidecars).. Scenario: An implementer following the basename-only sentence can enforce pairing only for basename rows, leaving seeded relative-path wires unratcheted and false-negative on the #6211 defect class.
- **Proposed resolution**: Change the rule to "each manifest row (by `(kind, artifact)`)" and specify reader/writer matching per kind (basename token vs full relative path suffix).

### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_wire_artifact_pairing.py
- **Concern**: A3 does not define how shell/Python writer discovery matches `relative_path` artifacts such as `.completed/step-3-terminal`.. Scenario: Shell writers emit quoted paths like `"$DESIGN_TMPDIR/.completed/step-3-terminal"`; basename-only scans miss the writer and force bogus baselines or fail clean trees for seeded sentinels.
- **Proposed resolution**: Document and implement path-aware matching: for `relative_path`, accept writer evidence for the full artifact string or a anchored `/.completed/<name>` suffix in `scripts/` and `skills/*/scripts/`; add/keep harness coverage beyond basename cases.
