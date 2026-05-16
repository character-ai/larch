# check-step-token-budget.sh contract

**Sibling script**: `scripts/check-step-token-budget.sh`.

**Purpose**: Per-step combined vendor token budget guard for launcher scripts. Reads the JSONL token-ledger for the current session, sums all vendor `total` fields since the last `mark` row, and compares the total against a configured cap. Launchers call this helper before spawning an external agent; when the cap is exceeded they short-circuit with a `STATUS=cap_hit` signal.

## Invocation

```bash
check-step-token-budget.sh --cap N [--step NAME]
```

- `--cap N` (required): combined token cap as a positive integer.
- `--step NAME` (optional): human-readable step name included in the output for diagnostic purposes; defaults to `unknown`.

## Stdout

Exactly one line, one of:

```
STATUS=cap_hit TOTAL=<N> CAP=<N> STEP=<name>
STATUS=under_cap TOTAL=<N> CAP=<N> STEP=<name>
```

## Session identity

`LARCH_TOKEN_SESSION_ID` is read from the environment or from `$IMPLEMENT_TMPDIR/session-id` when the env var is absent.  The helper passes the resolved session ID to `token-ledger.sh dump`, which reads only the JSONL file for that session.

## Ledger parsing

The helper reads `token-ledger.sh dump` output and uses awk to walk the JSONL rows:

- Any `"type":"mark"` row resets the running total to 0.
- Any `"type":"vendor"` row adds its `"total"` field to the running total.

The final total therefore reflects only the vendor records logged after the **last** step mark — i.e. the current step's external-reviewer spend.

## Fail-open behavior

Any ledger read error, missing JSONL file, or parse failure leaves `TOTAL=0` and returns `STATUS=under_cap`.  This guarantees that a transient failure (e.g. `LARCH_TOKEN_SESSION_ID` unset, ledger not yet created) never hard-blocks a launcher.

## Exit code

Always 0.

## Callers

Each caller passes `--cap $TOKEN_BUDGET_CAP` when the `--token-budget-cap` flag was supplied.

## Edit-in-sync

When changing the ledger JSON schema (e.g. renaming `"type":"vendor"` or `"total"` keys), update the awk logic in this script in the same PR.
