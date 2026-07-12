### [Plan Review] FINDING_1

### FINDING_1: Retired design harness references omitted from update list
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Design wrapper documentation still references the retired structure harness and could fail retired-script lint after deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/design-step5b-prepare.md` and `### UPDATED: skills/design/scripts/design-step5c.md` retargeting coverage to `make test-design-structure` or the shared pytest selection


### [Plan Review] FINDING_2

### FINDING_2: Design context-window parity is unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Generic containment or ordering pins would not preserve the legacy bounded line-window checks around design anchors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `test_skill_structure.py`, add named tests (or a `context-before` pin with line bounds and the Step 3 launch anchor rule) that preserve each legacy label and window size
  - From Cursor-Innovation: Name a design context-window specialized named-test module in the NEW/UPDATED `test_skill_structure.py` contract, port every `check_context*` assertion with the same anchors and line bounds, and map each legacy fail label in the inventory.
  - From Cursor-Pragmatic: Port each context_before/context_before_step3_launch assertion as a named specialized test or a line-window-before-anchor pin, and map every legacy label in the inventory.


### [Plan Review] FINDING_3

### FINDING_3: Implement byte-proximity parity is unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Migrating implement checks as generic containment, ordering, or same-line pins could allow required contracts to drift beyond the legacy byte windows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skill_structure_pins.py` add a `near` pin (anchor, needle, byte_limit) or list every `require_near` legacy label under implement specialized named tests; require each in the legacy-label inventory and focused `make test-implement-structure` selection
  - From Cursor-Innovation: Add an explicit implement proximity named-test family (or a near pin with anchor, token, max_bytes, and legacy labels) to `skill_structure_pins.py`/`test_skill_structure.py`, include every legacy label in the inventory, and keep it inside each focused Make selection.
  - From Cursor-Pragmatic: Add a same-file near predicate (anchor, token, max_bytes) with observed-distance diagnostics, migrate every legacy require_near label into implement pins or an explicit named-test table, and keep the legacy-label inventory one-to-one.


### [Plan Review] FINDING_4

### FINDING_4: Research/review header and ordering bounds are unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Whole-file header pins and unconstrained ordering checks would not preserve first-20-line header placement or research line-order contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add research/review named tests (or a `prefix-lines` pin with line count and anchored vs substring mode) covering every legacy header assertion
  - From Cursor-Innovation: Add explicit research/review specialized named tests for first-20 header triplets and `line_for` line-order chains; register their legacy labels and include them in focused Make selections.
  - From Cursor-Pragmatic: Add a research named test (or first-N-lines pin) that preserves the `head -n 20` anchored-regex semantics and inventory mapping.
  - From Cursor-Requirements: Add a research named test (or bounded-line pin) that preserves the head -n 20 anchored-header semantics and map its legacy label in the inventory.


### [Plan Review] FINDING_5

### FINDING_5: Implement wrapper executable-bit checks are omitted
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The migration names executable-absence checks but not the positive `X_OK` checks for required implement wrappers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an implement specialized named test mirroring the wrapper list and `os.access(..., os.X_OK)` assertions, and map legacy labels in the inventory
  - From Cursor-Innovation: Add a named `test_implement_wrapper_executable_bits` (or equivalent) covering the same wrapper set and legacy labels; keep it in the implement focused selection.
  - From Cursor-Pragmatic: Add an implement named test that preserves the positive X_OK wrapper list and legacy labels.
  - From Cursor-Requirements: Explicitly port `test_implement_wrapper_siblings_executable` (or equivalent) as a named implement specialized test covering the same wrapper list and X_OK semantics, and register it in the implement focused selection inventory.


### [Plan Review] FINDING_6

### FINDING_6: Implement step-5-review documentation is omitted from updates
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: `skills/implement/scripts/step-5-review.md` still references the retired implement structure harness and may fail retired-script lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/step-5-review.md to retarget maintenance prose to make test-implement-structure or the shared pytest suite.


### [Plan Review] FINDING_7

### FINDING_7: Design documentation cites a nonexistent helper
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Design guidance names `assert_wrapper_pause_before_work`, which is not defined by the current harness and would remain invalid if only the path is retargeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When editing skills/design/SKILL.md, replace the bogus helper with the actual pytest selection or named specialized test that enforces wrapper pause-before-work ordering.
  - From Cursor-Requirements: When updating skills/design/SKILL.md, replace the harness citation with the focused Make target or pytest selection and drop the assert_wrapper_pause_before_work name; point pause ordering at the migrated wrapper pause-before-work named coverage instead.


### [Plan Review] FINDING_8

### FINDING_8: Quick-mode documentation references the retired implement harness
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `scripts/test-quick-mode-docs-sync.md` still documents `test-implement-structure` as an aggregate or prerequisite, causing stale-reference lint failures after retirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add this file as `### UPDATED:` and state that the pytest-focused target runs separately and through `make py-test`
  - From Cursor-Requirements: Add ### UPDATED: scripts/test-quick-mode-docs-sync.md to replace the retired path with make test-implement-structure or python/tests/skills/test_skill_structure.py in the harness prerequisite example.


### [Plan Review] FINDING_9

### FINDING_9: Render-cost allowlist retains a retired harness path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The render-cost allowlist still includes `scripts/test-design-structure.sh`, which retired-script lint will reject after migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: scripts/test-render-cost-line-callsites.sh to drop scripts/test-design-structure.sh from allowed_re (do not broaden the allowlist)


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/skills/skill_structure_pins.py:1
- **Concern**: [SCOPE-REDUCTION] `bounded cross-file` predicate has no legacy consumer. Scenario: None of the seven Bash structure harnesses implement a bounded cross-file assertion; shipping an unused predicate adds evaluator and self-test surface without parity benefit
- **Proposed resolution**: Drop `bounded cross-file` from Approach item 3, pin kinds, and self-tests unless a concrete legacy label is identified first


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan over-requires seven focused-target documentation rows. Scenario: Only make test-alias-structure has a dedicated docs/linting.md table row today (line 404); the other six structure targets are Makefile-only. Requiring seven new rows expands doc churn without changing lint behavior once shard lists move to pytest.
- **Proposed resolution**: Revise the single existing alias row plus shard-coverage prose to describe the shared pytest suite and per-skill -k selections; do not invent six redundant table entries.


### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan overstates seven linting.md target rows when only alias is documented. Scenario: docs/linting.md currently documents only make test-alias-structure; the other six focused structure targets have no table rows. Requiring seven row updates invites six redundant doc additions without improving migration verification.
- **Proposed resolution**: Revise the docs/linting.md task to update the existing alias row plus shard-coverage prose, and only add new rows if a target already has a dedicated entry today.


