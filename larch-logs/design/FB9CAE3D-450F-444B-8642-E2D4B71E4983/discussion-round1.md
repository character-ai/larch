## Decision 1: Flow scope
- **Question**: Should dependency management apply to both `--oos` and standard flows?
- **Resolution**: Primary target is `--oos` only; standard flow deferred per issue wording "optionally the standard flow".
- **Source**: issue body

## Decision 2: Dependency direction coverage
- **Question**: Should we inherit both `blocked_by` and `blocking` edges from source issues?
- **Resolution**: Yes, both directions. Add `issue_blocking_read` to `gh.py` (mirrors `issue_blocked_by_read`) to fetch what a source issue blocks.
- **Source**: codebase + issue body

## Decision 3: Audit phase mechanism
- **Question**: Should the audit phase use Python or skill-level LLM reasoning?
- **Resolution**: Tier-1 (prose mentions via `blocker.parse_prose_blockers`) is Python-driven; Tier-2 (semantic reasoning over open-issue pairs) runs at skill-level inside SKILL.md.
- **Source**: codebase (blocker.py has parse_prose_blockers) + issue body

2 decisions resolved.
