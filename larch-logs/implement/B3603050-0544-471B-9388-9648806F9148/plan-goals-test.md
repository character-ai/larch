## Goal
Implement issue #5174: [IMPLEMENTING] [py-code-quality] Packaging 8/9: move reporting/tokens and issue tooling into larch.report and larch.issue.

## Implementation Plan
**Problem.** Token/cost reporting, run-log, and issue-management modules are flat with no package boundary. `run_logs` has 10 importers, `issue_wire` 8; the `report_tokens_*` family is a coherent pipeline.

**Proposed change.** Move two coherent groups into packages. `larch.report`: `tokens`, `report_tokens_models`/`scan`/`cost`/`render`/`plot`/`issue`/`cli`, `run_logs`, `timing`, `progress_report`, `final_report`. `larch.issue`: `issue_wire`, `issue_create`, `issue_query`, `tracking_issue`, `deps_audit`, `combine_issues`, `file_oos`, `oos`, `analyze_issues`, `audit_runs`, `execution_issues`. Rewrite all importers and update the corresponding `cli.py` `_REGISTRY` entries. Exact split between `larch.report` and `larch.issue` (and whether to keep them separate) is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (token ledger grammar, tracking-issue comment contracts, run-log batch format). Pure move plus import rewrites.

**Acceptance.** Reporting and issue modules live under their packages; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations (`python/cli.py report-tokens analyze`) unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
