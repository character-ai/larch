### [Plan Review] FINDING_3

### FINDING_3: Sparse `_write_minimal_state` fixtures conflict with canonical implement baseline
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Refactoring `_write_minimal_state` through `write_session_env` conflicts with the intentional two-key sparse contract (`REPO` + `MODE=N/A`). The helper’s default-merging implement baseline would inject `REPO_ROOT`, `LARCH_CLAUDE_PLUGIN_ROOT`, tool flags, and other keys the minimal fixture deliberately omits; `MODE` is also outside the implement baseline and may be rejected under a narrow allowlist reading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Keep _write_minimal_state as a raw two-line session-env write, or add an explicit carve-out: omit every implement baseline key and allow only non-writer test keys such as MODE via a documented sparse-fixture path. Do not route _write_minimal_state through the canonical default baseline.
  - From Cursor-Requirements: Require _write_minimal_state (and similar sparse fixtures) to pass omit= for every implement baseline key or keep them as raw session-env writes exempt from the shared writer refactor


### [Plan Review] FINDING_4

### FINDING_4: Default `seed_plan` / `seed_feature_description` bytes are unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Dispatch `_session` seeds `plan.txt` as `## Plan\n` and `feature-description.txt` as `feature\n`, but the helper spec does not pin those defaults. Mechanical migration can silently diverge from the 148-call dispatch contract (and from bootstrap sites that still use other bytes such as `plan\n`) before foundation tests catch drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin defaults in `session.py` to `## Plan\n` and `feature\n`, add optional `content=` to both seed helpers, and assert the literals in `test_foundation.py`
  - From Cursor-Innovation: Pin defaults to the current _session bytes: plan.txt is "## Plan\n" and feature-description.txt is "feature\n"; assert them in test_foundation.py.
  - From Cursor-Pragmatic: Pin defaults to ## Plan\n and feature\n for make_implement_tmpdir to match dispatch _session, and state that bootstrap sites with other bytes must call seed_plan or seed_feature_description with explicit content after tmpdir creation.


### [Plan Review] FINDING_5

### FINDING_5: `write_design_source_env` production wire shape is underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: “Production-style” emission for design session env is ambiguous relative to `write_design_env_main` and lighter test writers. Missing rules for `shlex.quote` on spaced paths, shebang, generator comment, and stable export ordering can let helper tests pass while diverging from the production wire shape that design-consumer tests must match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make `write_design_source_env` use the same `export` + `shlex.quote` emission as `session_env._export_line`, and cover a spaced `REPO_ROOT` in `test_foundation.py`
  - From Cursor-Innovation: Require the same wire shape as write_design_env_main: shebang, generator comment line, and export KEY=shlex.quote(value) rows in stable key order.


### [Plan Review] FINDING_6

### FINDING_6: `make_design_tmpdir` does not pin a default `SESSION_ID`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The design baseline requires `SESSION_ID`, yet `make_design_tmpdir` provides no deterministic default. Migrated design-consumer tests can get inconsistent `SESSION_ID` values and flaky assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin one deterministic default (for example "test-session-1") and allow overrides; assert it in test_foundation.py.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_final_report.py
- **Concern**: [SCOPE-REDUCTION] Keep _write_minimal_state as a raw sparse fixture instead of migrating it through write_session_env. Scenario: The plan both says to refactor _write_minimal_state via the shared writer and to retain deliberately incomplete session files. The helper baseline adds REPO_ROOT, plugin-root, and tool keys that minimal final-report tests currently omit; that can change report inputs beyond REPO=o/r.
- **Proposed resolution**: Exclude _write_minimal_state from shared-writer migration; keep its two-line raw session-env.sh. Use write_session_env only for ordinary plan-coverage setups that need the canonical baseline.


