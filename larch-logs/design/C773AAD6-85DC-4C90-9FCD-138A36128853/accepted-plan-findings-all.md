### FINDING_2: Legacy status needs a seeded-module allowlist
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Manifest Gate Integrity, Codex-dyn-Manifest Gate Integrity
- **Severity**: major
- **Concern**: A newly added lint module could claim `legacy` with `source_issue: 0`, bypassing justification and commissioning requirements.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Innovation: Add a frozen legacy allowlist of seeded module basenames (or equivalent rule) in lint_module_manifest.py; emit a finding when host_decision is legacy for any module outside that set; add a matching pytest case in python/tests/lint/test_lint_module_manifest.py
  - From Cursor-Pragmatic: Add an explicit rule: only seed-baseline module basenames may use legacy (for example a frozen legacy_modules list in the manifest header, or equivalent); emit a finding when any other on-disk lint_*.py has legacy or when a new manifest row uses legacy for a non-seed basename
  - From Codex-Pragmatic: Add a fixed seeded-legacy allowlist, reject legacy for other modules, and test a new module disguised as legacy
  - From Codex-Requirements: Bind legacy to an immutable seeded allowlist and test that a newly added module marked legacy fails.
  - From Cursor-dyn-Manifest Gate Integrity: Add a frozen LEGACY_SEED_MODULES (or equivalent) listing only pre-commission basenames; reject host_decision legacy for any other module. Add an explicit test that a new on-disk module with a legacy row fails.
  - From Codex-dyn-Manifest Gate Integrity: Define an immutable seeded legacy set, reject legacy rows outside it, and add a regression test for a new module using legacy.


### FINDING_3: Proposal contracts need complete Host and Cheaper alternative semantics
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Merely requiring field names permits `Host: New module` or `Cheaper alternative: none` without the required explanations.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Add the conditional requirement to report and filing contracts, and pin it in the structure and completeness checks
  - From Codex-Innovation: Require that exception sentence in report and Lint, Hook-contract, and Regression test contracts, and pin it in the structure harness
  - From Codex-Pragmatic: Add the exact Host and Cheaper alternative semantics, and make completeness reject blank or incomplete values
  - From Codex-Requirements: Require Host to name an existing host or name the closest host and explain why it cannot absorb the rule. Require Cheaper alternative to name the nearest cheaper mechanism and explain why it is insufficient.


### FINDING_4: Oversized proposals need explicit gates and filing splits
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The structure harness does not pin default-mode Step 5 approval for proposals over 400 lines or filing-mode split-before-filing behavior.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Extend the structure harness to pin explicit SKILL prose for Step 5 oversized-proposal approval and for filing-mode split-before-filing when Size budget exceeds 400
  - From Cursor-Innovation: Pin the Step 5 oversize approval gate prose in _structure_learn_from_bugs_specialized.py alongside the existing completeness and threshold pins


### FINDING_6: Boolean `source_issue` values must be rejected
- **Reviewer(s)**: Cursor-dyn-Manifest Gate Integrity
- **Severity**: major
- **Concern**: Python treats JSON booleans as integers, so `source_issue: true` could satisfy a positive-integer check.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-dyn-Manifest Gate Integrity: Validate with isinstance(v, int) and not isinstance(v, bool), matching python/larch/lint/lint_lifecycle_prefix_literal.py:528 and siblings. Add a test with source_issue true.


