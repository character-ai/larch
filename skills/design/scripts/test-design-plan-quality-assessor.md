# test-design-plan-quality-assessor.sh

Offline regression harness for `design-plan-quality-assessor.sh` and the `SKILL.md` Step 3.6 orchestrator handoff mirror (`apply_step3_6_handoff`).

Pins: argv errors, non-HARD skip, HARD happy path, `write-after` failure rollback, `EFFECTIVE_ASSESSORS=0` WARN chat visibility (including dedup and stdout-fallback), `assess-failed` handoff WARN replay, classification-alignment orchestrator banner, `cursor-read-failed` settle path, `ASSESSOR_STATUS=paused` pause checkpoint, `--timeout` argv forwarding, symlink refusal stderr, result-env key presence, fail-closed abort banners (exit `2` and empty mandatory keys), two-step `WARN=` chat contract, qualified-plugin-path invoke, and `LARCH_SNAPSHOT_PLAN_ROUND_SH` / `LARCH_ASSESS_PLAN_ROUND_SH` hermetic stubs.

Makefile target: `test-design-plan-quality-assessor`.

## Thin-fence regressions

The harness covers rc `0/2/10/11/*`, SIMPLE cheap-skip behavior, rc=10 trailer filtering/validation with fail-closed invalid trailers, rc=11 pause-save handoff, display neutralization for spoofed marker/KV lines, and `ASSESSOR_VERDICT_ENV` fixed-key sidecar loading. Stale fat-handoff expectations such as symlink result-env routing, mandatory-key stdout fallback, and `ASSESSOR_STATUS=paused` routing are obsolete.
