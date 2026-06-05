### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-contract-ledger
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: Plan drops timing-ledger workflow-path subcommand but omits this harness from Files to modify and Testing strategy. Scenario: After removing cmd_workflow_path, make test-timing-ledger (test-harnesses-16) fails on the workflow-path invocation and v1/workflow row grep
- **Proposed resolution**: Add UPDATED scripts/test-timing-ledger.sh: remove workflow-path call and workflow-row assertions; adjust ledger fixture if needed; sync scripts/test-timing-ledger.md; list the target in Testing strategy

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:83-92
- **Concern**: Implement timing reports can still inherit a stale design workflow fallback. Scenario: The plan removes implement workflow rows but leaves resolve_workflow_fallback effectively usable by default implement runs; if DESIGN_TMPDIR remains exported from a prior design run, timing-report.sh can emit SIMPLE/HARD instead of omitting markdown and writing JSON workflow_path unknown
- **Proposed resolution**: Gate workflow fallback on LARCH_TIMING_SKILL=design before resolving/printing, and add a timing-report test with LARCH_TIMING_SKILL=implement plus DESIGN_TMPDIR/run-params.json asserting no markdown Workflow path line and JSON workflow_path unknown

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:22-31
- **Concern**: timing-ledger workflow-path harness pin is not in the plan. Scenario: The plan removes the workflow-path subcommand from scripts/timing-ledger.sh but does not update test-timing-ledger.sh; make test-timing-ledger will still call workflow-path HARD and then grep for a workflow row that no longer exists
- **Proposed resolution**: Drop the workflow-path call and workflow-row grep from test-timing-ledger.sh, and update scripts/test-timing-ledger.md if it still claims workflow row coverage

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: `test-timing-ledger.sh` not in plan file/harness list. Scenario: Removing `workflow-path` from `timing-ledger.sh` breaks `make test-timing-ledger` while the harness still calls `workflow-path HARD` and greps for a `workflow` row
- **Proposed resolution**: Add `### UPDATED: scripts/test-timing-ledger.sh` (drop the `workflow-path` call and `workflow` row assertion; keep mark/vendor/round coverage) and include `test-timing-ledger` in **Testing strategy** / acceptance grep

### FINDING_5:
- **Reviewer(s)**: Codex-Edge, Codex-dyn-migration-orphans
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-ledger.sh:21-28
- **Concern**: Plan removes timing-ledger workflow-path but omits the timing-ledger harness that still invokes it and asserts a workflow row. Scenario: make lint runs test-timing-ledger; after the subcommand is removed no workflow row is written, so the grep pin fails
- **Proposed resolution**: Include scripts/test-timing-ledger.sh in the change; remove the workflow-path invocation and v1 workflow assertion, and update its sibling md if needed

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:23-27
- **Concern**: Plan removes timing-ledger.sh workflow-path but leaves the timing-ledger harness pinned to that subcommand. Scenario: make test-timing-ledger or make lint fails after the subcommand is removed
- **Proposed resolution**: Add scripts/test-timing-ledger.sh to the plan; remove the workflow-path invocation and v1 workflow assertion, or replace with a minimal negative check for the removed subcommand if desired

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: Plan drops timing-ledger workflow-path but omits this harness and test-timing-ledger.md. Scenario: make test-harnesses-16 / test-timing-ledger fails on removed subcommand and v1 workflow row grep
- **Proposed resolution**: Add UPDATED entries for scripts/test-timing-ledger.sh (drop workflow-path call and workflow-row assertion) and scripts/test-timing-ledger.md; list test-timing-ledger in Testing strategy

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: Plan removes timing-ledger workflow-path but omits the timing-ledger harness. Scenario: After the subcommand is removed, make lint still runs test-timing-ledger.sh; the workflow-path call writes no workflow row and the v1 workflow grep fails
- **Proposed resolution**: Add scripts/test-timing-ledger.sh and scripts/test-timing-ledger.md to the plan; remove the workflow-path invocation and workflow-row expectation

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_report_tokens_render.py:60-63, python/fixtures/report_tokens_implement_golden.md:6-29
- **Concern**: Implement report golden fixture is not listed for update. Scenario: The renderer will drop implement workflow tables/columns, but the golden test still reads a fixture containing workflow output, so py-test fails unless the test is rewritten
- **Proposed resolution**: Add python/fixtures/report_tokens_implement_golden.md to the plan, or explicitly rewrite the golden test so it no longer reads the stale fixture

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step2-dispatch.md:30-34
- **Concern**: Step2 test contract doc still describes the removed --workflow flag. Scenario: The plan acceptance grep says no --workflow references remain under skills/implement, but this omitted md file would keep those references and stale behavior notes
- **Proposed resolution**: Update test-step2-dispatch.md alongside test-step2-dispatch.sh to describe unknown-flag handling and fixed 7200s timeout

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: Plan drops `timing-ledger.sh workflow-path` but omits the `make lint` harness that still invokes it. Scenario: The subcommand removal breaks `test-timing-ledger.sh` (wired via `scripts/timing-ledger.md` / `test-harnesses-4`); `make lint` fails even when production callers are updated
- **Proposed resolution**: Add `### UPDATED: scripts/test-timing-ledger.sh` (and sibling `scripts/test-timing-ledger.md` if prose still claims workflow-row coverage): remove the `workflow-path HARD` invocation and `v1\tworkflow\t` assertion; list `test-timing-ledger.sh` in Testing strategy

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-ledger.sh:22-30; Makefile:296-297
- **Concern**: Plan removes timing-ledger.sh workflow-path but does not update the wired timing-ledger harness. Scenario: The Makefile target still runs scripts/test-timing-ledger.sh; after the subcommand is removed, line 23 fails and line 30 still expects a workflow row, so make lint fails
- **Proposed resolution**: Include scripts/test-timing-ledger.sh in the plan: remove the workflow-path call and workflow-row assertion or replace them with a negative assertion for the removed subcommand; add it to the testing strategy

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-migration-orphans
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_report_tokens_render.py:60-63; python/fixtures/report_tokens_implement_golden.md:6-29
- **Concern**: Plan changes implement report-tokens table shapes but omits the golden fixture file used by the test. Scenario: The golden test reads fixtures/report_tokens_implement_golden.md, which still contains Aggregate cost by workflow and workflow columns; py-test will fail or the old workflow dimension will remain in the golden output
- **Proposed resolution**: Add python/fixtures/report_tokens_implement_golden.md to the updated files and revise it to the no-workflow implement rendering while leaving the design golden fixture unchanged

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-contract-ledger
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-ledger.sh:22-31; scripts/test-timing-ledger.md:1-3
- **Concern**: Plan removes timing-ledger workflow-path subcommand but does not update the timing-ledger harness that still produces and asserts workflow rows. Scenario: make test-timing-ledger remains wired into lint and will fail after cmd_workflow_path and workflow dispatch are deleted
- **Proposed resolution**: Update test-timing-ledger.sh to stop invoking workflow-path and stop asserting v1 workflow rows; update the sibling md coverage sentence accordingly

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-schema-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_report_tokens_render.py:40-63
- **Concern**: Plan omits golden fixture update for implement render output. Scenario: `test_render_implement_golden_markdown` byte-compares rendered markdown to `python/fixtures/report_tokens_implement_golden.md`; after `report_tokens_render.py` changes aggregate heading, All runs row, and workflow-stripped tables, pytest fails even if tests are touched
- **Proposed resolution**: Add `### UPDATED: python/fixtures/report_tokens_implement_golden.md` to the plan (new `## Aggregate cost` + `All runs` row, top-runs header without Workflow column) and list it in Testing strategy

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-schema-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:42-55,98-106,246-254
- **Concern**: Unconditional run-params fallback can reintroduce implement workflow values despite the plan promise. Scenario: After removing workflow rows, render_report still calls resolve_workflow_fallback unconditionally; if DESIGN_TMPDIR remains exported or run-params.json sits beside an implement ledger, workflow becomes SIMPLE/HARD, so markdown prints **Workflow path** and JSON emits SIMPLE/HARD instead of unknown.
- **Proposed resolution**: Gate the fallback to design-only timing reports, and add an implement test with DESIGN_TMPDIR/run-params.json asserting no markdown workflow line and JSON workflow_path == "unknown".

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-migration-orphans
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-ledger.sh:23-30
- **Concern**: Harness still exercises removed workflow-path subcommand. Scenario: Deleting cmd_workflow_path leaves test-timing-ledger.sh calling a dead subcommand and grepping workflow rows; make test-timing-ledger fails
- **Proposed resolution**: Add ### UPDATED: scripts/test-timing-ledger.sh — drop the workflow-path invocation and workflow-row grep (or replace with a mark-only ledger smoke test); include it in Testing strategy
