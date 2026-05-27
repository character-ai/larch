## Step 1c Decisions (scope/UX prompts)

### Decision 1c.1: Worse-verdict UX
- **Question**: What happens when the 3-assessor panel votes WORSE majority?
- **Resolution**: 2 options — Continue / Stop. Stop = exit /design without finalizing. No automated rollback machinery.
- **Source**: user

### Decision 1c.2: Tier scope
- **Question**: Which /design tiers fire the assessor stage?
- **Resolution**: HARD only (workflow_path=HARD in run-params.json). Re-read per invocation so mid-flow tier drift is handled.
- **Source**: user

### Decision 1c.3: Today's call site
- **Question**: Where does the assessor actually fire?
- **Resolution**: Gate C(c) "Re-run review panel" re-entry today (round ≥ 2). Architect a clean call-site (new Step 3.6 between Gate B settled and Step 3b, file-only state) so #2871's future auto-loop can reuse without redesign.
- **Source**: user

### Decision 1c.4: Assessor panel composition
- **Question**: Which 3 models compose the assessor panel?
- **Resolution**: Claude + Cursor + Codex (cross-model). Reuses launch-claude-review.sh + dispatch-with-waterfall.sh primitives. Same composition as dialectic judges.
- **Source**: user

---

## Step 1d Decisions (Round 1 scope)

### Decision 1d.1: Degraded-panel fallback rule
- **Question**: When fewer than 3 assessors return parseable verdicts, what's the default?
- **Resolution**: WORSE iff *all* successful assessors agree WORSE — i.e., unanimous WORSE among the available 1 or 2 voters. With 3 successful voters, the original strict majority rule applies (`WORSE > BETTER`). With 0 successful voters: NOT_WORSE. Concretely:
  - 3 successful: WORSE iff `worse_count > better_count` (strict majority).
  - 2 successful: WORSE iff both said WORSE (unanimous).
  - 1 successful: WORSE iff it said WORSE.
  - 0 successful: NOT_WORSE (default-open on full panel failure).
- **Source**: user

### Decision 1d.2: Verdict persistence (storage + log flush)
- **Question**: Where should the assessor verdict + brief justifications live for posterity?
- **Resolution**: Per-round verdict file under `$DESIGN_TMPDIR` with compact contents. Format: literally `NOT_WORSE` for the not-worse case; for the worse case, `WORSE: <brief justification — a few sentences>`. File is flushed with the design log bundle (`design-log-publish.sh` includes `$DESIGN_TMPDIR/**` so the file appears under `larch-logs/design/<RUN_ID>/`). Do NOT surface in the `larch:final-summary` structured block; the design log is the durable record.
- **Source**: user

---

## Scope boundaries (consolidated)

- **In scope**: HARD-only assessor stage, fires at Gate C(c) re-entry (round ≥ 2), 3-assessor cross-model panel, 2-option Continue/Stop UX on WORSE-majority, per-round verdict file, design-log flush, #2871-compatible seam.
- **Out of scope**:
  - Rollback machinery (no rollback-plan-round.sh, no rollback-in-progress sentinel, no cursor decrement on rollback).
  - 3-option Abort path (finalize previous plan via Gate C).
  - Automatic multi-round loop (deferred to #2871; assessor is operator-driven via Gate C(c) today).
  - Convergence gates / max-round caps.
  - Surfacing verdict in `larch:final-summary` block or on the GitHub issue body/comment.
  - SIMPLE / TRIVIAL tier instrumentation.

## Hard constraints

- Re-read `workflow_path` from `run-params.json` per invocation (no in-memory caching). Skip silently when not HARD.
- Round 1 skip is silent (no previous plan to compare). No verdict file written for round 1.
- Per `dispatch-plan-voters.sh` integrity: do NOT extend it with a `--role assessor` mode. Build a sibling dispatcher.
- Output grammar (`ASSESSMENT: BETTER|WORSE|TIE`) must NOT collide with the `FINDING_N:` / `OOS_N:` voter grammar.
- Per `BASH_AUTHORING.md §4`: long-running launches require background+breadcrumb-monitor pair.
- All new scripts must have `.md` sibling documentation per `script-md-siblings` rule.
- Plan must respect `KARPATHY_CLAUDE.md §2` (Simplicity First) — drop the rollback/abort surface area from the prior plan since the user picked Continue/Stop.
