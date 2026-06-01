## Decision 1: Driver extraction boundary (region owned)
- **Question**: Should the new `design-publish.sh` own the entire deterministic tail starting at `plan-block-write.sh` (current Step 5c items 4–11) as one foreground call?
- **Resolution**: Yes. The driver owns items 4–11: `plan-block-write.sh`, `design_reentry_marker_write`, `REPO` resolve, 5c.5 diagrams upsert, `render-final-summary.sh` (pre+post), `design-log-publish.sh`, `[DESIGNED]` rename. Compose (item 1), validator gate (item 2), and redaction (item 3) stay prompt-side.
- **Source**: user

## Decision 2: plan-block-write failure summary ownership
- **Question**: On `plan-block-write` failure (preserve `$DESIGN_TMPDIR`, skip cleanup), who renders the `failed-plan-write` final-summary?
- **Resolution**: The driver renders it (`render-final-summary.sh` for the failure outcome) and returns `PLAN_WRITE_OK=false`. The orchestrator's post-driver behavior is uniform: emit `final-summary.md` verbatim once, then footer/cleanup keyed on `PLAN_WRITE_OK`/`PUBLISH_OK`. Single emit point for both success and failure.
- **Source**: user

## Decision 3: Step 5b → Step 5c ordering enforcement
- **Question**: How should the driver encode the "Step 5b before Step 5c" invariant?
- **Resolution**: Hard precondition. The driver verifies `$DESIGN_TMPDIR/.completed/step-5b` exists and exits non-zero (refusing to publish) if absent. The step-5b sentinel is written on all 5b exit paths, so this is safe and makes the ordering code-enforced.
- **Source**: user

## Decision 4: Prompt-side surface preserved
- **Question**: What stays prompt-side / out of the driver?
- **Resolution**: `composed-plan.md` authoring (LLM), the `invoke-plan-validator.sh` gate on `composed-plan.md` (review_budget != quick) with its shared Fix/Override/Cancel handler, and `redact-secrets.sh` → `composed-plan.redacted.md`. The `test-design-structure.sh` "validator-before-redact on composed-plan.md" pin therefore stays in SKILL.md prose. The driver consumes `composed-plan.redacted.md` as input.
- **Source**: codebase / issue #3246

## Decision 5: Harness + structural pins updated in lockstep
- **Question**: Must `test-design-structure.sh` change with this refactor?
- **Resolution**: Yes. Add `design-publish.sh` structural pins mirroring the `design-init-runparams.sh` pattern (SKILL Step 5c invokes the driver; driver calls plan-block-write / reentry-marker / upsert-diagrams / design-log-publish / render-final-summary / tracking-issue-write rename; ordering: marker before publish/rename, upsert after plan-write before publish, hard-fail on missing step-5b sentinel; exit-2 prose; result-env file-first read; REPO threading). Preserve the existing anti-halt step chains (`5→5a→5b→5c.1→5c.5→5c.7→5c.8→6`) and the 5b-before-5c header-order check. Add `test-design-publish.sh` offline harness + `.md` siblings (script-md-siblings rule). Grep docs/ for stale Step 5c prose (drift-prone-prose rule).
- **Source**: codebase (test-design-structure.sh, .claude/rules)

## Decision 6: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: The cancellation-path Final-summary callsites (Step 0b / 2b.5 / 3.6) stay as-is. The other 5 umbrella #3133 pieces are not touched here. No behavior change to the publish/rename/summary semantics — this is a pure prose→code extraction that must preserve every existing branch (SESSION_ID-empty skips, PUBLISH_OK gating of the rename, UPSERT failure non-blocking, etc.).
- **Source**: codebase / issue #3246

## Decision 7: Driver implementation pattern
- **Question**: What structural template does `design-publish.sh` follow?
- **Resolution**: The `lib-phase-driver.sh` sibling-driver pattern: `set -euo pipefail`, source `lib-phase-driver.sh` + `larch_quiet_init`, `fail()`→`larch_err`+exit 2, argv validation helpers, `phase_driver_resolve_plugin_root`, write `.design-publish-result.env` via `phase_driver_write_result_env`, `emit_kv` machine stdout (`PLAN_WRITE_OK`, `PUBLISH_OK`, `RENAMED`, `UPSERT_STATUS`, `FINAL_SUMMARY_PATH`, `WARN`), exit codes 2=config/argv, 1=operational, 0=success, Bash 3.2-safe.
- **Source**: codebase (design-init-runparams.sh)
