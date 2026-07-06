### FINDING_1: Wire-manifest seed identities don't match on-disk names
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: The A3 seed list in `python/wire-artifact-manifest.json` uses artifact names that do not match the actual on-disk wires used by the code, especially the leading-dot `.ship-route-exit-handoff.env` and `.design-step5c-status.env` sidecars, so reader/writer pairing will miss the real artifacts or force bogus baseline rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Fix the seed manifest to the dotted basenames (or kind:relative_path rows that match the real paths). Drop or rename the incorrect entries before bootstrap."
  - From Cursor-Innovation: "Use .design-step5c-status.env (relative_path or basename with leading dot) and drop step-5c-status.env"
  - From Cursor-Innovation: "Add a relative_path row for .ship-route-exit-handoff.env (and keep or baseline the committed batch name separately if needed)"
  - From Cursor-Pragmatic: "Replace seed entry with .design-step5c-status.env (relative_path kind if needed)"
  - From Cursor-Requirements: "Add .design-step5c-status.env with kind relative_path or basename as implemented; drop step-5c-status.env"
  - From Cursor-dyn-Lint Ratchet Specialist: "Seed manifest identities from exact on-disk names (including leading dots and design prefixes) or add an explicit relative_path kind whose artifact string matches code literals."


### FINDING_2: ci_monitor.py still bypasses the gh wrapper
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The A5 migration still leaves `python/larch/implement/ci_monitor.py` doing direct `runner.run(["gh", ...])` work, including `collect_failed_logs` without a bounded timeout, so CI can still hang and the subprocess-via-runner lint will flag the file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Route through larch.git.gh (e.g. run_logs_failed or a shared read helper) with the default read timeout, and add it to the explicit A5 caller migration list."
  - From Codex-Arch: "Add python/larch/implement/ci_monitor.py to the firm updates and route both checks paths through larch.git.gh while preserving the required flag and CI_STATUS_QUERY_TIMEOUT_SEC"
  - From Cursor-Innovation: "Add ### UPDATED: python/larch/implement/ci_monitor.py: route pr checks and collect_failed_logs through larch.git.gh read helpers with bounded timeouts; remove direct runner.run gh literals"
  - From Cursor-Pragmatic: "Add UPDATED python/larch/implement/ci_monitor.py: route log collection through gh.run_logs_failed (or gh.run_log_read) and pr checks through existing gh.pr_checks_text_read for both branches"
  - From Cursor-Requirements: "Add python/larch/implement/ci_monitor.py to ### UPDATED; route both sites through larch.git.gh (extend pr_checks_text_read or add a --required variant for the checks call; use a timeout-bearing run-log-failed read for log collection)"


### FINDING_3: gh read timeouts need one default and one failure type
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: `_retry_read` now applies a default read timeout, but `pr_view` still only turns `EXIT_TIMEOUT` into `GhReadTimeout` when the caller explicitly passed `timeout=`, so callers that rely on the default will still see a generic read failure instead of the timeout signal the poll paths expect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Raise GhReadTimeout on EXIT_TIMEOUT whenever the effective read timeout was applied (default or explicit). Add a test with timeout omitted and a fake EXIT_TIMEOUT result."
  - From Cursor-dyn-Lint Ratchet Specialist: "Raise GhReadTimeout on EXIT_TIMEOUT whenever the effective read timeout is bounded (default or explicit), and update python/tests/git/test_gh.py timeout expectations accordingly."
  - From Cursor-dyn-Lint Ratchet Specialist: "Specify the default constant (reuse CI_STATUS_QUERY_TIMEOUT_SEC or document a single new value) in the plan and test it in python/tests/git/test_gh.py."


### FINDING_4: Writer discovery must see shell-written sentinels
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A3 writer discovery still misses shell-written sentinels under `skills/*/scripts`, so real writers for `.completed/*`, `.bg-wait-active`, and similar artifacts will not be seen even though the manifest seeds depend on them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Either extend writer detection to skills/*/scripts shell writes (printf/>, touch) or audit each seeded row and omit/bashline-only artifacts until that scope is in the lint."
  - From Cursor-Innovation: "Document and implement shell write detection in scripts/ (redirection, touch, printf-to-file) alongside Python write APIs"
  - From Cursor-Pragmatic: "Document and implement shell write detection in scripts/ (redirection, touch, printf-to-file) alongside Python write APIs"
  - From Cursor-Requirements: "Define shell writer evidence in scripts/ (redirection, tee, atomic_write CLI calls) mirroring lint_bg_wait_writer_parity; add harness cases for bash-written manifest entries"


### FINDING_5: Writer discovery must exclude tests and fixtures
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: A3 writer evidence can be satisfied by tests, fixtures, or support code, which lets the lint pass on non-production writers and masks the missing-runtime-writer defect it is meant to catch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Exclude tests, fixtures, pycache, and generated logs from writer discovery; add a fixture where only a test file writes an artifact and a production reader still fails the lint"
  - From Codex-Arch: "Exclude tests, fixtures, pycache, and generated logs from writer discovery; add a fixture where only a test file writes an artifact and a production reader still fails the lint"
  - From Codex-Innovation: "Exclude tests, fixtures, generated logs, and harness-only writers from writer evidence; add a fixture proving test-only writers do not satisfy the lint"
  - From Codex-Pragmatic: "Restrict writer evidence to runtime code only, excluding python/tests, python/test_fixtures, __pycache__, and other non-runtime analysis fixtures"
  - From Cursor-dyn-Lint Ratchet Specialist: "Scan python/ for runtime writers but exclude pytest, support, and fixture trees by the same production-scope rules as existing lints; keep top-level runtime files such as python/cli.py eligible; add test_test_fixture_writer_does_not_satisfy_reader"


### FINDING_6: Other direct gh callers remain outside the wrapper
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: Several non-`ci_monitor.py` call sites still invoke `gh` directly outside `python/larch/git/gh.py`, including `clarify.py`, `state/finalize.py`, `tracking_issue.py`, `issue_create.py`, and `promote_release.py`, so the new lint will still fail and some reads will keep bypassing centralized wrapper behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Add clarify.py and state/finalize.py to the A5 caller migration list (or an explicit baseline only with reasons)"
  - From Codex-Innovation: "Extend the A5 sweep to every current direct literal `runner.run([\"gh\", ...])` outside `python/larch/git/gh.py`, or baseline only deliberate exceptions with reasons"
  - From Cursor-Pragmatic: "Add both files to the A5 migration list; use gh.resolve_repo_gh_only / issue_view_field_read (or thin wrappers) preserving return-code behavior"
  - From Cursor-Pragmatic: "Expand tracking_issue.py step to migrate all three call sites; reuse gh.issue_comments_list_read and an issue title read helper"
  - From Codex-Pragmatic: "Add firm update entries for the missed files and route those reads through larch.git.gh helpers, or explicitly narrow and justify any deliberate exemption"
  - From Codex-dyn-Lint Ratchet Specialist: "Add an explicit AST sweep step for every literal .run([\"gh\", ...]) and proc.run([\"gh\", ...]) under python/larch/; update all hits or add reason-bearing intentional baselines; include a repository-fixture test that fails on an unlisted direct gh call outside python/larch/git/gh.py"


### FINDING_7: A4 guard detection and rollout are too narrow
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Cursor-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: The empty-array Bash rule does not yet recognize existing length-checked guard patterns as safe, and the rollout still needs a cleanup or baseline plan for the current committed hits, so the new lint would generate avoidable false positives on already-safe scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Document that a preceding \"${#name[@]}\" -gt 0 guard satisfies A4, or add that guard to the awk rule before landing A4"
  - From Codex-Pragmatic: "Add a firm sweep step and file entries to guard, fix, or reason-suppress each current hit, or add the reason-bearing Bash baseline the issue calls for"
  - From Cursor-dyn-Lint Ratchet Specialist: "Treat a preceding non-comment [ \"${#name[@]}\" -gt 0 ] (or -eq 0 early-return) on the same array as a guard in the A4 awk pass, or document and harness the expected suppression count before enabling the rule repo-wide."


### FINDING_9: Wire-manifest row schema needs one shape
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: The A3 manifest contract is internally inconsistent about whether rows are basename-only strings or structured `kind`/`artifact` objects, so the validator, baseline keys, and seed data need one explicit schema before dotted or slash-containing artifacts can be represented reliably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: "Define one manifest record shape (artifact string plus optional kind) and align validator, baseline keys, and docs to it"
  - From Cursor-dyn-Lint Ratchet Specialist: "Mandate one manifest row schema up front (e.g. {kind, artifact}) with identity = artifact string; reject slashes for kind=basename; require kind=relative_path for .completed/* entries before seeding."


### FINDING_13:
- **Reviewer(s)**: Codex-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-28; <TMPDIR>/plan.txt:41-70
- **Concern**: [SCOPE-REDUCTION] A3 assigns one reason-bearing exact-key schema to both the manifest and baseline while also seeding manifest entries as plain names and relative paths. Scenario: The proposed python/wire-artifact-manifest.json cannot both be an array of basenames or relative_path rows and require non-empty reason fields; if implemented literally, python/tests/lint/test_lint_wire_artifact_pairing.py::test_malformed_manifest_exits_2 can reject the shipped seed or force suppression reasons into the manifest instead of the baseline
- **Proposed resolution**: Split schemas: manifest rows use exact artifact plus optional kind with no reason; baseline rows use exact artifact, side, and non-empty reason; make duplicate identity kind plus artifact when relative_path exists


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


