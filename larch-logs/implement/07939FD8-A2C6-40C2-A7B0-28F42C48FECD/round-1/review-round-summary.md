# Review Round 1

- Mode: `diff`
- 3 accepted, 16 rejected (3 exonerated)

## Accepted Findings

### FINDING_13: correctness: scripts/launch-claude-ci.sh:192-199
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] Claude CI vendor timing pin is applied to a record-vendor-task call that timing-ledger.sh rejects because only codex|cursor vendors are accepted. launch-claude-ci.sh invokes record-vendor-task --vendor claude, timing-ledger.sh returns 1, the launcher suppresses it with || true, and the new scanner still passes without any Claude CI timing row being recorded. Add claude as an accepted vendor with regression coverage for claude-ci-fix, or exclude launch-claude-ci.sh from the vendor-row contract if unsupported.
- **Suggested revision**: Address the concern above.


### FINDING_24: **risk-integration** `scripts/launch-claude-ci.sh:192-199` — This branch adds `launch-claude-ci.sh` to the A1 timing-pin scanner and applies an A2 `LARCH_TIMING_SKILL=implement` prefix on its `record-vendor-task` call, but `scripts/timing-ledger.sh:192` only accepts `--vendor codex|cursor`. The launcher passes `--vendor claude`, so `cmd_record_vendor_task` always returns 1 and the trailing `|| true` swallows the failure; no Claude CI-fix vendor rows are ever written. The new pin and scanner entry therefore imply guarded implement telemetry where none is recorded, which is a false-confidence integration risk rather than a real attribution fix. **Suggested fix:** Either teach `timing-ledger.sh` to accept `claude` when `task-kind` is `claude-ci-fix` (and add a harness asserting a row lands with `skill=implement`), or stop treating `launch-claude-ci.sh` as a vendor-row emitter in the A1 scanned set and document that Claude CI-fix wall time is not captured via `record-vendor-task`.
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `scripts/launch-claude-ci.sh:192-199` — This branch adds `launch-claude-ci.sh` to the A1 timing-pin scanner and applies an A2 `LARCH_TIMING_SKILL=implement` prefix on its `record-vendor-task` call, but `scripts/timing-ledger.sh:192` only accepts `--vendor codex|cursor`. The launcher passes `--vendor claude`, so `cmd_record_vendor_task` always returns 1 and the trailing `|| true` swallows the failure; no Claude CI-fix vendor rows are ever written. The new pin and scanner entry therefore imply guarded implement telemetry where none is recorded, which is a false-confidence integration risk rather than a real attribution fix. **Suggested fix:** Either teach `timing-ledger.sh` to accept `claude` when `task-kind` is `claude-ci-fix` (and add a harness asserting a row lands with `skill=implement`), or stop treating `launch-claude-ci.sh` as a vendor-row emitter in the A1 scanned set and document that Claude CI-fix wall time is not captured via `record-vendor-task`.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/launch-claude-ci.sh:192-199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A1 now pins LARCH_TIMING_SKILL on record-vendor-task but timing-ledger.sh rejects --vendor claude and the launcher swallows the failure. Claude CI-fix runs pass the new scanner yet still emit no vendor timing row, leaving implement timing reports incomplete under the false belief CI launchers are covered. Accept claude in timing-ledger record-vendor-task, or remove the call and document mark-only Claude CI telemetry.
- **Suggested revision**: Address the concern above.


