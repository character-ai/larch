## Proposed Design Outline

### Goals
- Move all six `scripts/*.py` utilities into `python/` behind `cli.py` verbs.
- Keep behavior identical; repoint every caller; leave no stale references.
- Drop the repo's last `yaml` import by de-yaml'ing check-topology.

### Non-goals
- No adjacent refactors, behavior changes, or new features.
- No new test coverage for the three previously-untested utilities.
- No in-process rewrite of the `run_logs.py` render-transcript subprocess boundary; repoint only.

### Approach sketch
- Each script becomes a `python/<module>.py` (flat layout) plus a `_REGISTRY` verb in `cli.py`.
- Three linters join the existing `lint` domain: `lint literal-counts`, `lint no-raw-stderr-after-quiet-init`, `lint topology-rule-paths`.
- De-yaml check-topology: stdlib parse of the `paths:` quoted block list; the existing harness is the parity gate.
- Port the three linter `test-*.sh` to colocated `python/test_lint_*.py`; delete each bash harness plus `.md`.
- Record every deleted path in `python/migrated-scripts.tsv` with `#4974`; `make lint-retired-scripts` stays clean.

### Surfaces in scope
- The six `scripts/*.py` files plus their `.md` siblings and the three linter `test-*.sh` harnesses.
- `python/cli.py`, the new `python/` modules and tests, `python/run_logs.py`, `python/migrated-scripts.tsv`.
- Callers: `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/ci.yaml`, `agent-lint.toml`, `docs/linting.md`, `docs/run-logs.md`, `python/README.md`.

### Open questions
- Verb domain for the three non-lint utilities (render-session-transcript, cleanup-implement-logs, retro-v3-sweep): pick from existing `cli.py` domains during drafting.
