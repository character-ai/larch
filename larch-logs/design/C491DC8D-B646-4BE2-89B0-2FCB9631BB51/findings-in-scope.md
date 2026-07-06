### FINDING_1: Unwrapped gh reads still remain in finalize and tracking_issue
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: The A5 gh-read migration is still incomplete: `finalize.py` keeps a direct `runner.run(["gh", "issue", "view", ...])` path in `_rename_issue`, and `tracking_issue.py` still has direct gh reads for the issue body, comments, and title. Those callsites would continue to bypass the centralized wrapper timeout/retry policy and trip the new subprocess-via-runner lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add finalize.py steps: route `_rename_issue` through an existing `_issue_view_read`/`issue_view_field_read` helper (or a small `title,state` wrapper), preserve `check=False` branching on non-zero reads, and delete the direct `runner.run` call.
  - From Cursor-Innovation: Add finalize.py bullets: route _rename_issue through gh.issue_view_state_url_read or gh.issue_view_title_body_read with default CI_STATUS_QUERY_TIMEOUT_SEC and preserve stalled-title skip behavior
  - From Cursor-Pragmatic: Add a `finalize.py` bullet: route `_rename_issue` read-only `gh issue view` through `larch.git.gh` (new or existing helper), preserve `CommandResult` branching and `check=False` semantics, and thread the default read timeout.
  - From Cursor-Requirements: Add finalize steps: route `_rename_issue` through a `larch.git.gh` read helper (or `_retry_read` with default `CI_STATUS_QUERY_TIMEOUT_SEC`), preserve `CommandResult` branching, and note any other gh reads in this file.
  - From Cursor-Innovation: Expand tracking_issue.py steps to migrate all three read sites to existing gh.issue_view_body/issue_comments_list_read/issue_view_field_read helpers (or thin api wrappers) with preserved CliFailure behavior
  - From Codex-Innovation: Expand the tracking_issue.py step to migrate the body, comments, and title reads through larch.git.gh helpers while preserving cwd and return-code behavior.
  - From Cursor-Pragmatic: Explicitly migrate these remaining runner.run gh reads through larch.git.gh helpers, preserving cwd, return-code, and caller branching behavior.

### FINDING_2: Wire-artifact lint misses batch and touch writers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: A3 writer discovery only matches literal write/open/atomic_write/shell-redirect shapes, so it misses run-log batch producers and Python touch-based sentinels. Seeded artifacts like `token-report.json` and `.completed/step-5c-terminal` can therefore look writerless or force a bogus baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Teach writer discovery to treat `_LARCH_LOG_BATCHES` plus `_write_batch`/`run-log append --batch <slug>` call sites as writers for `{slug}{extension}`, or temporarily drop batch-produced basenames from the initial manifest until that mapping exists.
  - From Codex-Arch: Count `Path.touch()` and the local `_touch(...)` wrapper as Python writer evidence when the artifact path is present.
  - From Cursor-Innovation: In lint_wire_artifact_pairing.py, treat _LARCH_LOG_BATCHES keys plus static batch= arguments to run-log write helpers as writers for matching {slug}{extension} manifest rows
  - From Codex-Innovation: Count touch/_touch file creation and map run-log batch names plus extensions to manifest artifact names. Add focused tests for a touched relative_path sentinel and a run-log batch artifact.
  - From Cursor-Pragmatic: Extend writer discovery to treat `run_log_batch.BATCHES` keys combined with `BatchInfo` suffixes (and `_write_batch` / `_atomic_write` call sites) as writers for `{batch}{suffix}` filenames, or drop those rows from the initial manifest until that discovery exists; add a unit test with a `batch="token-report"` write and a `token-report.json` reader.

### FINDING_3: PR-check migration points at the wrong gh helper
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The PR-check path is JSON-first and also needs `--required`, but the plan points at the text helper. Switching helpers blindly would change classification and run-id extraction, and required checks would lose semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `gh.pr_checks_read` with `timeout` and `required` parameters, migrate `_gh_pr_checks`/`_read_pr_checks_text` to that helper, and remove the local `runner.run` gh argv builder.
  - From Cursor-Innovation: Add optional required: bool = False to pr_checks_read and pr_checks_text_read (append --required to argv when true), document in gh.py UPDATED, and migrate ci_monitor call sites to those helpers
  - From Cursor-Pragmatic: Migrate `_gh_pr_checks` to `gh.pr_checks_read` (extend it with `timeout=` and `required=` if needed), keep JSON stdout parsing unchanged, and delete the local `runner.run(["gh", ...])` builder.
  - From Cursor-Requirements: Extend `gh.pr_checks_text_read` with a `required: bool` (or add a sibling helper) and switch `_read_pr_checks_text`/`_gh_pr_checks` call sites to it with the default timeout.

### FINDING_4: Promote-release path points at the wrong module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The MAY_UPDATE entry targets a nonexistent `python/larch/issue/promote_release.py`, leaving the real release-promotion gh callsites outside the intended audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Repoint the MAY_UPDATE entry to `python/larch/release/promote_release.py` and keep the dynamic-argv baseline note there.
  - From Cursor-Innovation: Fix the MAY_UPDATE path to python/larch/release/promote_release.py and note proc.run gh literals there need gh-wrapper migration or a subprocess-via-runner-gh baseline row

### FINDING_5: collect_failed_logs migration needs a parity contract
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `collect_failed_logs` cannot be swapped to `gh.run_logs_failed` mechanically because it currently tails the log, redacts it, and reports in-progress state differently. The migration needs an explicit parity contract or a new helper that preserves those semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify migration explicitly: either add a bounded `gh.run_logs_failed_tail(..., tail_lines=...)` helper that preserves current tail semantics, or document why full-log behavior is acceptable and update callers/tests accordingly.
  - From Cursor-Requirements: Keep `collect_failed_logs` and thread `_retry_read`/`_gh` with default timeout inside it (or add a gh helper that matches tail+redaction+`LogCollectResult`); do not alias to `run_logs_failed` without a parity contract.

### FINDING_6: Test harness writers contaminate writer evidence
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: major
- **Concern**: Test-only writers still satisfy the writer side if test harnesses and fixtures are counted. That lets `touch`/`printf` in shell tests or Python test helpers mask missing production writers for the seeded artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Exclude flat and nested Python test/helper files plus shell test harnesses from reader and writer evidence, and make the test-only-writer case cover both Python and shell tests.
  - From Codex-Pragmatic: Exclude shell test harnesses and fixtures such as scripts/test-*.sh from writer evidence, or otherwise mark only production scripts as writer-eligible. Add a shell test-only writer fixture to the lint tests.

### FINDING_7: relative_path artifacts need path-aware pairing
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: A3 is still phrased as basename-only pairing even though the seed manifest includes `relative_path` artifacts. Those rows need path-aware matching by `(kind, artifact)` so `.completed/*` sentinels are ratcheted correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Change the rule to "each manifest row (by `(kind, artifact)`)" and specify reader/writer matching per kind (basename token vs full relative path suffix).
  - From Cursor-Requirements: Document and implement path-aware matching: for `relative_path`, accept writer evidence for the full artifact string or a anchored `/.completed/<name>` suffix in `scripts/` and `skills/*/scripts/`; add/keep harness coverage beyond basename cases.
