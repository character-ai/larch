# test-design-plan-quality-assessor.sh

Offline regression harness for `design-plan-quality-assessor.sh` and the `SKILL.md` Step 3.6 orchestrator handoff mirror (`apply_step3_6_handoff`).

Pins: argv errors, non-HARD skip, HARD happy path, `write-after` failure rollback, `EFFECTIVE_ASSESSORS=0` WARN chat visibility, symlink refusal stderr, result-env key presence, fail-closed abort banners (exit `2` and empty mandatory keys), two-step `WARN=` chat contract, qualified-plugin-path invoke, and `LARCH_SNAPSHOT_PLAN_ROUND_SH` / `LARCH_ASSESS_PLAN_ROUND_SH` hermetic stubs.

Makefile target: `test-design-plan-quality-assessor`.
