### FINDING_1: Pre-commit hook receives unintended filenames
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The planned repo-wide lint hook does not disable filename passing or specify system execution, so staged paths can be passed as unsupported positional arguments and cause the hook to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: .pre-commit-config.yaml, mirror lint-readability-preamble / lint-em-dash-output: language: system, pass_filenames: false, always_run: true, and a files regex for AGENTS.md, SECURITY.md, the lint module, its test, and python/lint-module-manifest.json. State that main() always scans both Tier-1 docs and accepts no positional file args.
  - From Cursor-Innovation: Mirror `lint-markdown-heading-fence-state`: `language: system`, `pass_filenames: false`, `always_run: true`, plus the planned `files:` scope for AGENTS.md, SECURITY.md, and the lint implementation/tests


### FINDING_2: SECURITY.md deletion rationales are not required
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: minor
- **Concern**: The plan does not bind acceptance criterion 7, allowing deleted SECURITY.md passages to lack deletion rationales in the PR description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit SECURITY.md sweep bullet or Testing strategy step: for each deleted passage, record a one-line rationale in the PR description (or a short PR-body checklist) before merge.
  - From Cursor-Requirements: Add one bullet under ### UPDATED: SECURITY.md or Testing strategy: when a dead pointer is removed rather than repointed, record the deletion rationale in the PR description and verify the final diff against acceptance criterion 7


### FINDING_4: SECURITY.md contains unenumerated stale script references
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Security Doc Integrity
- **Severity**: major
- **Concern**: Prefix-filtered enumeration does not detect bare script basenames or other unprefixed deleted machinery, so stale security guidance can remain after the 24-token check passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit SECURITY.md sweep bullet: while rewriting deleted-machinery passages (assessor lane, breadcrumb publish, ship driver), fix every stale bare `` `*.sh` `` basename and other non-enumerated dead cites; keep acceptance on enumeration printing nothing, but do not treat the 24-count alone as complete
  - From Cursor-dyn-Security Doc Integrity: Expand ### UPDATED: SECURITY.md with explicit rewrite rows for :335 (Step 0 `python/cli.py bootstrap invoke` / session setup), :366 (Python `run-log publish-breadcrumbs`), and the breadcrumb block (:446-447) naming `python/cli.py run-log publish-breadcrumbs` / `python/larch/report/run_log_commit.py`


### FINDING_5: Gitignored local paths remain visible to enumeration
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Suppressing or environment-depending on gitignored `.claude/*` paths does not satisfy the required enumeration, which ignores suppressions and can behave differently on developer machines versus CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Resolve the conflict in the plan: do not leave the generated path as an enumerated inline-backtick token, while retaining accurate generated-artifact guidance
  - From Cursor-Pragmatic: Extend the SECURITY.md sweep step to require reason-bearing same-line suppressions on lines 253 and 337 for all gitignored dev-local `.claude/*` runtime paths (settings.local.json and hook-audit.log), not only hook-audit.log. Add an acceptance check that runs `python3 python/cli.py lint doc-pointer-paths` in a clean tree (or a fixture tree without those files), not enumeration alone.
  - From Codex-Requirements: Rewrite the row to retain the generated-file rationale without a path-shaped backticked token, rather than suppressing it.


### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: SECURITY.md:337
- **Concern**: [SCOPE-REDUCTION] G-Md-2: Planned suppression retains a dead SECURITY.md pointer. Scenario: The required raw enumeration is not suppression-aware, so `.claude/hook-audit.log` remains a reported dead pointer and acceptance criterion 2 cannot pass with a correct scanner.
- **Proposed resolution**: Rewrite the row to describe the generated audit log without a path-shaped inline token, rather than adding a lint suppression.


