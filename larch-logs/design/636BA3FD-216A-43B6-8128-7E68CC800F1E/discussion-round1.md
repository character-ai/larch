## Decision 1: Scope of em-dash scrub
- **Question**: Should the fix extend to other SKILL.md lines or other Python files beyond the two surfaces named?
- **Resolution**: No. Scope is exactly `skills/design/SKILL.md` line 249 (the `⏩ 1d.7` breadcrumb) and `python/larch/design/design_step5b.py` lines 168-269 (warning/skip strings). Do not touch machine-parsed tokens, sentinels, or KEY=value grammars.
- **Source**: codebase / feature description

## Decision 2: Replacement punctuation
- **Question**: Which punctuation replaces em-dashes in each context?
- **Resolution**: Use a colon or comma as specified in the issue ("colon or comma form"). Preserve surrounding whitespace conventions. No other prose changes.
- **Source**: feature description
