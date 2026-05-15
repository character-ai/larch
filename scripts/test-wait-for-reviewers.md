# scripts/test-wait-for-reviewers.md - contract

`scripts/test-wait-for-reviewers.sh` is the regression harness for `scripts/wait-for-reviewers.sh`'s `--timeout` validation contract and the `scripts/collect-agent-results.sh` wait-passthrough contract (closes #1186 + #1188 / umbrella #1200). It pins:

- **R1, R2**: literal `0`, zero-valued padded forms (`00`, `000`), and non-numeric values exit 1 with diagnostics containing `must be a positive integer`.
- **R3**: `--timeout` with no following value exits 1 with diagnostics containing `--timeout requires a value`. The empty-string case `--timeout ""` follows the same parameter-expansion path because Bash treats an empty `$2` as null for `${2:?}`. The case-statement empty-string arm is unreachable from normal CLI; the harness does not claim to exercise it.
- **R4, R5** (stdout grammar): `^DONE <idx> <basename>: exit=<code>$` on success, `^TIMEOUT <idx> <basename>$` on missed sentinel. This is the grammar that `scripts/collect-agent-results.sh`'s index-keyed timeout parser depends on.
- **R6** (duplicate basename fixture): two sentinel paths under different directories share `same.done` but emit distinct `DONE 1 same` / `DONE 2 same` records.
- **R7, R8** (`WAIT_FOR_REVIEWERS_POLL_INTERVAL` integer floor): `00` and `000` exit 1 with the positive-number diagnostic.
- **S1** (suspend-delta detection): PATH-stubbed `date` reports a long poll iteration and PATH-stubbed `sleep` materializes the sentinel during that iteration. The harness asserts the reviewer still reports `DONE` and diagnostics contain `suspend detected`.
- **C1, C2** (collector passthrough): `scripts/collect-agent-results.sh --timeout 0` and `--timeout abc` exit 1 with wait's diagnostics copied to the collector diagnostics followed by a `collect-agent-results.sh: wait-for-reviewers.sh exited <N>` trailer line, and no reviewer records on stdout. The trailer is part of the contract — the harness pins both the wait diagnostic message and the trailer prefix.

The full primary contract for the wait script lives at `scripts/wait-for-reviewers.md`. Wired into `make test-harnesses` via `the test-harnesses-N shard partition`. R5 takes about 1 wall-clock second by design at the harness poll interval because the wait loop computes `MAX_POLLS` from `--timeout` and `WAIT_FOR_REVIEWERS_POLL_INTERVAL`. `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05` tightens the dot-tick cadence while preserving the timeout grammar assertion. Edits to the harness must keep its rejection-message greps aligned with the validator's literal diagnostic text at `scripts/wait-for-reviewers.sh`'s timeout and poll-interval validators and Bash's parameter-expansion error format from the `--timeout` option parser.

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.
