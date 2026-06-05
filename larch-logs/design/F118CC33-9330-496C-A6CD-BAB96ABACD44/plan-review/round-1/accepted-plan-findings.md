### FINDING_1: Timing-ledger harness still pins removed workflow-path behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-contract-ledger, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-dyn-migration-orphans, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-contract-ledger, Cursor-dyn-migration-orphans
- **Severity**: important
- **Concern**: The plan removes `scripts/timing-ledger.sh workflow-path` but omits the wired timing-ledger harness and sibling documentation that still invoke the subcommand and assert workflow rows, so `make test-timing-ledger`, `make test-harnesses-*`, or `make lint` will fail after the subcommand is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation, Cursor-dyn-contract-ledger: Add UPDATED scripts/test-timing-ledger.sh: remove workflow-path call and workflow-row assertions; adjust ledger fixture if needed; sync scripts/test-timing-ledger.md; list the target in Testing strategy
  - From Codex-Arch: Drop the workflow-path call and workflow-row grep from test-timing-ledger.sh, and update scripts/test-timing-ledger.md if it still claims workflow row coverage
  - From Cursor-Edge: Add `### UPDATED: scripts/test-timing-ledger.sh` (drop the `workflow-path` call and `workflow` row assertion; keep mark/vendor/round coverage) and include `test-timing-ledger` in **Testing strategy** / acceptance grep
  - From Codex-Edge, Codex-dyn-migration-orphans: Include scripts/test-timing-ledger.sh in the change; remove the workflow-path invocation and v1 workflow assertion, and update its sibling md if needed
  - From Codex-Innovation: Add scripts/test-timing-ledger.sh to the plan; remove the workflow-path invocation and v1 workflow assertion, or replace with a minimal negative check for the removed subcommand if desired
  - From Cursor-Pragmatic: Add UPDATED entries for scripts/test-timing-ledger.sh (drop workflow-path call and workflow-row assertion) and scripts/test-timing-ledger.md; list test-timing-ledger in Testing strategy
  - From Codex-Pragmatic: Add scripts/test-timing-ledger.sh and scripts/test-timing-ledger.md to the plan; remove the workflow-path invocation and workflow-row expectation
  - From Cursor-Requirements: Add `### UPDATED: scripts/test-timing-ledger.sh` (and sibling `scripts/test-timing-ledger.md` if prose still claims workflow-row coverage): remove the `workflow-path HARD` invocation and `v1\tworkflow\t` assertion; list `test-timing-ledger.sh` in Testing strategy
  - From Codex-Requirements: Include scripts/test-timing-ledger.sh in the plan: remove the workflow-path call and workflow-row assertion or replace them with a negative assertion for the removed subcommand; add it to the testing strategy
  - From Codex-dyn-contract-ledger: Update test-timing-ledger.sh to stop invoking workflow-path and stop asserting v1 workflow rows; update the sibling md coverage sentence accordingly
  - From Cursor-dyn-migration-orphans: Add ### UPDATED: scripts/test-timing-ledger.sh — drop the workflow-path invocation and workflow-row grep (or replace with a mark-only ledger smoke test); include it in Testing strategy


### FINDING_2: Implement timing reports can still inherit design workflow fallback
- **Reviewer(s)**: Codex-Arch, Codex-dyn-schema-compat
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` still resolves workflow fallback unconditionally, so an implement timing report can emit stale design workflow values from `DESIGN_TMPDIR` or nearby `run-params.json` despite the plan’s promise to remove implement workflow output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Gate workflow fallback on LARCH_TIMING_SKILL=design before resolving/printing, and add a timing-report test with LARCH_TIMING_SKILL=implement plus DESIGN_TMPDIR/run-params.json asserting no markdown Workflow path line and JSON workflow_path unknown
  - From Codex-dyn-schema-compat: Gate the fallback to design-only timing reports, and add an implement test with DESIGN_TMPDIR/run-params.json asserting no markdown workflow line and JSON workflow_path == "unknown".


### FINDING_3: Implement report golden fixture omitted from plan
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-migration-orphans, Cursor-dyn-schema-compat
- **Severity**: important
- **Concern**: The plan changes implement report-token rendering table shapes but omits the golden markdown fixture that the tests byte-compare against, so `py-test` can fail or stale workflow output can remain encoded in the expected output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add python/fixtures/report_tokens_implement_golden.md to the plan, or explicitly rewrite the golden test so it no longer reads the stale fixture
  - From Codex-Requirements, Codex-dyn-migration-orphans: Add python/fixtures/report_tokens_implement_golden.md to the updated files and revise it to the no-workflow implement rendering while leaving the design golden fixture unchanged
  - From Cursor-dyn-schema-compat: Add `### UPDATED: python/fixtures/report_tokens_implement_golden.md` to the plan (new `## Aggregate cost` + `All runs` row, top-runs header without Workflow column) and list it in Testing strategy


### FINDING_4: Step2 dispatch contract doc still describes removed --workflow flag
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-step2-dispatch.md` still documents the removed `--workflow` flag, conflicting with the plan’s acceptance grep and leaving stale behavior notes under `skills/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update test-step2-dispatch.md alongside test-step2-dispatch.sh to describe unknown-flag handling and fixed 7200s timeout

