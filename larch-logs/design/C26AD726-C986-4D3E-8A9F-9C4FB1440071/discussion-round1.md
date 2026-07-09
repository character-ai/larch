## Decision 1: Section E dual-use terminal-sentinel disposition
- **Question**: How should the removal PR treat the 11 dual-use terminal sentinels (Section E) that still have live non-guard routing consumers in /design and /implement?
- **Resolution**: Full, per the issue. Repoint each consumer to the bgjob result env (`$TMPDIR/bgjob/<step>.result.env`) and delete the sentinel wherever a consumer allows; KEEP a sentinel only when a consumer genuinely cannot be repointed. Record an explicit KEEP/REPOINT/DELETE decision per row with consumer evidence (acceptance criterion 5). Maximal cleanup; accept the larger diff (may trigger the plan-size split).
- **Source**: user

## Decision 2: Hard constraint — no bgjob behavior changes
- **Question**: What must this removal PR NOT change?
- **Resolution**: Removals, doc replacements, and sentinel repoints only. No behavior changes to the bgjob machinery itself (acceptance criterion 7). The retained coverage lint (`lint_bg_wait_coverage.py`), the generic repeated-Read branch of `hook-anti-read-poll.sh`, and the replacement NEVER rule in `orchestrator-never.md` must survive.
- **Source**: codebase
