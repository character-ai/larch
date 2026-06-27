# Settle-wrapper dispatch

**Consumer**: `/design` Gate B post-apply, Step 1e Gate A re-entry optional-trailer guard, and Round 2 post-plan discussion revision after `design-step35-settle.sh` returns.

**Contract**: single canonical prose table for orchestrator dispatch on `design-step35-settle.sh` machine actions. This file documents prompt-side branching only; it does not change wrapper behavior, Python-owned rc values, postplan semantics, or settle retry mechanics.

**When to load**: immediately before any orchestrator branches on `design-step35-settle.sh` output at Gate B post-apply, Gate A re-entry trailer guard, or discussion-round2 plan revision after the settle wrapper returns.

---

## Dispatch key

Primary key: branch on the whole-line `SETTLE_NEXT_ACTION=...` row from `design-step35-settle.sh` stdout.

If the `SETTLE_NEXT_ACTION` action row is absent, stop for operator repair. Do not route from the wrapper rc when the action row is missing.

If `SETTLE_NEXT_ACTION` and wrapper rc disagree, stop for repair rather than silently choosing one.

Wrapper exit codes remain diagnostics and legacy process contracts only. The orchestrator must not use them as fallback routing authority.

Diagnostics:

- `POSTPLAN_RC=0` maps to exit `0`.
- `POSTPLAN_RC=10|12|13` maps to exit `10|12|13`.
- `POSTPLAN_RC=11` or pause signals map to exit `11`.
- Post-rewrite dedup revision needed maps to exit `1`. There is no `POSTPLAN_RC=1` on the postplan path.
- Unexpected `POSTPLAN_RC` values map to exit `3`.

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
| `gate-a-hard-size` | **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/step2b5-rc-handling.md` immediately before dispatch. Use the retained Step 2b.5 behavior. |
| `gate-b-split` | Run Split-path only. Non-exiting Split returns use `python/cli.py design step2b-postplan --write-completion-only` before continuing. |
| `gate-a-split` | Run Split-path per `decompose-panel.md`. |

## Compatibility note

`design-step35-settle.sh` still maps `gate-a` and `discussion-round2` to `python/cli.py design step2b-postplan --site discussion-round2` internally.
