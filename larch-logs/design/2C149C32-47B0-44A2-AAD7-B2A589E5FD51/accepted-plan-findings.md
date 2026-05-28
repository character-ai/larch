### FINDING_1: Python argv-list `gh` calls are missed
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-wiring-placement, Codex-dyn-wiring-placement
- **Severity**: important
- **Concern**: Planned Python coverage does not match normal subprocess argv-list forms because the proposed regex requires whitespace after `gh`; calls like `subprocess.run(["gh", "issue", "create", "--body", "x"])` would bypass the lint while the plan and harness advertise that they fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add a Python-specific argv-list pattern or broaden the gh token matcher to accept quoted gh followed by a comma, and keep the planned Python harness case
  - From Cursor-Edge, Codex-Edge: Add a separate exact Python argv-list pattern for quoted `gh` followed by comma and quoted `--body`/`--notes` excluding file variants, or drop `.py` from this lint and hook if Python coverage is not intended
  - From Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements: Add a minimal second awk pattern for quoted argv/list forms, or narrow the PR to .sh only by removing .py from hook/docs/tests
  - From Cursor-Pragmatic, Codex-Pragmatic: Widen the token handling to cover quoted argv-list forms like "gh", or drop .py from scope only if shell-only is intended
  - From Cursor-dyn-wiring-placement, Codex-dyn-wiring-placement: Either narrow the hook/files/docs/test scope to .sh only, or minimally widen the gh token match to cover quoted/list argv forms such as "gh", before --body or --notes.


### FINDING_2: Tracked `larch-logs` files remain in repo enumeration
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned script says `larch-logs` is excluded, but the `git ls-files` enumeration path still includes tracked `.sh` and `.py` artifacts under `larch-logs`; pre-commit excludes do not constrain a `pass_filenames: false` hook's internal file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Filter larch-logs in the git enumeration too, for example with an exclude pathspec or a case filter before scan_file
  - From Cursor-Edge, Codex-Edge: Filter `larch-logs/*` in the git enumeration too, for example with an exclude pathspec or a rel-path skip before `scan_file`
  - From Cursor-Pragmatic, Codex-Pragmatic: Filter larch-logs in the git ls-files branch too, either with an exclude pathspec or a rel-path skip before scan_file
  - From Cursor-Requirements, Codex-Requirements: Filter larch-logs in the git ls-files path too, for example with a case skip or git pathspec exclude, and add a small harness fixture covering tracked larch-logs exclusion if that contract remains stated


### FINDING_3: Regression harness can flag its own forbidden fixtures
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned test script contains bad-case fixture lines in its own source, so the new repo-wide lint can fail on `scripts/test-lint-gh-body-inline.sh` before the harness reaches the generated temporary fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Specify fixture construction that does not match the source scan while still generating unsuppressed temp files, for example split literals or strip temporary allow comments before running the lint

