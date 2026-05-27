## Proposed Design Outline

### Goals
- Add opt-in `--emergency` flag to `/implement` that bypasses three Preflight gates (plan-block presence, plan-adequacy audit, clarify-state pending).
- Preserve current default behavior exactly: all Preflight gates fire when `--emergency` is absent.
- Persist the flag through `run-params.json` (or implement equivalent) and surface it in audit trails (final summary block + tracking-issue `larch:metadata`).

### Non-goals
- Bypassing the semantic materiality / stale-plan notice (still fires under `--emergency`).
- Skipping any post-Preflight step; Step 0+ implementation flow is unchanged.
- Auto-detecting "emergency" conditions or making `--emergency` default-on.
- Allowing `--emergency` + `--draft` (rejected as mutually exclusive).

### Approach sketch
- Parse `--emergency` in `/implement` argv (`skills/implement/SKILL.md` Step 1) with default `false`; add mutual-exclusion check against `--draft`.
- In Preflight: when `emergency_requested=true`, downgrade `BLOCK_PRESENT=false`, `AUDIT=refuse`, and `clarify-state` pending from hard refusals (exit 2/3) to "warn and proceed"; keep semantic materiality / stale-plan notice firing as a hard gate.
- When no `larch:plan` block exists under `--emergency`, the plan-materialization path (Step 0 / `implement-bootstrap.sh`) falls back to the raw issue body as the plan source.
- Emit a loud bold chat warning AND append a structured entry to `execution-issues.md` (or the `/implement` Tool Failures / Warnings log) each time `--emergency` is invoked and at least one bypass actually triggers.
- Persist `emergency_requested` in `run-params.json`; thread it through `larch:metadata` and the final summary block via existing patterns.

### Surfaces in scope
- `skills/implement/SKILL.md` — argv table, Preflight branching, mutual-exclusion guard, NEVER list / anti-pattern entry as needed.
- `skills/implement/references/` — Preflight-related reference files that describe gating semantics.
- `scripts/persist-implement-run-flags.sh` and/or `scripts/implement-admission.sh` / `scripts/plan-block-read.sh` consumers, depending on where the bypass branch lives.
- `skills/implement/scripts/implement-bootstrap.sh` — plan materialization fallback to raw issue body when `BLOCK_PRESENT=false` and `--emergency` is set.
- Documentation: `README.md`, `AGENTS.md`, `docs/` files that describe `/implement` Preflight.

### Open questions
- None.
