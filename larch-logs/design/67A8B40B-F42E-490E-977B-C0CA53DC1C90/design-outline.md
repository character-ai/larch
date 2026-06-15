## Proposed Design Outline

### Goals
- Prevent test infrastructure from reaching the installed plugin cache.
- Remove dev-only top-level directories (`.claude/`, `.github/`, `.gemini/`) from the sparse checkout cone.
- Add a post-install cleanup step in `upgrade_larch.py` that deletes test files from the cache after install.

### Non-goals
- Moving test files to different directories in the repo (files stay where they are in the source tree).
- Covering initial installs without `/upgrade-larch` (first-time installs keep test files until first upgrade).
- Excluding runtime markdown or docs from the install.

### Approach sketch
- Remove `.claude`, `.github`, `.gemini`, `tests` from `LARCH_SPARSE_DIRS` in `scripts/lib-sparse-dirs.sh` and `python/upgrade_larch.py`.
- Add `clean_test_files_from_cache(cache_dir, version)` in `upgrade_larch.py`; call it in `run_main` after successful `claude plugin install`.
- Patterns to clean: `python/test_*.py`, `python/conftest.py`, `python/pyproject.toml`, `python/ruff.toml`, `scripts/test-*.sh`, `scripts/test-*.md`, `skills/*/scripts/test-*.sh`, `skills/*/scripts/test-*.md`, root `parallel-tests.py`, `Makefile`.
- Update the intentional literal guard in `python/test_upgrade_larch.py`.
- Update all edit-in-sync surfaces: `docs/installation-and-setup.md`, `skills/upgrade-larch/SKILL.md`, `.claude/skills/release/SKILL.md`, `docs/skills.md`, `SECURITY.md`.

### Surfaces in scope
- `scripts/lib-sparse-dirs.sh` — primary sparse allowlist
- `python/upgrade_larch.py` — upgrade driver, LARCH_SPARSE_DIRS constant, cleanup function
- `python/test_upgrade_larch.py` — literal guard update
- `docs/installation-and-setup.md` — user-facing install command
- `skills/upgrade-larch/SKILL.md` — skill reference
- `.claude/skills/release/SKILL.md` — release skill reference
- `docs/skills.md`, `SECURITY.md` — edit-in-sync surfaces

### Open questions
- None.
