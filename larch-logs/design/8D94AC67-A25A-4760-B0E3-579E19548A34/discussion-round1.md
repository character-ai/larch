## Decision 1: G-Cfg-1 marking
- **Question**: G-Cfg-1 is only partially mechanized (env-var half only). Mark with a partial-coverage note in the Mechanized line, or leave unmarked?
- **Resolution**: Mark G-Cfg-1 with a Mechanized line that names the lint and notes the partial coverage scope.
- **Source**: user

## Decision 2: G-Py-11 status
- **Question**: Mark G-Py-11 now?
- **Resolution**: Do NOT mark G-Py-11. The companion suppression-reason lint issue has not landed. Leave G-Py-11 unchanged.
- **Source**: codebase (no suppression-reason lint exists in python/larch/lint/)

## Decision 3: docs/linting.md update
- **Question**: Is the marker load-bearing for lint discovery, requiring docs/linting.md update?
- **Resolution**: The marker is a prose annotation in ARCHITECTURAL_GUIDELINES.md that drives parser behavior; it is not a lint target name. The issue says "document the marker if the designer makes it load-bearing for lint discovery" - since it is not a lint-discovery mechanism (it does not drive make or cli.py), a docs/linting.md update is not required unless the plan exposes a new make target or CLI verb.
- **Source**: codebase
