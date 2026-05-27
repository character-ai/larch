## Decision 1: Item D scope (defer or include)
- **Question**: Item D (folding the second `create-branch.sh --check` into `phase_infra`) is explicitly conditional on a future Phase 4 (coder waterfall) Step 0 collapse. Should this design include it now?
- **Resolution**: Defer. Drop Item D from this design's scope. Address only Items A, B, C, E, F.
- **Source**: user

## Decision 2: Item B direction (add marks vs. document folded-into-preflight)
- **Question**: Item B offers two alternatives: emit `token-ledger.sh mark` + `timing-ledger.sh mark "Step 0 — tracking issue"` at the top of `phase_tracking`, OR document the tracking-bucket-folded-into-preflight intent in `scripts/implement-bootstrap.md` and `skills/implement/SKILL.md`.
- **Resolution**: Add the marks. Emit both `token-ledger.sh mark` and `timing-ledger.sh mark "Step 0 — tracking issue"` at the top of `phase_tracking` (mirroring the `phase_infra` pattern at lines 450-451). This eliminates latent regression risk if a future cutover moves the orchestrator-side mark off SKILL.md.
- **Source**: user

## Decision 3: Item F failure mode (loud error vs. silent zero vs. annotated warning)
- **Question**: When `token-report.json` is present but corrupt/all-zeros, the current code paths in `scripts/render-run-summary.sh` and `skills/implement/scripts/write-final-report.sh` silently yield $0.00. What should the desired behavior be?
- **Resolution**: Log warning, continue with $0.00. Detect the corrupt-zeros-with-present-file case and emit a clear `**⚠ token-report.json appears corrupt; reporting $0.00**` warning, then continue producing the report. Preserves current happy-path behavior for downstream consumers.
- **Source**: user

## Decision 4: In-scope items (combined OOS)
- **Question**: Which OOS items remain in scope after Item D deferral?
- **Resolution**: Items A (implement-bootstrap.md breadcrumb section freshness), B (phase_tracking ledger marks — per Decision 2), C (test-implement-bootstrap.sh missing harness cases for documented bail paths), E (docs/linting.md:238 stale Phase-2 case description), F (corrupt token-report.json warning emission — per Decision 3). Item D deferred per Decision 1.
- **Source**: user (combined with codebase inspection of the 6 OOS items)

## Decision 5: Hard constraints
- **Question**: What must not break in the implement bootstrap and final-report rendering paths?
- **Resolution**: (a) `phase_infra` and `phase_tracking` external behavior (KV outputs, sentinel writes, breadcrumbs) must remain stable; only add new ledger marks inside `phase_tracking`. (b) `render-run-summary.sh` and `write-final-report.sh` must keep their existing happy-path output format and exit codes — the only new behavior is an additional `**⚠ ...**` stderr line on corrupt-zero detection. (c) Test-harness additions must not change pass/fail status of existing cases; only add new cases for the bail paths in Item C.
- **Source**: codebase (existing /implement Step 0 and final-report contracts)
