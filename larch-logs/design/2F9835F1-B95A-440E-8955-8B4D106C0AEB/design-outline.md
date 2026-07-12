## Proposed Design Outline

### Goals
- Add `--sweep` / `--sweep-max N` flag to `/analyze-bugs` to find unfiled bugs in recent main merges.
- Run adversarial finder + refuter agents per merge, emit surviving findings in a new report section, and gate filing behind the existing approval prompt.
- Persist sweep state fail-closed so partial runs do not corrupt progress.

### Non-goals
- No auto-filing without explicit approval gate.
- No branches other than `origin/main`; no runtime execution checks.
- No blast-radius scan from the sibling verdict-depth issue (minimal inline consumer scan acceptable).

### Approach sketch
- New `sweep_state` read/write helpers in `analyze_bugs.py` alongside `_cache_root`; state file at `<cache_root>/sweep-state.json`.
- New `sweep_main` / `sweep_enumeration` / `sweep_run` functions in `analyze_bugs.py`; new `("analyze-bugs", "sweep")` CLI verb in `python/larch/cli.py`.
- New agent `.claude/agents/sweep-bug-finder.md` (sonnet, Read/Grep/Glob); adversarial prompt returns strict JSONL.
- SKILL.md gains `--sweep` / `--sweep-max` flag docs, new sweep stages (Stage S0 state-load, S1 enumeration, S2 finder+refuter dispatch, S3 sweep report), and expectation-setting paragraph.
- Tests in `tests/issue/test_analyze_bugs.py` cover enumeration exclusion rules, sweep-state round-trip, fail-closed partial-run, JSONL parse, prioritization, cap/skip-count.

### Surfaces in scope
- `python/larch/issue/analyze_bugs.py`
- `python/larch/cli.py` (new verb)
- `.claude/agents/sweep-bug-finder.md` (new agent)
- `.claude/skills/analyze-bugs/SKILL.md`
- `python/tests/issue/test_analyze_bugs.py`

### Open questions
- None.
