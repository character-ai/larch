## Proposed Design Outline

### Goals
- Port the version-bump and changelog logic to two stdlib-only modules: `python/version_bump.py` and `python/changelog.py`.
- Cover the subtle paths explicitly: bump branch-guard, same-version race, and `NEW_VERSION < origin/main` regression correction.
- Carry bash-parity tests vs each ported `.sh`, plus unit tests for the gap paths and Markdown + RST changelog cases.

### Non-goals
- No change to the live `/implement` path; no module is wired in until Phase 7 (strangler-fig).
- Delete no `.sh`; the live path still calls them.
- No Phase 3 rebase orchestration — only the commit/drop primitives the rebase flow will later call.

### Approach sketch
- `version_bump.py`: classify (PATCH/MINOR/MAJOR/NONE), apply to `plugin.json`, branch-guard, same-version-race retry, regression correction, drop-bump-commit.
- `changelog.py`: read / insert / retitle / drop-section / extract a `## [X.Y.Z]` body for Markdown **and** RST, auto-resolve merge conflicts, commit-changelog, drop-changelog-commit.
- Shell out to `git` only through the injectable `proc.run` seam; route outbound text through `redact.py`; constants in `config.py`.
- Parity tests subprocess the real `.sh` and compare output, guarded by `skipif` when bash/`.sh` is unavailable (Phase 1 pattern).

### Surfaces in scope
- New: `python/version_bump.py`, `python/changelog.py`, `python/test_version_bump.py`, `python/test_changelog.py`.
- Updated (likely): `python/config.py` (new constants), `python/README.md` (module list).
- Read for port: `classify-bump.sh`, `apply-bump.sh`, `check-bump-version.sh`, `lib-changelog.sh`, `commit-changelog.sh`, `drop-bump-commit.sh`, `drop-changelog-commit.sh`, `auto-resolve-changelog.sh`.

### Open questions
- Exact source of the "refuse to bump on main/master unless forked" branch-guard (resolved during plan research).
- Whether drop-*-commit reimplements `git rebase --onto` history surgery in Python or wraps a thin git primitive — a plan-level choice, non-blocking.
