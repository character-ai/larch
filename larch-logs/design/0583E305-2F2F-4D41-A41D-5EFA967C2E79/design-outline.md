## Proposed Design Outline

### Goals
- Create `python/rendering.py` porting 18 bash scripts: all `render-*`, `sanitize-mermaid-fragment`, `upsert-diagrams-comment`, all `generate-*`, and `check-generators`.
- Register ~20 new CLI verbs in `python/cli.py` (`render`, `generate`, `mermaid`, `diagrams` domains); cut all call-sites to direct `python3 cli.py` invocations.
- pytest replaces all bash harnesses; `generate-*` verbs produce byte-identical artifacts (SHA-256 pinned in tests).

### Non-goals
- Changing generated artifact content or format.
- Refactoring caller skill scripts beyond the one-line call-site repoint.
- Porting sourced-only bash libs (`lib-quiet.sh`, `lib-untrusted-block.sh`, etc.).
- Changing `generators.tsv` column-2 output-path semantics.

### Approach sketch
- Port all 18 absorbed scripts into `python/rendering.py` as importable functions with `*_main(argv)` CLI entry points.
- Update `scripts/generators.tsv` to use Python verb names (column 1 becomes `generate <verb>`); update `check-generators.sh` walker to Python; CI step changes to `python3 python/cli.py generate check`.
- Repoint ~10 calling scripts in `skills/review/`, `skills/research/`, `skills/design/scripts/`, `skills/implement/scripts/` to `python3 cli.py` invocations.
- Delete all 18 bash scripts, their `.md` siblings, and ~10 bash test harnesses; append to `python/migrated-scripts.tsv`.

### Surfaces in scope
- `python/rendering.py` (NEW)
- `python/test_rendering.py` (NEW)
- `python/cli.py` (UPDATED)
- `python/migrated-scripts.tsv` (UPDATED)
- `scripts/generators.tsv` (UPDATED)
- `.github/workflows/ci.yaml` (UPDATED)
- `skills/review/scripts/dispatch-panel.sh`, `scripts/launch-review.sh`, `scripts/launch-claude-review.sh` (UPDATED)
- `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/design/scripts/design-publish.sh` (UPDATED)
- `skills/implement/scripts/step-7a.sh` (UPDATED)
- `skills/research/scripts/` callers (UPDATED)
- 18 bash scripts + `.md` siblings + bash harnesses (DELETED)

### Open questions
- None.
