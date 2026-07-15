### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: The lint module plan still does not pin the approved-prefix tuple, forbidden-character set, or token regex to match the issue enumeration snippet verbatim (G-Enf-1).. Scenario: Acceptance criterion 2 requires the supplied enumeration to print nothing while criterion 1 runs the CLI verb. If the implementer copies only the plan bullets, the scanner can diverge on edge tokens (for example placeholder filtering) and pass one check while failing the other.
- **Proposed resolution**: Add one plan bullet listing the exact `prefixes` tuple, forbidden characters, inline-backtick regex, fence toggle rule, suffix stripping, and `larch-logs/` skip copied from the scope anchor enumeration procedure, and require tests to assert the same constants.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: Existence probes are not required to be anchored to `--root` before containment checks (G-Md-1, G-CLI-2).. Scenario: The scope anchor uses `Path(probe).exists()` from the repo root. A naive `Path(probe).exists()` implementation follows the process cwd, so `pre-commit`, `make`, or manual runs from another directory can miss dead pointers or emit false positives.
- **Proposed resolution**: Require `(root / relative_probe).resolve()` containment under `root`, then existence on that resolved path; add a fixture test that runs `main(["--root", ...])` with a non-repo cwd.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: I-Gate-1: Same-line document-authored suppressions disarm this hard lint gate. Scenario: A contributor can add a dead pointer and a non-empty `lint-doc-pointer-paths: ok` comment on that line, making CI pass on solely gated-entity metadata and allowing the stale-pointer class to regrow.
- **Proposed resolution**: Do not let the inline comment alone suppress a finding. Require independently verified operator authorization recorded outside the gated document, or remove the suppression escape hatch and revise its planned acceptance test.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: SECURITY.md:102-366
- **Concern**: Acceptance testing treats prefix-only enumeration as full dead-pointer verification. Scenario: The lint and issue enumeration both keep only backtick tokens with an approved prefix and a slash. SECURITY.md still carries dead unprefixed names such as `session-setup.sh`, `design-route.sh`, `ship-pr-state.sh`, and `design-log-publish.sh` that lack any approved prefix. An implementer can satisfy acceptance criteria 1 and 2 while those stale security-control references remain, defeating Part 1 of the issue.
- **Proposed resolution**: Add an explicit verification step outside the prefix filter: review or mechanically check bare `*.sh` and other unprefixed machinery citations called out in the SECURITY.md sweep bullets, and require each to be repointed, rewritten, or documented with a PR deletion rationale.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: The lint module contract still does not pin the prefix tuple or forbidden-character set. Scenario: The NEW module section refers to an approved prefix and forbidden placeholder characters without listing the exact values from the issue enumeration procedure. The implementer can ship a scanner that diverges from the supplied enumeration snippet while tests still pass, breaking acceptance criterion 2 parity between manual enumeration and `python3 python/cli.py lint doc-pointer-paths`.
- **Proposed resolution**: Copy the issue prefix tuple and forbidden-character membership test verbatim into the module contract (or a single shared constant block referenced by both the lint and tests).
