## Proposed Design Outline

### Goals
- Part 1 (docs): document removing `apiKeyHelper` from `~/.claude/settings.json` and the four dual-auth aliases in the Claude section of `docs/installation-and-setup.md`.
- Part 2 (behavior): flip the default external tool to Codex-first for three roles — coder, CI fixer, merge-resolve fixer — in both Bash and the Python port.
- Keep Claude as the terminal fallback; keep explicit `--coder cursor` working.

### Non-goals
- No runtime/script/behavior change in Part 1 (docs only).
- Do not touch code-review / `review-and-fix` dispatchers (already Codex-first).
- Do not wire the Python port into the live path (parity-only; live until Phase 7).
- Do not auto-flip cursor-first surfaces outside the three roles — report them for your decision.

### Approach sketch
- Part 1: extend the Claude section of `docs/installation-and-setup.md` with the `apiKeyHelper` warning, the four aliases, and the credential-precedence mechanism.
- Part 2 Bash: flip the base `tiers=(cursor codex claude)` tuple in `run_ci_fix_vendor`, the `for tier in cursor codex claude` list in `run_recovery_waterfall`, and the waterfall order in `_phase_coder_implicit` (preserve the per-attempt start rotation).
- Part 2 Python: flip `config.FIXER_TIER_ORDER` (its consumers `ci_monitor._available_tiers()` / `rebase.py` derive from it).
- Update order-asserting tests; sync prose docs that state the old order.

### Surfaces in scope
- `docs/installation-and-setup.md`
- `scripts/implement-bootstrap.sh`, `scripts/ship-pr.sh`
- `python/config.py` (+ derived `ci_monitor.py`, `rebase.py`)
- Tests: `python/test_config.py`, `scripts/test-ship-pr.sh`, `scripts/test-implement-step2-routing.sh`
- Prose docs surfaced during design (e.g. `scripts/ship-pr.md`)

### Open questions
- Exact set of prose docs to sync, and any extra cursor-first defaults found — reported in the plan for your decision (Round 1 Decision 1).
