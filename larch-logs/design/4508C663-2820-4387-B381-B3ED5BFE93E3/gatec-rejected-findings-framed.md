---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Pin lint/enumeration token rules
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan does not pin the exact prefixes, forbidden characters, token regex, and related scanning rules, risking divergence between the lint and the required enumeration procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one plan bullet listing the exact `prefixes` tuple, forbidden characters, inline-backtick regex, fence toggle rule, suffix stripping, and `larch-logs/` skip copied from the scope anchor enumeration procedure, and require tests to assert the same constants.
  - From Cursor-Innovation: Copy the issue prefix tuple and forbidden-character membership test verbatim into the module contract (or a single shared constant block referenced by both the lint and tests).


### [Plan Review] FINDING_2

### FINDING_2: Anchor existence probes to `--root`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Existence checks may use the process working directory instead of the supplied repository root, causing incorrect results when invoked outside the repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require `(root / relative_probe).resolve()` containment under `root`, then existence on that resolved path; add a fixture test that runs `main(["--root", ...])` with a non-repo cwd.


### [Plan Review] FINDING_3

### FINDING_3: Prevent document-authored suppression bypass
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Same-line suppression comments in gated documents can independently disable the hard lint and allow stale pointers to return without external authorization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not let the inline comment alone suppress a finding. Require independently verified operator authorization recorded outside the gated document, or remove the suppression escape hatch and revise its planned acceptance test.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: Makefile
- **Concern**: [SCOPE-REDUCTION] "Add it to the local lint battery" is ambiguous and can reintroduce the rejected duplicate-run shape (G-Enf-1).. Scenario: `make lint` already ends with `lint-only`, which runs every pre-commit hook. Adding `lint-doc-pointer-paths` to the top-level `lint:` target would run the same check twice, matching the round-1 rejected Makefile duplication concern.
- **Proposed resolution**: State explicitly that wiring mirrors `lint-markdown-heading-fence-state`: `py-lint-checks-fast`, focused Make target, tests, and pre-commit only; do not add a direct dependency on the top-level `lint:` target.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_doc_pointer_paths.py
- **Concern**: [SCOPE-REDUCTION] Rejecting symlinked required documents exceeds the fixed two-document pointer-lint contract. Scenario: A normal checkout has regular Tier-1 documents; this adds hostile-filesystem policy and fixture complexity without affecting pointer detection or any acceptance criterion
- **Proposed resolution**: Keep ordinary missing/read/UTF-8 failures as tool errors, but remove the explicit symlink rejection and its dedicated test coverage

---LARCH-REJECTED-END---
