# ship-pr Python foundation (Phase 1)

Flat `python/` tree for the in-progress `scripts/ship-pr.sh` → Python rework. **Runtime
modules import stdlib only** (Python ≥ 3.12). Linters and pytest are dev/CI-only and are never
imported by runtime code.

## Layout

- `config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `proc.py` — injectable subprocess seam
- `errors.py`, `outcomes.py`, `run_context.py` — typed errors and run context
- `logging_util.py` — breadcrumbs + JSONL journal (observability only)
- `redact.py`, `retry.py` — ports of `redact-secrets.sh` / `lib-net.sh`
- `git.py`, `gh.py`, `agents.py` — typed `git` / `gh` / fixer launcher surfaces
- `test_<module>.py` — colocated unit tests; `test_stdlib_only.py` enforces stdlib-only imports

## Dependencies

| File | Purpose |
|------|---------|
| `requirements-dev.txt` | ruff, pylint, pyright (Python Lint CI / `make py-lint`) |
| `requirements-test.txt` | pytest only (Python Tests CI / `make py-test`; no Node) |

## Run locally

From the repository root (after `pip install -r python/requirements-dev.txt` and/or
`python/requirements-test.txt`):

```bash
make py-lint   # cd python && ruff check . && pylint . && pyright
make py-test   # cd python && pytest
```

The live `/implement` path still uses bash until Phase 7 (`LARCH_SHIP_PR_IMPL=python`).
