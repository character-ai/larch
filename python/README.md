# ship-pr Python foundation (Phase 1–2)

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
- `bump_worktree.py` — shared drop/worktree helpers (`DropResult`, porcelain, sorted diff)
- `version_bump.py`, `changelog.py` — Phase 2 ports of bump-version / CHANGELOG scripts
  (not wired into the live `/implement` path until Phase 7). `commit_changelog` is Markdown-only
  today; RST changelog commit is deferred until Phase 7 (no bash `commit-changelog` counterpart for RST).
- `checks.py` — local relevant-checks runner and lint-fix loop (Phase 4)
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

`make lint` does not invoke `py-lint` or `py-test`; use those targets explicitly or rely on
CI `python-lint` / `python-tests` jobs. Per-job CI replay (`make py-lint` / `make py-test` from
ship-pr failed-job tables) needs the same toolchain as CI: `pip install -r python/requirements-dev.txt`
for lint (including **Node** on PATH for pyright) and `pip install -r python/requirements-test.txt`
for tests.

Twin-repo parity tests that source `scripts/lib-changelog.sh` require **bash** and **gawk** on
PATH (the bash helpers use `gawk` for RST changelog transforms). CI `python-tests` installs `gawk`;
local runs without it skip those cases via `pytest.mark.skipif`.

The live `/implement` path still uses bash until Phase 7 (`LARCH_SHIP_PR_IMPL=python`).

## Phase 1 wiring outside `python/`

Plan acceptance lists four non-`python/` files (Makefile, CI workflow, docs, harnesses). **`scripts/ship-pr.sh`** is an intentional fifth wiring change: failed-job replay maps `python-lint` / `python-tests` CI jobs to `make py-lint` / `make py-test` (see `scripts/test-ship-pr.sh` replay cases). Revert only if replay stays allowlist-only until a later phase.
