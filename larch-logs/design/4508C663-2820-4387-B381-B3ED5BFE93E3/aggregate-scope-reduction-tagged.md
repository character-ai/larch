### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: Makefile
- **Concern**: [SCOPE-REDUCTION] "Add it to the local lint battery" is ambiguous and can reintroduce the rejected duplicate-run shape (G-Enf-1).. Scenario: `make lint` already ends with `lint-only`, which runs every pre-commit hook. Adding `lint-doc-pointer-paths` to the top-level `lint:` target would run the same check twice, matching the round-1 rejected Makefile duplication concern.
- **Proposed resolution**: State explicitly that wiring mirrors `lint-markdown-heading-fence-state`: `py-lint-checks-fast`, focused Make target, tests, and pre-commit only; do not add a direct dependency on the top-level `lint:` target.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: [SCOPE-REDUCTION] Rejecting symlinked required documents exceeds the fixed two-document pointer-lint contract. Scenario: A normal checkout has regular Tier-1 documents; this adds hostile-filesystem policy and fixture complexity without affecting pointer detection or any acceptance criterion
- **Proposed resolution**: Keep ordinary missing/read/UTF-8 failures as tool errors, but remove the explicit symlink rejection and its dedicated test coverage
