# test-get-issue-state.sh contract

## Purpose

Regression harness for `scripts/get-issue-state.sh`, the `/implement` Step 0 adoption target state/URL probe.

## Coverage

The harness runs offline with a PATH-stubbed `gh`. It pins the new numeric `--issue` self-validation, preserved missing-argument behavior, valid numeric values passing through to the `gh` boundary, `gh` failure envelopes, and the success envelope (`STATE=`, `URL=`, `IS_PR=`).

## Makefile wiring

Makefile target: `test-get-issue-state` — `bash scripts/harness-timer.sh $@ bash scripts/test-get-issue-state.sh`.

Shard placement: `test-harnesses-18`, alongside `test-tracking-issue-read-sentinel`.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/get-issue-state.sh` | Script under test. Any change to validation, `gh` argv, or output fields should update this harness. |
| `scripts/get-issue-state.md` | Runtime contract for the wrapper. |
| `Makefile` | Owns the `test-get-issue-state` recipe and shard membership. |
| `agent-lint.toml` | Excludes this Makefile-only harness from dead-script checks. |

## Conventions

Bash 3.2-safe. The harness is hermetic and does not touch the network.
