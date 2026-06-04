## Decision 1: Treatment of open soak-phase blockers (#3446, #3404, #3405, #3449)
- **Question**: The issue's "Sequencing / blockers" section says the python-default flip should land only after these four resolve and soak; all four are still OPEN. Should the plan gate on them?
- **Resolution**: Flip unconditionally. Treat the four blockers as out of scope for this plan; the default flip is designed to land independently of their status. Do NOT add blocker-gating preconditions to Acceptance.
- **Source**: user

## Decision 2: Selector-default regression pin
- **Question**: No CI pin asserts the ship-pr selector default today. Should the plan add a regression guard for the new python-default?
- **Resolution**: Add a selector-default pin — a small offline test asserting `skills/implement/SKILL.md` selector prose reads python-default and bash is the explicit opt-in. Satisfies #3446's requested pin.
- **Source**: user

## Decision 3: File surface that encodes the default (codebase-resolved)
- **Question**: Which surfaces encode the current bash default and must flip?
- **Resolution**: The default is resolved prompt-side (no `${LARCH_SHIP_PR_IMPL:-bash}` shell helper). Surfaces: `skills/implement/SKILL.md` ("Python driver selector" block, ~line 955), `AGENTS.md` (`python/` section), `docs/configuration-and-permissions.md` (`LARCH_SHIP_PR_IMPL` section), `python/README.md` (Phase 7 line). `SECURITY.md` references the env var only as a descriptive label and gets a light touch if framing becomes misleading. `scripts/ship-pr.sh` and the bash contract prose stay byte-stable — bash remains opt-in, never removed.
- **Source**: codebase

## Decision 4: Bash path preservation (hard constraint)
- **Question**: Must the legacy bash path keep working?
- **Resolution**: Yes. With `LARCH_SHIP_PR_IMPL=bash`, `/implement` Step 8+ must invoke `scripts/ship-pr.sh` byte-for-byte as today. Bash removal stays deferred to a later cutover step.
- **Source**: issue (Acceptance)
