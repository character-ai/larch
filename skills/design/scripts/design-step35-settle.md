# design-step35-settle.sh

## Purpose

Shared post-rewrite settle wrapper for Gate B, Gate A after-discussion rewrites, and discussion Round 2. It runs the mechanical post-rewrite dedup, delegates postplan to `python/cli.py design step2b-postplan`, and centralizes the exit-code and marker contract that prompt-side prose previously respelled.

## Primary callers

Prompt-side `/design` calls this wrapper through the design launcher:

```bash
"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b
```

Gate A uses `--site gate-a`. Discussion Round 2 uses `--site discussion-round2`.

## Arguments

| Argument | Required | Purpose |
| --- | --- | --- |
| `--session-env-path PATH` | launcher-supplied | Optional session env to source before plugin-root validation. |
| `--claude-pid PID` | launcher-supplied | Forwarded to `python/cli.py design step2b-postplan`. |
| `--plugin-root DIR` | launcher-supplied | Plugin root used for helper resolution. |
| `--site gate-b\|gate-a\|discussion-round2` | yes | Selects marker handling and postplan site mapping. |
| `--round-num N` | Gate B optional | Explicit Gate B review round. |

## Gate B round derivation

For `--site gate-b`, the wrapper resolves the round in this order:

| Order | Source |
| --- | --- |
| 1 | `--round-num` |
| 2 | `FINAL_ROUND_NUM` |
| 3 | `STEP3_REVIEW_ROUND_NUM` |
| 4 | `ROUND_NUM` |

Missing or non-numeric Gate B rounds exit `2`.

## Site mapping

| Settle site | Internal postplan call |
| --- | --- |
| `gate-b` | `python/cli.py design step2b-postplan --site gate-b` |
| `gate-a` | `python/cli.py design step2b-postplan --site discussion-round2` |
| `discussion-round2` | `python/cli.py design step2b-postplan --site discussion-round2` |

## Exit code contract

The wrapper also emits a whole-line `SETTLE_NEXT_ACTION=<value>` row on stdout before each deterministic dispatch exit. The row is required on stdout. A stderr-only action row does not satisfy the contract. The process rc remains a wrapper diagnostic and legacy process contract.

| `SETTLE_NEXT_ACTION` | Meaning |
| --- | --- |
| `gate-b-continue` | Gate B clean postplan result. Continue to loop-mode or legacy continuation handling. |
| `gate-a-return` | Gate A or discussion Round 2 clean postplan result. Return to Gate A. |
| `dedup-revise` | Dedup found a revise-again result. Revise `plan.txt` and retry settle. |
| `gate-b-validator-fail` | Gate B validator operator brake. |
| `gate-a-validator-fail` | Gate A or discussion Round 2 validator operator brake. |
| `pause` | Delegated pause-save terminal result. |
| `gate-b-hard-size` | Gate B hard plan-size brake. |
| `gate-a-hard-size` | Gate A or discussion Round 2 hard plan-size brake. |
| `gate-b-split` | Gate B split path. |
| `gate-a-split` | Gate A or discussion Round 2 split path. |

| Exit | Meaning |
| --- | --- |
| `0` | Settled. |
| `1` | Dedup revise-again result; caller revises `plan.txt` and retries settle. |
| `2` | Usage, invalid site, invalid tmpdir, or invalid Gate B round. |
| `3` | Fail-closed wrapper or dedup contract failure. |
| `10` | Validator operator brake. |
| `11` | Delegated pause-save terminal result. |
| `12` | Hard plan-size brake. |
| `13` | Split path. |

Unexpected child output that lacks an anchored whole-line `POSTPLAN_RC=` row is a contract error unless pause output or a fresh pause breadcrumb is present.

## Marker ownership

- Owns `$DESIGN_TMPDIR/.gate-b-postapply-ready-N` for Gate B.
- Owns `$DESIGN_TMPDIR/.step3-round-N.phase` for Gate B.
- `python/cli.py design step2b-postplan` owns `$DESIGN_TMPDIR/.completed/step-2b.5`.
- After successful post-rewrite dedup, the wrapper calls `python/cli.py design dialectic-clear-stale --design-tmpdir "$DESIGN_TMPDIR" --reason plan-rewrite`.
- After successful postplan with `POSTPLAN_RC=0`, the wrapper calls the same stale-clear verb again. Ordering is dedup → clear-stale → postplan → clear-stale.
- A non-zero `dialectic-clear-stale` exit is surfaced as a loud stderr warning but does not abort settle: the clarifier is fail-open and Gate C re-validates plan fingerprints before any debate.
- `python/cli.py design step2b-postplan` owns scout-manifest clearing for mapped non-initial sites.
- This wrapper does not write `plan-after-round-N.txt`.

## Gate B resume idempotency

An existing `.gate-b-postapply-ready-N` marker means dedup already succeeded for that rewrite. The wrapper skips dedup and re-enters postplan. It does not reapply reviewer findings during marker resume.

## Pause contract

Pause output or a fresh `.pause-save-complete` breadcrumb exits `11`. Pause never writes a clean Gate B `awaiting-continuation` phase. Both pre-postplan `.pause-requested` handling and postplan pause signals emit `SETTLE_NEXT_ACTION=pause` on stdout before exit `11`.

## Test seams

- `DESIGN_STEP35_DEDUP_PLAN_SH` overrides the default `python3 cli.py plan-review gate-b-dedup` call.
- `DESIGN_STEP35_POSTPLAN_SH` overrides the default argv-array `python/cli.py design step2b-postplan` call as a single executable stub path.

## Harness

Covered by `scripts/test-design-structure.sh`, `python/test_design_lifecycle.py`, and `skills/design/scripts/test-gate-b-apply-mode.sh`.

Compatibility grep note: historical launcher-fence rows still resolve through the launcher:

| Site | Historical launcher fence |
| --- | --- |
| `gate-a` | `design-step2b-postplan.sh --site discussion-round2` |
| `discussion-round2` | `design-step2b-postplan.sh --site discussion-round2` |
