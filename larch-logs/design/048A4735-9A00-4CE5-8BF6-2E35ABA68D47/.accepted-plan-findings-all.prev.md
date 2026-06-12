### FINDING_1: Mermaid lint harness lacks mmdc availability guard
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds `assert_mermaid_valid` / `python3 python/cli.py lint mermaid-fences` to `scripts/test-render-review-phase-detail.sh`, but the harness does not ensure `mmdc` (or equivalent mermaid-lint tooling) is available before calling the linter. `test-harnesses-12` runs this harness with only pip harness deps (`.github/workflows/ci.yaml`); the separate `lint-mermaid` job installs npm/puppeteer tooling. `python/lint_mermaid_fences.py` exits 2 when `mmdc` is missing and auto-`npm ci` fails or is unavailable, so a hard assert can fail `make test-harnesses-12` and local `make test-render-review-phase-detail` on hosts without `mmdc`, even when existing substring Gantt grep assertions pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate assert_mermaid_valid on mmdc resolution (same pattern as the harness jq SKIP at line 10): skip with a visible SKIP line when mmdc is absent; run lint mermaid-fences only when the CLI can succeed. Document that full parse validation requires mmdc locally.
  - From Cursor-Innovation: Wrap assert_mermaid_valid in a guard that skips with an explicit SKIP breadcrumb when mmdc is unavailable (mirror the jq fromdateiso8601 gate around Test 10), or probe python/cli.py lint mermaid-fences exit 2 and skip; only hard-fail when mmdc is present and lint returns a parse error.
  - From Cursor-Pragmatic: Before `assert_mermaid_valid`, mirror `Makefile` `lint-mermaid`: `if [ ! -f mermaid-lint/node_modules/.package-lock.json ]; then (cd mermaid-lint && npm ci); fi`, then run lint; on non-zero exit print `FAIL:` and exit 1. Document the dependency in the harness `.md` if needed.


### FINDING_2: Skill filter on rrange may change Gantt window behavior
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan treats the filtered `rrange` as table/cost-only, but the same `rstart`/`rend` values are written to `round_windows_file` and drive Gantt chart generation. Applying `$4==SKILL` to that shared window would change Gantt overlap behavior for same-number round rows from other skills, violating the stated non-goal to avoid Gantt behavior changes. A design-round row that currently widens the Gantt overlap window would stop contributing to reviewer timing once `rrange` filters on skill.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the new skill filter on the table/cost window only. Preserve the existing unfiltered round window for round_windows_file, or explicitly split table_windows and gantt_windows


### FINDING_3: Skill-contamination regression fixture omits round-meta.json
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned skill-contamination regression fixture omits `round-meta.json` and a minimal completed rounds-root layout. The renderer emits per-round table rows only for `round-N` dirs that contain `round-meta.json` (`scripts/render-review-phase-detail.sh:80-84`). A fixture with only timing-ledger round rows would hit the no-completed-rounds path, so the Time-column assertion would not exercise the `rrange` skill filter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add round-1/round-meta.json (minimal valid tally/panel JSON) under the contamination rounds root, keep the implement/design timing rows, run with --skill implement --no-gantt, and assert round 1 Time reflects the implement window only (not the wider design window)


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/render-review-phase-detail.sh:242-258
- **Concern**: [SCOPE-REDUCTION] Planned skill filter on shared rrange also changes Gantt round windows. Scenario: The rrange result feeds round_windows_file at lines 255-258, so adding $4==SKILL there fixes table Time and Cost but also filters the Gantt window even though the scope says not to alter Gantt behavior
- **Proposed resolution**: Split the window calculation: use skill-filtered start/end only for table Time and round_vendor_cost, and keep the existing unfiltered round-window scan for round_windows_file/Gantt


### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh:242-258
- **Concern**: [SCOPE-REDUCTION] The proposed skill filter is attached to the shared rrange path that also feeds Gantt round windows. Scenario: Adding $4==SKILL there changes reviewer timing charts because line 257 writes the filtered range to round_windows_file, even though the plan says not to change Gantt behavior
- **Proposed resolution**: Use the skill-filtered range only for table Time and Cost, and keep a separate unfiltered round-window source for the existing Gantt path


### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh:240-258
- **Concern**: [SCOPE-REDUCTION] Planned skill filtering changes the shared round window that also feeds Gantt. Scenario: The scope says not to change Gantt behavior, but filtering rrange by skill also changes round_windows_file, so Gantt overlap/clamping changes for same-number cross-skill round rows
- **Proposed resolution**: Split table/cost windows from Gantt windows. Use the skill-filtered window for Time and Cost only, and keep the existing unfiltered round window for Gantt overlap behavior.




### FINDING_2: Plan omits #4062 merge prerequisite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The scope anchor blocks items 1, 2, and 4 on #4062 Gantt harness and renderer work, but `plan.txt` never states that gate. Implementing before #4062 lands can target missing Test 5b/Gantt call sites or conflict with in-flight renderer changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an Approach or Edge cases note: merge #4062 first; items 3 and 5 are independent; items 1, 2, and 4 assume post-#4062 Gantt tests and renderer behavior.


### FINDING_3: Contamination test does not assert cost column
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The skill-window contamination test does not exercise the cost column. The issue is specifically about cross-skill round windows inflating vendor cost, but the planned contamination fixture only asserts Time; an implementation could still pass tests while using the unfiltered Gantt window for `round_vendor_cost`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a token-ledger record inside only the wider other-skill window and assert the implement round Cost and Total stay $0.00 or otherwise exclude that record


### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/lint_mermaid_fences.py:181-203; .github/workflows/ci.yaml:245-300
- **Concern**: [SCOPE-REDUCTION] Mermaid availability probe can trigger npm ci inside the test harness. Scenario: The planned helper treats python cli exit 2 as unavailable, but the lint command first runs npm ci when mmdc is absent; CI test-harnesses do not install/cache Mermaid, so shard 12 can gain a hidden Node/Chromium install or local runs can dirty mermaid-lint/node_modules
- **Proposed resolution**: Precheck for an existing local/PATH mmdc before invoking the Python lint command and emit the SKIP breadcrumb when absent, or add explicit cached Mermaid setup to the harness CI path instead of relying on linter auto-install




### FINDING_2: Generated Mermaid validation must not be opportunistically skipped in CI
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan allows Mermaid validation to skip whenever no existing Mermaid CLI is present. CI test-harness shards do not install the Mermaid toolchain, so invalid generated Gantt output can still pass with only a SKIP breadcrumb instead of failing validation. That undermines the stated goal of validating generated Mermaid fences in the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep the local no-auto-install guard if desired, but make generated Mermaid validation mandatory in CI or otherwise guarantee the toolchain is present before this harness path runs.



