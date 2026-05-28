# test-lib-net.sh

Hermetic offline harness for `scripts/lib-net.sh`.

## Scope

- `is_transient_net_signature` positive and negative fixtures
- `with_transient_retry` rc=0 short-circuit, transient rc!=0 retry (3 attempts), non-transient short-circuit, rc=0 envelope-predicate retry, and 2s/4s backoff via stubbed `sleep-seconds.sh`
- `ship_pr_with_transient_retry` envelope exhaustion (rc=0 after retries but predicate still matches) invoking stubbed `exit_transient_net`

## Fixture layout

Working dir: `${TMPDIR}/test-lib-net.XXXXXX`. Stub commands write stderr to the `fail_file` first argument and print stdout; `SLEEP_SCRIPT_DIR` points at a stub `sleep-seconds.sh` that appends sleep durations to `SLEEP_LOG`.

## Run

```bash
bash scripts/test-lib-net.sh
```

Or `make test-lib-net`.
