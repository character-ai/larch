# Review Round 2

- Mode: `diff`
- 13 accepted, 17 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/test-implement-structure.sh:449-454
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Step 7a structure pin checks mark text only, not LARCH_TIMING_SKILL=implement, unlike Step 4/7 commit wrappers. A future edit can drop the implement skill pin from step-7a.sh without failing make test-implement-structure, reintroducing polluted-design-env mis-attribution for Step 7a intervals. Mirror the Step 4/7 grep -qF assertions for LARCH_TIMING_SKILL=implement on step-7a.sh timing-ledger and timing-report invocations.
- **Suggested revision**: Address the concern above.


### FINDING_26: code-quality: scripts/test-implement-structure.sh:450-451
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 7a structure harness does not require LARCH_TIMING_SKILL=implement unlike Step 4/7 pins. A future edit could drop the implement skill pin from step-7a.sh while still satisfying the substring grep, weakening polluted-env protection. Align the grep with commit-implementation.sh and require the full LARCH_TIMING_SKILL=implement timing-ledger mark literal.
- **Suggested revision**: Address the concern above.


### FINDING_27: architecture: skills/design/SKILL.md:4375-4391
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Design SKILL degraded-tools gate was rewritten despite plan saying all skills/design/ stay untouched. A workflow-only PR also changes /design Step 0 gate behavior and review surface, violating stated acceptance that design SIMPLE/HARD behavior stays byte-identical. Revert or split design SKILL changes into a separate PR; keep this PR implement/report-tokens only.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: scripts/degraded-tools-gate.sh; scripts/write-design-current-env.sh; skills/shared/external-reviewers.md; scripts/implement-bootstrap.sh:570-573
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch bundles #3540 degraded-tools presence handling not listed in the workflow-removal plan. Merged acceptance for workflow removal does not isolate regressions in availability waterfall, empty-presence warnings, or resume defaults (CODEX_PRESENT default "" vs "false"). Land #3540 separately or add explicit combined regression tests and call out the coupling in the PR description.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: scripts/test-timing-report.sh:3691-3714
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Design fallback harness omits DESIGN_TMPDIR cases required by the plan. DESIGN_TMPDIR-only fallback (run-params not sibling to ledger) is untested; a regression in that branch could slip through. Add a timing-report test with DESIGN_TMPDIR pointing at a fixture dir and ledger elsewhere.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/implement/SKILL.md:641
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Q/A redispatch prose has a broken fragment after workflow removal ("cursor presence, from"). Operator-facing SKILL text reads ungrammatical and may confuse implement orchestrators. Reword to "derives $PLAN_FILE, $FEATURE_FILE, and cursor presence from …".
- **Suggested revision**: Address the concern above.


### FINDING_33: **risk-integration** `scripts/test-implement-structure.sh:436-454` — The branch’s stated acceptance contract requires every implement production `timing-ledger.sh` / `timing-report.sh` caller to pin `LARCH_TIMING_SKILL=implement` (and clear `DESIGN_TMPDIR` on report subprocesses), and production code does so in `step-7a.sh`, `refresh-run-logs.sh`, and `implement-finalize.sh`; however `test-implement-structure.sh` only grep-asserts the pin on `commit-implementation.sh` and `commit-review-fixes.sh`, and its `step-7a.sh` check only requires a bare `timing-ledger.sh` mark substring without `LARCH_TIMING_SKILL=implement` or any `timing-report.sh` pin/`DESIGN_TMPDIR=''` assertion. A future regression that drops env pins on the pre-ship/refresh/finalize report paths would pass `make lint` while re-opening polluted-session workflow leakage or missing implement intervals. **Suggested fix:** Extend `test-implement-structure.sh` with the plan’s production-path acceptance greps (at minimum `step-7a.sh`, `refresh-run-logs.sh`, `implement-finalize.sh`, and `implement-bootstrap.sh` mark sites) mirroring the pins already enforced for commit wrappers.
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:436-454` — The branch’s stated acceptance contract requires every implement production `timing-ledger.sh` / `timing-report.sh` caller to pin `LARCH_TIMING_SKILL=implement` (and clear `DESIGN_TMPDIR` on report subprocesses), and production code does so in `step-7a.sh`, `refresh-run-logs.sh`, and `implement-finalize.sh`; however `test-implement-structure.sh` only grep-asserts the pin on `commit-implementation.sh` and `commit-review-fixes.sh`, and its `step-7a.sh` check only requires a bare `timing-ledger.sh` mark substring without `LARCH_TIMING_SKILL=implement` or any `timing-report.sh` pin/`DESIGN_TMPDIR=''` assertion. A future regression that drops env pins on the pre-ship/refresh/finalize report paths would pass `make lint` while re-opening polluted-session workflow leakage or missing implement intervals. **Suggested fix:** Extend `test-implement-structure.sh` with the plan’s production-path acceptance greps (at minimum `step-7a.sh`, `refresh-run-logs.sh`, `implement-finalize.sh`, and `implement-bootstrap.sh` mark sites) mirroring the pins already enforced for commit wrappers.
- **Suggested revision**: Address the concern above.


### FINDING_36: **risk-integration** `skills/implement/scripts/step2-implement.md:61-71` — The dispatcher contract doc still documents the Step 2 flag table but no longer records the coder timeout after removing `--workflow VALUE` (which previously mapped SIMPLE→3600s and HARD→7200s). Production code now hard-codes `LAUNCHER_TIMEOUT=7200` and always passes `--timeout 7200` to the Codex/Cursor launchers (`skills/implement/scripts/step2-implement.sh:656-668`), and `test-step2-dispatch.sh` test 17 pins that behavior, but the authoritative contract file operators and harness authors read does not mention the fixed 7200s boundary. That leaves a stale public contract surface where the only timeout documentation was deleted without a replacement. **Suggested fix:** Add an invariant or flags-table note in `step2-implement.md` stating external implementer launches always use a fixed 7200s wall-clock timeout (no `--workflow` flag, no SIMPLE/HARD branching), and cross-reference the launcher argv in `run-step2-dispatch.md` / `step2-implement.sh`.
- **Reviewer**: dyn-cli-contract-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/step2-implement.md:61-71` — The dispatcher contract doc still documents the Step 2 flag table but no longer records the coder timeout after removing `--workflow VALUE` (which previously mapped SIMPLE→3600s and HARD→7200s). Production code now hard-codes `LAUNCHER_TIMEOUT=7200` and always passes `--timeout 7200` to the Codex/Cursor launchers (`skills/implement/scripts/step2-implement.sh:656-668`), and `test-step2-dispatch.sh` test 17 pins that behavior, but the authoritative contract file operators and harness authors read does not mention the fixed 7200s boundary. That leaves a stale public contract surface where the only timeout documentation was deleted without a replacement. **Suggested fix:** Add an invariant or flags-table note in `step2-implement.md` stating external implementer launches always use a fixed 7200s wall-clock timeout (no `--workflow` flag, no SIMPLE/HARD branching), and cross-reference the launcher argv in `run-step2-dispatch.md` / `step2-implement.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_37: **risk-integration** `scripts/test-render-run-summary.sh:30-89` — The primary implement happy-path render tests still pass `--workflow-path SIMPLE` even though `/implement` is supposed to omit that flag entirely; only the later `TMP_NO_PATH` case (`scripts/test-render-run-summary.sh:235-255`) asserts absence of `- **Path**:`. Because `scripts/render-run-summary.sh:253-255` still prints the Path bullet whenever `--workflow-path` is non-empty, a regression that reintroduced `--workflow-path` on the implement caller (for example `skills/implement/scripts/write-final-report.sh`) would pass the main shape/cost tests while violating the no-workflow-path implement contract. **Suggested fix:** Remove `--workflow-path` from the primary implement fixtures in `scripts/test-render-run-summary.sh`, or add an explicit `assert_not_contains '- **Path**:'` guard to every `--skill implement` case so the harness enforces the new caller contract on the happy path, not only in the dedicated no-path test.
- **Reviewer**: dyn-cli-contract-output.txt
- **Concern**: - **risk-integration** `scripts/test-render-run-summary.sh:30-89` — The primary implement happy-path render tests still pass `--workflow-path SIMPLE` even though `/implement` is supposed to omit that flag entirely; only the later `TMP_NO_PATH` case (`scripts/test-render-run-summary.sh:235-255`) asserts absence of `- **Path**:`. Because `scripts/render-run-summary.sh:253-255` still prints the Path bullet whenever `--workflow-path` is non-empty, a regression that reintroduced `--workflow-path` on the implement caller (for example `skills/implement/scripts/write-final-report.sh`) would pass the main shape/cost tests while violating the no-workflow-path implement contract. **Suggested fix:** Remove `--workflow-path` from the primary implement fixtures in `scripts/test-render-run-summary.sh`, or add an explicit `assert_not_contains '- **Path**:'` guard to every `--skill implement` case so the harness enforces the new caller contract on the happy path, not only in the dedicated no-path test.
- **Suggested revision**: Address the concern above.


### FINDING_38: **code-quality** `scripts/step-telemetry-mark.sh:39-42` — This branch hardens implement `timing-report.sh` callers with `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` (`scripts/refresh-run-logs.sh`, `scripts/implement-finalize.sh`, `skills/implement/scripts/step-7a.sh`, `skills/implement/SKILL.md`), but the `timing-ledger.sh mark` in `step-telemetry-mark.sh` only prefixes `LARCH_TIMING_SKILL=implement` and still inherits ambient `DESIGN_TMPDIR`. `timing-ledger.sh` resolves the ledger via `IMPLEMENT_TMPDIR` only when that directory exists; on the helper’s never-fatal degenerate paths (missing/`--implement-tmpdir` without a value, non-existent tmpdir — explicitly exercised in `scripts/test-step-telemetry-mark.sh`), resolution can fall through to `DESIGN_TMPDIR` while the row is tagged `skill=implement`, splitting marks across ledgers in a design→implement polluted session. **Suggested fix:** Mirror the timing-report contract on line 42, e.g. `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$SCRIPT_DIR/timing-ledger.sh" mark "$LABEL"`, and only export `IMPLEMENT_TMPDIR` when `--implement-tmpdir` parsed a real directory.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/step-telemetry-mark.sh:39-42` — This branch hardens implement `timing-report.sh` callers with `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` (`scripts/refresh-run-logs.sh`, `scripts/implement-finalize.sh`, `skills/implement/scripts/step-7a.sh`, `skills/implement/SKILL.md`), but the `timing-ledger.sh mark` in `step-telemetry-mark.sh` only prefixes `LARCH_TIMING_SKILL=implement` and still inherits ambient `DESIGN_TMPDIR`. `timing-ledger.sh` resolves the ledger via `IMPLEMENT_TMPDIR` only when that directory exists; on the helper’s never-fatal degenerate paths (missing/`--implement-tmpdir` without a value, non-existent tmpdir — explicitly exercised in `scripts/test-step-telemetry-mark.sh`), resolution can fall through to `DESIGN_TMPDIR` while the row is tagged `skill=implement`, splitting marks across ledgers in a design→implement polluted session. **Suggested fix:** Mirror the timing-report contract on line 42, e.g. `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$SCRIPT_DIR/timing-ledger.sh" mark "$LABEL"`, and only export `IMPLEMENT_TMPDIR` when `--implement-tmpdir` parsed a real directory.
- **Suggested revision**: Address the concern above.


### FINDING_39: **code-quality** `scripts/test-implement-structure.sh:449-451` — The same PR adds byte-exact `LARCH_TIMING_SKILL=implement` pins for `commit-implementation.sh` and `commit-review-fixes.sh` (lines 442–447), but the `step-7a.sh` guard only matches the substring `timing-ledger.sh" mark "Step 7a — code flow diagram"` and would still pass if the implement-skill prefix were dropped. That is an inconsistent harness strength for the pollution-hardening work this branch is landing. **Suggested fix:** Align the step-7a assertion with the commit-script pins, e.g. `grep -qF 'LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram"'`.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/test-implement-structure.sh:449-451` — The same PR adds byte-exact `LARCH_TIMING_SKILL=implement` pins for `commit-implementation.sh` and `commit-review-fixes.sh` (lines 442–447), but the `step-7a.sh` guard only matches the substring `timing-ledger.sh" mark "Step 7a — code flow diagram"` and would still pass if the implement-skill prefix were dropped. That is an inconsistent harness strength for the pollution-hardening work this branch is landing. **Suggested fix:** Align the step-7a assertion with the commit-script pins, e.g. `grep -qF 'LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram"'`.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/design/SKILL.md:254-1573
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan said design surfaces were untouched, but the branch adds LARCH_TIMING_SKILL=design to all design timing marks and rewrites the degraded-tools gate block. Reviewers cannot tell which design changes are required for implement workflow removal versus unrelated gate work, increasing regression risk on /design. Split design timing-pin changes into a separate commit/PR or update plan acceptance to document the coupling.
- **Suggested revision**: Address the concern above.


### FINDING_40: **code-quality** `scripts/step-telemetry-mark.sh:14-28` — Flag parsing uses `[ $# -ge 2 ] || break` for valued options and `*) shift ;;` for unknown flags, so a missing `--implement-tmpdir` value silently stops parsing instead of rejecting the call, and `--implement-tmpdir --label "Step 5 — code review"` binds `IMPLEMENT_TMPDIR=--label`. SKILL.md now routes Steps 5/16/17/18 through this helper, so malformed argv is more likely to produce silent mis-marking under `set -uo pipefail` never-fatal semantics. **Suggested fix:** Fail closed on unknown flags and missing values (exit 0 after no-op is fine, but do not consume the next token as a tmpdir path), matching `persist-implement-run-flags.sh` / `run-step2-dispatch.sh` style validation.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/step-telemetry-mark.sh:14-28` — Flag parsing uses `[ $# -ge 2 ] || break` for valued options and `*) shift ;;` for unknown flags, so a missing `--implement-tmpdir` value silently stops parsing instead of rejecting the call, and `--implement-tmpdir --label "Step 5 — code review"` binds `IMPLEMENT_TMPDIR=--label`. SKILL.md now routes Steps 5/16/17/18 through this helper, so malformed argv is more likely to produce silent mis-marking under `set -uo pipefail` never-fatal semantics. **Suggested fix:** Fail closed on unknown flags and missing values (exit 0 after no-op is fine, but do not consume the next token as a tmpdir path), matching `persist-implement-run-flags.sh` / `run-step2-dispatch.sh` style validation.
- **Suggested revision**: Address the concern above.


