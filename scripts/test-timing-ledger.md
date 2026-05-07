# test-timing-ledger.sh

Offline regression harness for `scripts/timing-ledger.sh`. It covers mark/workflow/vendor row shape, basename-only output storage, chmod mode, unknown task-kind warnings, malformed task-kind rejection, negative-duration clamping, `LARCH_TIMING_LEDGER` containment fallback, env-ledger acceptance, and parallel append column integrity.
