### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_review.py:1143-1147; plan.txt:41,87-91
- **Concern**: [SCOPE-REDUCTION] Plan still regenerates tally-plan-review.sh although tally_plan_review() is in-process only and never runs the embedded bash. Scenario: tally_plan_review() returns plan_review_tally.main(list(argv)) and the comment states the gzip blob is retained but not executed. Re-encoding that blob changes hundreds of base64 lines with zero runtime effect; the only driver is the planned global quiet-before-validate test that scans every asset containing larch_quiet_init
- **Proposed resolution**: Drop skills/design/scripts/tally-plan-review.sh from the nine-script regen list. Scope the global invariant test to _LEGACY_ASSETS keys whose live Python entrypoints still call _run_legacy for that path (exclude tally explicitly), or add a small dead-asset denylist in the test so pytest does not force dead-blob churn

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py embedded skills/design/scripts/run-step3-review.sh; plan.txt:71-85
- **Concern**: Non-preview validate placement is ambiguous for `--mode loop`: bullets group `single`, `loop`, and `run_step3_round_body`, but loop mode never calls `run_step3_round_body`; it cds/exports in a separate bottom `if [[ "$STEP3_MODE" == loop ]]` block before sourcing `review-design-step3-loop.sh`. Scenario: An implementer can add validate+quiet only inside `run_step3_round_body`, leaving the loop branch still doing `DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" ...)"` and downstream writes with no allowlist check while entry-level `larch_quiet_init` is removed; the security regression persists on the primary `plan-review run --mode loop` path
- **Proposed resolution**: Spell out one shared non-preview preamble immediately after the `--preview-only` early-exit: resolve `PLUGIN_ROOT` (preview-path `phase_driver_resolve_plugin_root` pattern), `session validate-design-tmpdir "$DESIGN_TMPDIR_ARG" || exit $?`, bind/export `DESIGN_TMPDIR`, then `larch_quiet_init`; only then enter the loop fork or `run_step3_round_body`
