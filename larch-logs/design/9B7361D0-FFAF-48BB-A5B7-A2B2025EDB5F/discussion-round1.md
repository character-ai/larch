## Decision 1: Scope — all 6 combined OOS items in one PR
- **Question**: Which of the 6 combined OOS items are in scope?
- **Resolution**: All 6 (doc/config/prose drift + 2 test-coverage gaps), per the combined-OOS intent (aggressive-mode single host: low-risk doc/config edits + additive tests). Item 4 is conditional — see Decision 2. No cross-item ordering dependency; each is an independent low-risk edit.
- **Source**: issue #4595 body

## Decision 2: Item 4 disposition — verified stale, KEEP and FIX (do not drop)
- **Question**: Does `skills/status/SKILL.md` DEGRADED copy already match the degraded-tools-gate both-down contract (issue says drop if it matches)?
- **Resolution**: Does NOT match — keep and fix. `degraded_tools_result` (python/agents.py) sets `both_down`; the both-down explanation is "Both external vendors are unavailable. This run cannot continue." `/implement` SKILL.md confirms both-down emits `DEGRADED_HARD_FAIL=true` and "stops in every mode" (no Claude-only fallback); one-down requires explicit operator confirmation to continue on a reduced panel with "no Claude padding". The status copy at line 29 ("will fall back to a reduced panel or Claude-only mode") is stale for both cases. Fix: rewrite the `DEGRADED=true` note to distinguish one-down (reduced panel, operator confirm) from both-down (hard fail, cannot continue).
- **Source**: codebase (python/agents.py `degraded_tools_result`; skills/implement/SKILL.md degraded gate; skills/status/SKILL.md:29)

## Decision 3: Hard constraints — surgical edits, preserve machine contracts
- **Question**: What must not break?
- **Resolution**: (a) Surgical edits only — change only the drifted prose/config/test lines; no adjacent reformatting. (b) `.claude/settings.json` stays valid JSON; new `Skill(bug)`/`Skill(larch:bug)` entries match existing allowlist style/placement. (c) Doc reframes (Items 1, 2, 4) must match the binding SKILL contracts exactly — verify `--emergency` audit-skip semantics and `run-statistics` emit sites before editing. (d) New test cases (Items 5, 6) follow each harness's existing case conventions and pass. (e) `make lint` (+ `make py-lint` / `make py-test` since Python test files change) must pass.
- **Source**: codebase + KARPATHY_CLAUDE.md (surgical changes)
