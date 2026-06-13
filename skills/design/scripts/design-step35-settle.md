# design-step35-settle.sh

## Purpose

Shared post-rewrite settle wrapper for Gate B, Gate A after-discussion rewrites, and discussion Round 2. It runs the mechanical post-rewrite dedup, delegates postplan to `design-step2b-postplan.sh`, and centralizes the exit-code and marker contract that prompt-side prose previously respelled.

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
| `--claude-pid PID` | launcher-supplied | Forwarded to `design-step2b-postplan.sh`. |
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
| `gate-b` | `design-step2b-postplan.sh --site gate-b` |
| `gate-a` | `design-step2b-postplan.sh --site discussion-round2` |
| `discussion-round2` | `design-step2b-postplan.sh --site discussion-round2` |

## Exit code contract

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
- `design-step2b-postplan.sh` owns `$DESIGN_TMPDIR/.completed/step-2b.5`.
- `design-step2b-postplan.sh` owns scout-manifest clearing for mapped non-initial sites.
- This wrapper does not write `plan-after-round-N.txt`.

## Gate B resume idempotency

An existing `.gate-b-postapply-ready-N` marker means dedup already succeeded for that rewrite. The wrapper skips dedup and re-enters postplan. It does not reapply reviewer findings during marker resume.

## Pause contract

Pause output or a fresh `.pause-save-complete` breadcrumb exits `11`. Pause never writes a clean Gate B `awaiting-continuation` phase.

## Test seams

- `DESIGN_STEP35_DEDUP_PLAN_SH` overrides the default `python3 cli.py plan-review gate-b-dedup` call.
- `DESIGN_STEP35_POSTPLAN_SH` overrides the default `skills/design/scripts/design-step2b-postplan.sh`.

## Harness

Covered by `scripts/test-design-structure.sh` and `skills/design/scripts/test-gate-b-apply-mode.sh`.
