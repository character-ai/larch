## Proposed Design Outline

### Goals
- Apply the `OPENAI_API_KEY` env-key auth preference to every uncovered `codex exec` path: `/research` lanes, `/research` validation lane, `lint-fix-loop.sh`, `run-negotiation-round.sh`.
- Add a lint/CI guard that flags any `codex exec` call site lacking shared auth wiring.

### Non-goals
- No refactor of the 5 covered sites (`launch-review.sh`, `launch-codex-ci.sh`, `launch-codex-implement.sh`, `check-reviewers.sh`, `review-and-fix.sh`).
- No Cursor-side auth changes (`lib-cursor-auth.sh` untouched).

### Approach sketch
- New shared launcher script under `scripts/` that wraps: ephemeral `CODEX_HOME` prep, `external_prepare_codex_auth`, `external_codex_auth_config_args`, then dispatch via `run-external-agent.sh`.
- Route the `/research` markdown fences (`research-phase.md`, `validation-phase.md`) and `lint-fix-loop.sh` `run_codex()` through the new launcher.
- Wire `run-negotiation-round.sh` (direct `codex exec`, event-stream + serial-lock shape) via the launcher if it fits, else inline per-site wiring.
- New lint script following the `lint-bare-grep-probe.sh` convention: scans shell + orchestrator markdown fences, pre-commit + Makefile target, inline `# lint-…: ok <reason>` suppressions.
- Update sibling `.md` contracts; extend `test-lint-fix-loop.sh`, `test-run-negotiation-round.sh`; add harnesses for the new launcher and lint.

### Surfaces in scope
- `scripts/` (new launcher + new lint + their `.md` siblings and `test-*.sh` harnesses)
- `scripts/lint-fix-loop.sh`, `scripts/run-negotiation-round.sh` (+ siblings)
- `skills/research/references/research-phase.md`, `skills/research/references/validation-phase.md`
- `Makefile`, pre-commit wiring, `docs/linting.md`

### Open questions
- Does `run-negotiation-round.sh` route through the new launcher or keep inline wiring (its `codex exec --json` event-stream contract differs from `run-external-agent.sh` dispatch)?
