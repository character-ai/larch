## Proposed Design Outline

### Goals
- After `--oos` combination, every combined issue inherits all blocked-by and blocking edges from its source issues.
- After combination, the skill detects and wires dependencies between combined issues and existing open issues.
- No non-OOS issue is blocked by a new OOS issue without explicit operator approval.

### Non-goals
- Standard (non-`--oos`) flow dependency management.
- Full LLM-based Tier-2 audit over all open-issue pairs (Tier-1 prose scanning is included; Tier-2 is best-effort via skill reasoning).
- Retroactive dependency audits of previously combined issues.

### Approach sketch
- Add `gh.issue_blocking_read` to `gh.py` (mirror of `issue_blocked_by_read` for the `blocking` endpoint).
- Add `combine-issues fetch-deps` verb to `combine_issues.py`: fetches blocked-by and blocking for a list of issues, outputs JSON.
- Register new verb in `cli.py`.
- Add SKILL.md steps oos-6 (inherit edges), oos-7 (audit open issues), oos-8 (exception gate), oos-9 (summary) after oos-5.
- Emit deduplication so the same edge is not registered twice.

### Surfaces in scope
- `python/gh.py`
- `python/combine_issues.py`
- `python/cli.py`
- `python/test_combine_issues.py`
- `.claude/skills/combine-issues/SKILL.md`

### Open questions
- None.
