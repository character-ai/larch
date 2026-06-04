## Decision 1: Python interpreter floor (#2)
- **Question**: Enforce ≥3.12, or lower the documented floor to 3.11?
- **Resolution**: Lower the *runtime* floor to 3.11. Document 3.11 as the floor, add a CI version matrix (3.11 + 3.12) for py-lint/py-test, and audit `python/` for 3.11 compliance. The `/implement` selector should validate `python3 ≥ 3.11` instead of invoking bare `python3`. Dev/pre-commit tooling may stay on 3.12.
- **Source**: user

## Decision 2: O1 / #7 flush-churn scope
- **Question**: Minimal #7 convergence fix (defer O1), or re-architect post-PR flushes now?
- **Resolution**: Re-architect now. Eliminate divergence at the root: after PR creation, avoid creating a divergent commit (fast-forward post-PR flushes and/or defer final logs to post-merge). Still include the #7 convergence guard (flush once before CI / idempotent flush) and the #5 OID-poll safety net.
- **Source**: user

## Decision 3: Design tier
- **Question**: Keep SIMPLE or upgrade to HARD?
- **Resolution**: Keep SIMPLE. No sketches/dialectic/assessor; the full plan-review panel still runs. The user expanded scope on Decisions 1 and 2; the plan stays surgical per finding, but honors those broader choices.
- **Source**: user

## Decision 4: Floor-lowering surface (codebase finding)
- **Question**: Which files carry the ≥3.12 floor that Decision 1 must change?
- **Resolution**: Runtime ≥3.12 mentions: `python/README.md:3`, `docs/installation-and-setup.md:96`. Dev/pre-commit mention: `docs/installation-and-setup.md:297` (may stay 3.12). CI pins `python-version: "3.12"` in `.github/workflows/ci.yaml` (~6 `setup-python` steps; py-lint ~426, py-test ~442). No literal `3.12` mandate found in `AGENTS.md` (confirm in plan). `Makefile` `py-lint`/`py-test` invoke `python3`.
- **Source**: codebase

## Out of scope (boundaries from the issue)
- `#3446` (orchestrator consume-JSON routing), `#3448` (per-process counter resets), `#3449` (CI-fix `stage_and_push` force-push gate) are tracked separately — do NOT touch.
- `#3451`, `#3465` are absorbed/closed; their findings (#1, #2) are handled here.
