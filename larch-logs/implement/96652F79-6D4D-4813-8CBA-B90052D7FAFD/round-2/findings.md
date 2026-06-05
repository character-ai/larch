### FINDING_1: code-quality: scripts/test-implement-structure.sh:449-454
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Step 7a structure pin checks mark text only, not LARCH_TIMING_SKILL=implement, unlike Step 4/7 commit wrappers. A future edit can drop the implement skill pin from step-7a.sh without failing make test-implement-structure, reintroducing polluted-design-env mis-attribution for Step 7a intervals. Mirror the Step 4/7 grep -qF assertions for LARCH_TIMING_SKILL=implement on step-7a.sh timing-ledger and timing-report invocations.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-implement-structure.sh:2947-2955
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan acceptance requires all production timing callers to pin LARCH_TIMING_SKILL=implement, but enforcement is fragmented across multiple harnesses with no unified production-script grep. A new implement script can add timing-ledger.sh mark without the pin and pass CI until an operator notices missing Step N intervals after a /design→/implement session. Add one test-implement-structure block grepping an allowlisted production caller set for LARCH_TIMING_SKILL=implement (and DESIGN_TMPDIR clearing on timing-report calls).
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: python/report_tokens_issue.py:20-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _TITLE_BY_SECTION still maps aggregate to design-only label Aggregate cost by workflow while implement relies on _section_label special-casing. A maintainer using the map directly for implement trim notices could reintroduce design-only omission text. Split or neutralize the aggregate title map so implement and design labels are explicit without a hidden override.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/SKILL.md:254-1573
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan said design surfaces were untouched, but the branch adds LARCH_TIMING_SKILL=design to all design timing marks and rewrites the degraded-tools gate block. Reviewers cannot tell which design changes are required for implement workflow removal versus unrelated gate work, increasing regression risk on /design. Split design timing-pin changes into a separate commit/PR or update plan acceptance to document the coupling.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/degraded-tools-gate.sh:1-200
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unrelated degraded-tools gate refactor is bundled with workflow-removal work. Higher coupling makes bisect/revert of workflow removal harder if design gate behavior regresses. Land gate fixes separately or isolate commits by feature.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/compute-pr-line-counts.sh:1151-1168
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated repo-slug validation and write-final-report LINES_DATA_OK simplification ride along in the same PR. Increases diff size and review time for a workflow-classification change. Split into a focused follow-up if not required for round-1 review fixes.
- **Suggested revision**: Address the concern above.

### FINDING_7: `37fed349b` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `37fed349b` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_8: `3c40c119b` — chore(larch-logs) implement run flush
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `3c40c119b` — chore(larch-logs) implement run flush
- **Suggested revision**: Address the concern above.

### FINDING_9: `7c00d697d` — Remove implement workflow classification
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `7c00d697d` — Remove implement workflow classification
- **Suggested revision**: Address the concern above.

### FINDING_10: (plus merged upstream chores unrelated to this feature)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - (plus merged upstream chores unrelated to this feature) ## Plan verification (summary) The diff matches the stated intent:
- **Suggested revision**: Address the concern above.

### FINDING_11: `/implement` no longer passes `--workflow`, persists `WORKFLOW_PATH`, or calls `timing-ledger.sh workflow-path`; Step 2 timeout is fixed at 7200s.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `/implement` no longer passes `--workflow`, persists `WORKFLOW_PATH`, or calls `timing-ledger.sh workflow-path`; Step 2 timeout is fixed at 7200s.
- **Suggested revision**: Address the concern above.

### FINDING_12: Implement summaries and timing reports omit Path / Workflow path; `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; implement callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Implement summaries and timing reports omit Path / Workflow path; `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; implement callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.

### FINDING_13: `report_tokens_scan._workflow` early-returns `""` for implement; render/issue paths are skill-aware; design behavior is preserved behind explicit `LARCH_TIMING_SKILL=design` pins.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `report_tokens_scan._workflow` early-returns `""` for implement; render/issue paths are skill-aware; design behavior is preserved behind explicit `LARCH_TIMING_SKILL=design` pins.
- **Suggested revision**: Address the concern above.

### FINDING_14: Round-1 gaps (legacy-flag test, `LARCH_TIMING_SKILL` pins on commit scripts, omit-`--workflow-path` render test, degraded-tools fence) appear addressed.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Round-1 gaps (legacy-flag test, `LARCH_TIMING_SKILL` pins on commit scripts, omit-`--workflow-path` render test, degraded-tools fence) appear addressed. Checked edge cases called out in the plan: polluted design env (shell + Python tests), legacy ledger `v1 workflow` rows, stale `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH` in tmpdir artifacts, and implement cache NDJSON omitting `"workflow"`.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: python/test_report_tokens_cli.py:51-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required CLI test only asserts post_issue receives skill=implement; no --skill design forwarding test. report_tokens_cli could regress to hardcoding skill=implement while design issue trim labels break silently. Add test_main path calling main(["--skill","design"]) and assert posted == [("o/r","design")].
- **Suggested revision**: Address the concern above.

### FINDING_16: **Env pollution**: Implement timing callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR` (`timing-report.sh`, `implement-finalize.sh`, `refresh-run-logs.sh`, `step-7a.sh`, `run-relevant-checks-captured.sh`, `step-telemetry-mark.sh`, `python/run_logs.py::_report_subprocess_env`). `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design` only.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Env pollution**: Implement timing callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR` (`timing-report.sh`, `implement-finalize.sh`, `refresh-run-logs.sh`, `step-7a.sh`, `run-relevant-checks-captured.sh`, `step-telemetry-mark.sh`, `python/run_logs.py::_report_subprocess_env`). `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design` only.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Reduced scan surface**: `python/report_tokens_scan.py::_workflow` returns `""` for implement before opening auxiliary JSON; `SECURITY.md` documents this boundary.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Reduced scan surface**: `python/report_tokens_scan.py::_workflow` returns `""` for implement before opening auxiliary JSON; `SECURITY.md` documents this boundary.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Stale session data**: `write-final-report.sh` no longer reads `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH`, so committed/session artifacts cannot repopulate the public Path bullet.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stale session data**: `write-final-report.sh` no longer reads `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH`, so committed/session artifacts cannot repopulate the public Path bullet.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Input validation**: `compute-pr-line-counts.sh` rejects non-numeric PR numbers and malformed repo slugs before `gh api`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Input validation**: `compute-pr-line-counts.sh` rejects non-numeric PR numbers and malformed repo slugs before `gh api`.
- **Suggested revision**: Address the concern above.

### FINDING_20: **Fail-safe degradation**: `degraded-tools-gate.sh` treats empty presence inputs as down when caller rehydration is incomplete.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-safe degradation**: `degraded-tools-gate.sh` treats empty presence inputs as down when caller rehydration is incomplete.
- **Suggested revision**: Address the concern above.

### FINDING_21: **Subprocess safety**: Timing refresh uses argv-array `subprocess.Popen` (no shell); ledger mark fields go through `sanitize_field`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Subprocess safety**: Timing refresh uses argv-array `subprocess.Popen` (no shell); ledger mark fields go through `sanitize_field`. No injection, auth bypass, secret leakage, path traversal, or deserialization regressions were found in the changed production paths.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/render-run-summary.sh:253-255` — The renderer still emits `- **Path**:` for `--skill implement` whenever any caller passes a non-empty `--workflow-path`; only the primary implement caller (`write-final-report.sh`) was updated to omit the flag. A future or alternate caller could still push arbitrary strings into tracking-issue / final-summary markdown (a public GitHub boundary). **Suggested fix:** Ignore or reject `--workflow-path` when `--skill implement` (defense in depth), matching the implement contract that Path is design-only.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `python/run_logs.py:105-118` — `_report_subprocess_env` still clones the full parent `os.environ` before overlaying implement pins. This is the existing trust model, but any unexpected inherited variable could affect child script behavior beyond the newly pinned keys. **Suggested fix:** Consider an allowlist-based env for timing-report subprocesses in a future hardening pass (out of scope for this workflow-removal change).
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/launch-codex-implement.sh:225-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] External implementer launchers record vendor timing without pinning LARCH_TIMING_SKILL=implement. A Claude session polluted with LARCH_TIMING_SKILL=design from a prior /design run can tag Step 2/5 vendor rows with skill=design in the implement ledger; per-step implement durations stay correct because marks are pinned, but vendor-row skill metadata is silently wrong for downstream ledger consumers. Export or inline-prefix LARCH_TIMING_SKILL=implement on every implement-scoped record-vendor-task invocation in launch-codex-implement.sh launch-cursor-implement.sh and launch-review.sh.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/timing-report.sh:4171-4175
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removing workflow row parsing and workflow_ts from last_event_ts changes duration math for legacy ledgers. Re-running timing-report.sh against an old implement ledger that still has v1 workflow rows can emit shorter total_seconds/total_hms than the committed timing-report.json from the original run. Document the behavior in timing-report.md or retain a legacy-only workflow_ts floor for implement re-renders while keeping workflow_path unknown in output.
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

### FINDING_29: architecture: scripts/step-telemetry-mark.sh; skills/implement/SKILL.md:774,1177,1212,1300
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Steps 5/16/17/18 entry timing marks use a new helper not named in the plan file list. Plan/harness docs still describe inline timing-ledger pins; future edits may miss the helper contract. Add the helper to the plan acceptance grep or restore inline LARCH_TIMING_SKILL=implement fences per original plan.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/test-timing-report.sh:3691-3714
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Design fallback harness omits DESIGN_TMPDIR cases required by the plan. DESIGN_TMPDIR-only fallback (run-params not sibling to ledger) is untested; a regression in that branch could slip through. Add a timing-report test with DESIGN_TMPDIR pointing at a fixture dir and ledger elsewhere.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/implement/SKILL.md:641
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Q/A redispatch prose has a broken fragment after workflow removal ("cursor presence, from"). Operator-facing SKILL text reads ungrammatical and may confuse implement orchestrators. Reword to "derives $PLAN_FILE, $FEATURE_FILE, and cursor presence from …".
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/compute-pr-line-counts.sh; skills/implement/scripts/write-final-report.sh:6493-6518
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] compute-pr-line-counts validation and write-final-report LINES_DATA_OK simplification are outside the workflow plan. Unrelated behavioral change bundled into the same PR increases review surface. Track as separate follow-up or note explicitly in PR summary.
- **Suggested revision**: Address the concern above.

### FINDING_33: **risk-integration** `scripts/test-implement-structure.sh:436-454` — The branch’s stated acceptance contract requires every implement production `timing-ledger.sh` / `timing-report.sh` caller to pin `LARCH_TIMING_SKILL=implement` (and clear `DESIGN_TMPDIR` on report subprocesses), and production code does so in `step-7a.sh`, `refresh-run-logs.sh`, and `implement-finalize.sh`; however `test-implement-structure.sh` only grep-asserts the pin on `commit-implementation.sh` and `commit-review-fixes.sh`, and its `step-7a.sh` check only requires a bare `timing-ledger.sh` mark substring without `LARCH_TIMING_SKILL=implement` or any `timing-report.sh` pin/`DESIGN_TMPDIR=''` assertion. A future regression that drops env pins on the pre-ship/refresh/finalize report paths would pass `make lint` while re-opening polluted-session workflow leakage or missing implement intervals. **Suggested fix:** Extend `test-implement-structure.sh` with the plan’s production-path acceptance greps (at minimum `step-7a.sh`, `refresh-run-logs.sh`, `implement-finalize.sh`, and `implement-bootstrap.sh` mark sites) mirroring the pins already enforced for commit wrappers.
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:436-454` — The branch’s stated acceptance contract requires every implement production `timing-ledger.sh` / `timing-report.sh` caller to pin `LARCH_TIMING_SKILL=implement` (and clear `DESIGN_TMPDIR` on report subprocesses), and production code does so in `step-7a.sh`, `refresh-run-logs.sh`, and `implement-finalize.sh`; however `test-implement-structure.sh` only grep-asserts the pin on `commit-implementation.sh` and `commit-review-fixes.sh`, and its `step-7a.sh` check only requires a bare `timing-ledger.sh` mark substring without `LARCH_TIMING_SKILL=implement` or any `timing-report.sh` pin/`DESIGN_TMPDIR=''` assertion. A future regression that drops env pins on the pre-ship/refresh/finalize report paths would pass `make lint` while re-opening polluted-session workflow leakage or missing implement intervals. **Suggested fix:** Extend `test-implement-structure.sh` with the plan’s production-path acceptance greps (at minimum `step-7a.sh`, `refresh-run-logs.sh`, `implement-finalize.sh`, and `implement-bootstrap.sh` mark sites) mirroring the pins already enforced for commit wrappers.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `scripts/launch-codex-implement.sh:230-238` and `scripts/launch-review.sh:94-102` — External implementer/reviewer launchers still call `timing-ledger.sh record-vendor-task` without `LARCH_TIMING_SKILL=implement`, so a session that still exports `LARCH_TIMING_SKILL=design` after `/design` can stamp vendor rows with `design` in column 4. This predates the branch, was not changed in the diff, and current `timing-report.sh` vendor aggregation ignores that skill column; impact is mostly ledger hygiene, not SIMPLE/HARD workflow leakage.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `python/checks.py:186-201` — The Python relevant-checks parity path spreads `os.environ` into timing-ledger marks without pinning `LARCH_TIMING_SKILL=implement`, while the live `/implement` shell helper `run-relevant-checks-captured.sh` was updated in this branch. This is dev/CI Phase-4 parity only (not the live orchestrator path) and unchanged by the diff.
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

### FINDING_40: **code-quality** `scripts/step-telemetry-mark.sh:14-28` — Flag parsing uses `[ $# -ge 2 ] || break` for valued options and `*) shift ;;` for unknown flags, so a missing `--implement-tmpdir` value silently stops parsing instead of rejecting the call, and `--implement-tmpdir --label "Step 5 — code review"` binds `IMPLEMENT_TMPDIR=--label`. SKILL.md now routes Steps 5/16/17/18 through this helper, so malformed argv is more likely to produce silent mis-marking under `set -uo pipefail` never-fatal semantics. **Suggested fix:** Fail closed on unknown flags and missing values (exit 0 after no-op is fine, but do not consume the next token as a tmpdir path), matching `persist-implement-run-flags.sh` / `run-step2-dispatch.sh` style validation.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/step-telemetry-mark.sh:14-28` — Flag parsing uses `[ $# -ge 2 ] || break` for valued options and `*) shift ;;` for unknown flags, so a missing `--implement-tmpdir` value silently stops parsing instead of rejecting the call, and `--implement-tmpdir --label "Step 5 — code review"` binds `IMPLEMENT_TMPDIR=--label`. SKILL.md now routes Steps 5/16/17/18 through this helper, so malformed argv is more likely to produce silent mis-marking under `set -uo pipefail` never-fatal semantics. **Suggested fix:** Fail closed on unknown flags and missing values (exit 0 after no-op is fine, but do not consume the next token as a tmpdir path), matching `persist-implement-run-flags.sh` / `run-step2-dispatch.sh` style validation.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/test-implement-timing-rehydration.sh:155-156` — The hard-coded expectation `plugin_root_source_count == 42` will break on any unrelated `SKILL.md` fence edit; consider deriving the count from a single documented invariant or bumping via a named constant in the harness header.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] No Bash 3.2 portability problems found in the workflow-removal edits: same-line env assignment (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement cmd`), `"${array[@]+"${array[@]}"}"` nounset-safe expansion, and `--workflow` removal in `step2-implement.sh` / `run-step2-dispatch.sh` all look correct; argv loops use proper `shift 2` and terminate unknown flags with exit 2.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - No Bash 3.2 portability problems found in the workflow-removal edits: same-line env assignment (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement cmd`), `"${array[@]+"${array[@]}"}"` nounset-safe expansion, and `--workflow` removal in `step2-implement.sh` / `run-step2-dispatch.sh` all look correct; argv loops use proper `shift 2` and terminate unknown flags with exit 2.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] Production implement surfaces no longer read or persist `WORKFLOW_PATH` / `--workflow`; fixed `LAUNCHER_TIMEOUT=7200` in `skills/implement/scripts/step2-implement.sh:657`; `scripts/timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; `python/run_logs.py:105-109` clears `DESIGN_TMPDIR` for timing-report subprocesses; and `skills/implement/scripts/write-final-report.sh` omits `--workflow-path` when calling `render-run-summary.sh`.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - Production implement surfaces no longer read or persist `WORKFLOW_PATH` / `--workflow`; fixed `LAUNCHER_TIMEOUT=7200` in `skills/implement/scripts/step2-implement.sh:657`; `scripts/timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; `python/run_logs.py:105-109` clears `DESIGN_TMPDIR` for timing-report subprocesses; and `skills/implement/scripts/write-final-report.sh` omits `--workflow-path` when calling `render-run-summary.sh`.
- **Suggested revision**: Address the concern above.

