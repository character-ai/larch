# Settle-wrapper dispatch

**Consumer**: `/design` Gate B post-apply, Step 1e Gate A re-entry optional-trailer guard, and Round 2 post-plan discussion revision after `design-step35-settle.sh` returns.

**Contract**: single canonical prose table for orchestrator dispatch on `design-step35-settle.sh` machine actions. This file documents prompt-side branching only; it does not change wrapper behavior, Python-owned rc values, postplan semantics, or settle retry mechanics.

**When to load**: immediately before any orchestrator branches on `design-step35-settle.sh` output at Gate B post-apply, Gate A re-entry trailer guard, or discussion-round2 plan revision after the settle wrapper returns.

---

## Dispatch key

Primary key: branch on the whole-line `SETTLE_NEXT_ACTION=...` row from `design-step35-settle.sh` stdout.

Fallback key: when the action row is missing, branch on the `design-step35-settle.sh` process exit status (`$?` after the launcher fence). Do not branch on raw `POSTPLAN_RC=` stdout rows parsed from postplan output.

If `SETTLE_NEXT_ACTION` and wrapper rc disagree, stop for repair rather than silently choosing one.

The wrapper maps internal postplan output to process exits:

- `POSTPLAN_RC=0` → exit `0`.
- `POSTPLAN_RC=10|12|13` → exit `10|12|13`.
- `POSTPLAN_RC=11` or pause signals → exit `11`.
- Post-rewrite dedup revision needed → exit `1`. There is no `POSTPLAN_RC=1` on the postplan path.
- Unexpected `POSTPLAN_RC` values → exit `3`.

## Branch on SETTLE_NEXT_ACTION

| Action | Dispatch |
|---|---|
| `gate-b-continue` | Continue to loop-mode or legacy continuation handling. |
| `gate-a-return` | Return to Gate A. |
| `dedup-revise` | Revise duplicate/trailer cleanup, rewrite `plan.txt`, and retry settle. |
| `gate-b-validator-fail` | Read allowlisted validator keys from `$DESIGN_TMPDIR/.design-postplan-emit-result.env`, then execute **### Plan command validator failure (shared)** with site `design Step 3.5 / Gate B`. Fix-and-retry re-enters settle with `--round-num` when bound. |
| `gate-a-validator-fail` | Execute **### Plan command validator failure (shared)** with site `design discussion-round2`. Fix-and-retry re-enters settle. |
| `pause` | Stop at the delegated pause boundary. |
| `gate-b-hard-size` | Run the existing Gate B hard plan-size prompt. Override uses `python/cli.py design step2b-postplan --write-completion-only` before continuing. |
| `gate-a-hard-size` | Use the retained Step 2b.5 behavior. |
| `gate-b-split` | Run Split-path only. Non-exiting Split returns use `python/cli.py design step2b-postplan --write-completion-only` before continuing. |
| `gate-a-split` | Run Split-path per `decompose-panel.md`. |

## Fallback: branch on wrapper rc

| Wrapper rc | Dispatch |
|---|---|
| `0` | Use the site variant table below. Gate B continues to loop-mode or legacy continuation handling. Gate A / discussion-round2 returns to Gate A. |
| `1` | Revise duplicate/trailer cleanup, rewrite `plan.txt`, and retry the settle wrapper. This is wrapper exit `1` from post-rewrite dedup revision-needed, not `POSTPLAN_RC=1`. |
| `10` | Read allowlisted validator keys from `$DESIGN_TMPDIR/.design-postplan-emit-result.env` where the site requires it, then execute **### Plan command validator failure (shared)** with the site context in the variant table. |
| `11` | Stop at the delegated pause boundary. |
| `12` | Use the site variant table below. |
| `13` | Use the site variant table below. |
| Other non-zero | Stop for operator repair. |

## Site variants for fallback rc dispatch

| Site variant | Wrapper call | rc `0` | rc `10` context and retry | rc `12` | rc `13` |
|---|---|---|---|---|---|
| **Gate B** | `design-step35-settle.sh --site gate-b` | Continue to loop-mode or legacy continuation handling. | Use `design Step 3.5 / Gate B`. Fix-and-retry re-enters the settle wrapper, with `--round-num` when bound. | Run the existing Gate B hard plan-size prompt. Override uses `python/cli.py design step2b-postplan --write-completion-only` before continuing. | Run Split-path only. Non-exiting Split returns use `python/cli.py design step2b-postplan --write-completion-only` before continuing. |
| **Gate A / discussion-round2** | `design-step35-settle.sh --site gate-a` or `design-step35-settle.sh --site discussion-round2` | Return to Gate A. | Use `design discussion-round2`. | Use the retained Step 2b.5 behavior. | Run Split-path per `decompose-panel.md`. |

## Compatibility note

`design-step35-settle.sh` still maps `gate-a` and `discussion-round2` to `python/cli.py design step2b-postplan --site discussion-round2` internally.
