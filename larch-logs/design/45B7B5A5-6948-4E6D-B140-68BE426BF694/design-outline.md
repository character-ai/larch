## Proposed Design Outline

### Goals
- Add premature-notification recovery carve-out to `skills/shared/orchestrator-never.md` NEVER #3.
- Fix stale NEVER cross-reference in `AGENTS.md` (NEVER #9 to NEVER #8).
- Document `submodule-restricted` failure class in `skills/implement/references/stall-recovery.md` Step 18a.
- Fix `research_eval.py` to accept `blocking` severity; add JSONL and TSV test cases.
- Replace `_check_feasibility` heuristic in `rebalance.py` with direct post-pack spread check.

### Non-goals
- Do not modify reviewer agent prompts or `reviewer-templates.md`.
- Do not change any runtime script behavior; these are doc and validation fixes only.
- Do not touch `SKILL.md` NEVER rules or `stall-recovery-report.sh` logic.

### Approach sketch
- Extend NEVER #3 in `orchestrator-never.md` with a single carve-out sentence for the sanctioned one-shot until-waiter re-launch; clarify it does not conflict with NEVER #4.
- Edit the AGENTS.md Monitor/polling bullet: change "NEVER #9" to "NEVER #8".
- Add `submodule-restricted` entry beside the `protected-path` bullet in `stall-recovery.md` Step 18a, using the warning text from SKILL.md (RESUME_HINT=none; no inline recovery).
- Add `"blocking"` to `_ALLOWED_SEVERITIES` in `python/research_eval.py`; add two new test cases covering JSONL and TSV `blocking` severity.
- Move the feasibility call in `rebalance.py` to after `pack()`; replace the heuristic with a direct spread computation from packed shard totals.

### Surfaces in scope
- `skills/shared/orchestrator-never.md`
- `AGENTS.md`
- `skills/implement/references/stall-recovery.md`
- `python/research_eval.py`
- `python/test_research_eval.py`
- `.claude/skills/rebalance-test-harnesses/scripts/rebalance.py`

### Open questions
- None.
