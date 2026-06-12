# test-design-postplan-emit.sh

Regression harness for `design-postplan-emit.sh`.

The primary contract lives in `design-postplan-emit.md`; this sibling exists for the script-documentation invariant and should be updated with that primary when harness coverage changes.

## `--with-plan-size` harness coverage

Tests added for the new mode (real `check-plan-size.sh` symlinked into the fake plugin tree via `$TMP/fake-plugin`):

- **clean rc 0**: display breadcrumb present, KVs only in result env, no stdout KV leakage.
- **plan body > 800 lines**: hard rc 12.
- **`diff_added > 2000`**: hard rc 12.
- **`mechanical_churn: true`**: soft advisory display, rc 0.
- **soft advisory + hard trigger**: both advisory and hard-section preamble displayed before rc 12.
- **`partition_requested=true`**: rc 13.
- **`partition_requested=true` with jq hidden from PATH**: still rc 13 (sed boolean fallback).
- **`partition_requested=true` + hard-sized plan**: rc 12, not rc 13 (hard wins over partition).
- **defects-found**: rc 10; plan-size skipped; validator context in result env.
- **`--snapshot-original` composition**: rc 0 clean path with snapshot.
- **D27+ nonfatal / merged failures**: plan-size rc 2/3 WARN display, `check-plan-size.validation.log` written, stderr diagnostics preserved, `execution-issues.md` entry attempted, no `APPENDED=` / `LOG=` in display output, nonfatal even when `run-log append-failure` itself fails; merged rc1 diagnostics for `snapshot-failed` and `validate-driver-failed`.
- **pause rc 11**: thin fence can exec pause-save.
- **missing run-params**: defaults remain quiet; no removed classification-reader warning is emitted.
- **rc1 subfailures**: failure-specific diagnostic emitted before exit.
- **result-env create/truncate/write failure or symlink**: rc1 with clear diagnostic, no stdout-KV fallback.
- **nested plan-size with `LARCH_QUIET_DISABLE=1`**: verdict KVs and WARNs captured even under a quiet-mode parent.

Non-flag cases retained to prove unchanged `{0,1,2}` + FD3-KV contract.

## Quiet-mode regression

The harness includes a default-quiet case with `run-params.json` removed. It asserts the merged postplan path stays quiet instead of replaying the removed classification-reader warning.
