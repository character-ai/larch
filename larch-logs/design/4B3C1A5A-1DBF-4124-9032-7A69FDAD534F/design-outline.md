## Proposed Design Outline

### Goals
- Port ~20 bash scripts across release, audit-runs, combine-issues, and analyze-issues to Python stdlib modules with `cli.py` verb registration.
- Hard cutover all callers (SKILL.md files, shipped scripts, test harnesses); delete all retired bash + `.md` siblings; append to `migrated-scripts.tsv`.
- Replace bash harnesses with representative pytest coverage; make lint + py-lint + py-test green.

### Non-goals
- Porting runtime Claude Code hooks (hooks stay bash, separate track).
- Changing classification logic or behavior in `classify-bump.md` (doc stays authoritative).
- Full 1:1 line-count port of the 3111-line `test-audit-runs.sh` harness (representative coverage only).

### Approach sketch
- Add `python/release_prepare.py`, `python/release_finish.py`, `python/promote_release.py`; add CLI verbs to `version_bump.py` for `classify-bump` and `read-plugin-version`.
- Add `python/audit_runs.py`, `python/combine_issues.py`; move `analyze.py`/`render-chart.py` from `.claude/skills/analyze-issues/scripts/` to `python/`; add `python/analyze_issues.py` as orchestrator.
- Register all new (domain, verb) pairs in `cli.py`; update SKILL.md files and any other callers to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>`.
- Delete retired bash + harness + `.md` siblings; add entries to `migrated-scripts.tsv`; run stale-ref sweep.

### Surfaces in scope
- `python/` — new/modified modules, `cli.py` registry, pytest files
- `.claude/skills/release/scripts/` — retire bash scripts + harnesses; SKILL.md callsite updates
- `.claude/skills/audit-runs/scripts/` — retire bash scripts + harnesses; SKILL.md callsite updates
- `.claude/skills/combine-issues/scripts/` — retire `apply-combination.sh`, `fetch-combinable-issues.sh`
- `.claude/skills/analyze-issues/scripts/` — move `analyze.py`/`render-chart.py` to `python/`; retire bash scripts
- `scripts/` — retire `promote-release.sh`, `verify-main.sh`, `read-plugin-version.sh`
- `skills/implement/scripts/refresh-execution-issues.sh`, `scripts/implement-finalize.sh`, `skills/status/scripts/status.sh` — cutover to `python3 cli.py` calls
- `python/migrated-scripts.tsv` — append retired paths

### Open questions
- Exact CLI domain/verb names for audit-runs, combine-issues, and analyze-issues (determined during plan drafting).
