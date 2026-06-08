# test-fluff-analysis.sh contract

Offline regression harness for `fluff-analysis.py` (the `/fluff-analysis`
analyzer). Self-contained: builds a synthetic `larch-logs` fixture under a
`mktemp` dir, runs the analyzer against it, and asserts:

- the report shape (`# Review Fluff Analysis`, `## Baselines`, implement +
  design baseline rows, `## Q1 …`, `## Recommendations`);
- a fluff group surfaces from the rejected-nit finding's refactor/clarity text;
- the implement reviewer-severity table renders;
- `--cutoff` adds the `## Pre/post cutoff` section;
- a missing `--log-root` exits `2`.

## Run

```bash
bash skills/fluff-analysis/scripts/test-fluff-analysis.sh
```

Exit `0` when all assertions pass, `1` otherwise.

## Wiring

Registered as the `test-fluff-analysis` Makefile target and assigned to a
`test-harnesses-*` shard (enforced by `test-harness-shards-coverage`). Primary
script under test: `skills/fluff-analysis/scripts/fluff-analysis.py`.
