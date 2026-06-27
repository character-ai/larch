## Decision 1: Retired dialectic choreography — relocate vs delete
- **Question**: The ~200-line retired Step 2a.5 dialectic judge-panel choreography in `skills/shared/dialectic-protocol.md` is fully dead (references non-existent `skills/design/references/dialectic-execution.md`; active Gate C clarifier never uses it). Move to `dialectic-legacy.md` or delete?
- **Resolution**: Relocate to `skills/design/references/dialectic-legacy.md` (parked). Keep ballot grammar + disposition enum + thresholds + clarifier binding in the active `skills/shared/dialectic-protocol.md`. Do NOT delete.
- **Source**: user

## Decision 2: dialectic-resolutions.md Consumer Contract — safe to relocate (issue's Med risk)?
- **Question**: Does any live parser consume the structured Consumer Contract schema?
- **Resolution**: No. `python/design_lifecycle.py` treats `dialectic-resolutions.md` only as an empty placeholder (checks `.is_file()` + `st_size == 0`; no schema parse). The Consumer Contract section is legacy and moves to `dialectic-legacy.md` with the rest of the choreography. The empty-placeholder write/check in `design_lifecycle.py` is untouched (out of scope; it is Python, not a shared ref).
- **Source**: codebase

## Decision 3: --step-prefix encoding move — which files must repoint?
- **Question**: Moving the nested-only `--step-prefix` encoding section (progress-reporting.md ~130-182) out — what consumes it?
- **Resolution**: Only `skills/design/references/flags.md:88` cites progress-reporting.md for the encoding spec → repoint to the new sub-reference. The orchestrator SKILL.md citations ("Follow shared/progress-reporting.md rules": design/implement/research) are generic and stay valid (the common breadcrumb rules remain in progress-reporting.md). `--step-prefix` is still a live flag accepted by `/review` (`skills/review/SKILL.md`), so the encoding is relocated (not deleted), with a short pointer left in progress-reporting.md. New sub-reference: `skills/shared/step-prefix-encoding.md`.
- **Source**: codebase

## Decision 4: Scope boundary — skills/design/SKILL.md is OUT of scope
- **Question**: Should #5567 touch `skills/design/SKILL.md`?
- **Resolution**: No. None of the three changes require a SKILL.md edit (verified above). Sibling md-to-py-VII issues #5562 (SKILL.md Step 3 / Gate region) and #5401 (SKILL.md anti-halt preamble, IMPLEMENTING) own that file. Keeping #5567 to `skills/shared/` + 2 new files + the one-line `flags.md` repoint keeps the deliberate partition conflict-free. No blocked-by edge needed (file-disjoint from all in-flight issues).
- **Source**: codebase

## Decision 5: voting-protocol.md voter argv removal — what to cite?
- **Question**: Drop the Generic Cursor/Codex voter argv blocks (~120-181) and cite which verbs?
- **Resolution**: Drop the two inline voter argv contracts plus the wait/collect boilerplate; replace with a one-line citation to the owning Python dispatchers: `python/cli.py plan-review voter-dispatch` (/design plan review) and `python/cli.py agent dispatch-voters` (/review, /implement Step 5). Keep the protocol's thresholds, scoring, OOS, and scoreboard content. The duplicate judge-argv in `dialectic-protocol.md:199-247` follows the Decision-1 relocation into `dialectic-legacy.md`.
- **Source**: issue + codebase

## Scope summary (binding for Step 2b)
- **In scope**: `skills/shared/dialectic-protocol.md` (split: keep grammar/enum/thresholds, move legacy choreography out), `skills/shared/voting-protocol.md` (drop voter argv, cite verbs), `skills/shared/progress-reporting.md` (move step-prefix encoding, leave pointer), NEW `skills/design/references/dialectic-legacy.md`, NEW `skills/shared/step-prefix-encoding.md`, `skills/design/references/flags.md` (repoint one line).
- **Out of scope (must not touch)**: `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md`, any `python/` code, the active `dialectic-clarifier.md` binding (verify-only — it consumes kept content).
- **Hard constraints**: preserve `dialectic-clarifier.md:64` binding (kept grammar must remain in the active file); keep `--step-prefix` encoding reachable from `flags.md`; do not break the generic breadcrumb rules every standalone run loads; `make lint` clean.
