### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/**
- **Concern**: (G-Py-11) Plan omits a firm deliverable to pragma-annotate existing test gh list literals. Scenario: The issue requires a no-baseline hard ban plus reason-bearing fixture suppression, and the plan states test files stay in scope with no implicit exemptions. The repo already has on the order of 175 raw `["gh", ...]` list literals across 23 files under `python/tests/` (assertions and mock-call comparisons). The firm `### NEW:` / `### UPDATED:` set wires the lint and isolated unit tests but names no migration of that existing corpus. After production repoint, `python3 python/cli.py lint gh-argv-literal` and `py-lint-checks-fast` still fail until every intentional test literal gets a same-line `# lint-gh-argv-literal: ok <reason>` pragma.
- **Proposed resolution**: Add an explicit landing step or `### MAY_UPDATE:` batch for `python/tests/**` (and any other in-scope non-git modules) to apply reason-bearing same-line pragmas to every intentional existing `["gh", ...]` list literal before merge; keep the testing-strategy zero-finding check as verification, not the only mention of this work.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [I-Gate-1] The planned pragma suppresses production literals and the planned tests require that bypass to work. Scenario: A new production `["gh", ...] # lint-gh-argv-literal: ok reason` disarms the hard ban using data authored with the violating code, so adoption can decay despite CI passing
- **Proposed resolution**: Permit pragma suppression only for explicit test-fixture paths or a reason-bearing fixture allowlist; reject production pragmas and replace the planned production-side suppression test with that rejection case

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/issue/test_issue_wire.py:123-648
- **Concern**: [G-Gate-1] The firm file set omits the existing in-scope fixture suppressions required before this baseline-free gate can pass. Scenario: The current tree has 236 matching AST list literals outside `python/larch/git/`, including many test assertions such as this file; production repoints do not remove expected wrapper argv assertions, so the new full-tree lint fails on landing
- **Proposed resolution**: Add the required `### UPDATED:` test files and same-line reason-bearing fixture pragmas for every retained test literal, then verify the final full-tree scan is clean

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/**
- **Concern**: Plan names no deliverable to clear existing test-tree raw list literals before the no-baseline gate lands. Scenario: The revised plan scans all of python/ outside python/larch/git/, keeps tests in scope, and requires a zero-finding clean scan, but its firm file set only adds the new linter module, wiring, docs, and an isolated tmp_path harness. The current tree already has well over 100 raw ["gh", ...] list literals across roughly 23 files under python/tests/ (mock argv comparisons and helpers such as cr(["gh"], ...)), while production sites outside python/larch/git/ are expected to be repointed separately. Landing this lint without a named same-PR pass to add reason-bearing pragmas or otherwise eliminate those literals leaves py-lint-checks-fast and the new pre-commit hook permanently red even after production repoint work completes.
- **Proposed resolution**: Add an explicit landing deliverable (### MAY_UPDATE: bulk pragma migration or a mechanical sweep step) that annotates or rewrites every existing python/tests/** literal the rule matches, and gate merge on python3 python/cli.py lint gh-argv-literal returning 0 after production repoint.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: File discovery omits the shared EXCLUDED_DIRS pruning used by every other python/ AST linter. Scenario: Operators commonly keep a virtualenv at python/.venv (repo docs reference it). rglob without skipping .venv, node_modules, .agents, or __pycache__ can report third-party ["gh", ...] literals or hit parse/read failures there, so a fully repointed larch tree still fails locally and diverges from subprocess-via-runner discovery parity
- **Proposed resolution**: In lint_gh_argv_literal.py discovery, skip paths whose relative parts intersect the shared EXCLUDED_DIRS set from sibling lints (.git, node_modules, .venv, .agents, __pycache__ at minimum); keep tests/ and test_*.py in scope; document the vendored-dir skip in docs/linting.md; add one isolated-tree test that a python/.venv/*.py literal is not scanned

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_clarify.py:154
- **Concern**: The planned hard gate lacks migration of existing fixture literals. Scenario: The proposed scan currently finds 236 matching lists across 41 non-exempt files, including this test fixture; the plan names no updates for those fixtures, so the clean scan and CI gate remain red.
- **Proposed resolution**: Add firm updates for every intentional existing fixture literal with the required same-line pragma, or a plan-permitted explicit fixture allowlist.
