## Decision 1: Dependencies are all done
- **Question**: Are B4, C4a, and B6 dependencies merged and available?
- **Resolution**: B4 (#3673 `agents.py`), C4a (#3683 `bootstrap.py`), B6 (#3675 `rendering.py`) are all CLOSED/DONE.
- **Source**: codebase

## Decision 2: lib-implement-round-cap.sh scope
- **Question**: Should lib-implement-round-cap.sh be ported? It is listed in the issue but does not exist in the repo.
- **Resolution**: File does not exist; resume-counter logic is already inlined in step2-implement.sh. Skip it; add to migrated-scripts.tsv if it was ever tracked.
- **Source**: codebase

## Decision 3: Launcher call-site in agents.py
- **Question**: Do the implement launchers go into agents.py (alongside CI launchers) or a new module?
- **Resolution**: B4 note says launchers "stay with C4b but reuse this framework." Given the pattern (all launcher mains in agents.py), implement launcher mains belong in agents.py. Dispatch + recovery + commit logic goes in a new python/implement_dispatch.py.
- **Source**: codebase
