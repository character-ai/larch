# Design Discussion — Round 1 (scope & constraints)

Issue #3235 — ship-pr → Python Phase 2: Version bump & changelog.

## Decision 1: Which .sh files does Phase 2 port?
- **Question**: Five of the eight named scripts appear in the module descriptions; the other three (`commit-changelog.sh`, `drop-bump-commit.sh`, `drop-changelog-commit.sh`) are git-history primitives driven by Phase 3's rebase/re-bump flow. Port five logic scripts, or all eight?
- **Resolution**: **All eight.** Phase 2 ports the git-commit/history-surgery logic too: `commit-changelog.sh`, `drop-bump-commit.sh`, `drop-changelog-commit.sh` are reimplemented now (ahead of the Phase 3 rebase port that will consume them), not just read for context.
- **Source**: user

## Decision 2: How wide is RST support in changelog.py?
- **Question**: `auto-resolve-changelog.sh` already handles Markdown + RST (parity requires keeping RST there). `lib-changelog.sh` (insert/retitle/drop-section/extract) is Markdown-only — RST there is net-new with no `.sh` parity source, and the repo has no `.rst` changelog. The acceptance criteria list RST editing cases. Full RST or parity-only RST?
- **Resolution**: **Full RST.** Implement RST for both the conflict auto-resolver (parity with `auto-resolve-changelog.sh`) and the insert/retitle/drop-section/extract editors (net-new). Cover Markdown + RST cases for every changelog operation, per the written acceptance criteria.
- **Source**: user

## Decision 3: Parity-test mechanism
- **Question**: What does "parity test vs each ported .sh" mean operationally?
- **Resolution**: Follow the Phase 1 precedent: subprocess the real `.sh` and compare its output/side-effects to the Python output on shared fixtures, normalizing trailing newlines, guarded by `@pytest.mark.skipif(not <SH>.is_file() or shutil.which("bash") is None, ...)` so hermetic environments skip cleanly. Pattern lives in `python/test_redact.py`, `python/test_retry.py`, `python/test_agents.py` (`test_parity_*`).
- **Source**: codebase

## Decision 4: Strangler-fig — no live wiring (hard constraint)
- **Question**: Does Phase 2 change any live `/implement` path or delete any `.sh`?
- **Resolution**: No. Modules are additive under `python/`. Zero change to the live `/implement` path until Phase 7. Do not delete any shared `.sh` (the live path still calls them; deletion gates on a zero caller-grep across `skills/`/`scripts/`/`hooks/`/`.github/`, which is not Phase 2's job).
- **Source**: issue + AGENTS.md

## Decision 5: Conventions (locked)
- **Question**: What conventions bind the new modules?
- **Resolution**: Flat `python/` (no subdirs); tests colocated as `python/test_<module>.py`; all constants in `config.py`; immutable `@dataclass(frozen=True)` records; shell out only to true externals via the injectable `proc.run` seam (a `Runner`/stub in tests); all outbound text through `redact.py`; stdlib-only runtime (Python ≥ 3.12).
- **Source**: issue + python/README.md + Phase 1 modules

## Decision 6: No `.md` sibling for python/ modules
- **Question**: Do `version_bump.py` / `changelog.py` need sibling `.md` contract files?
- **Resolution**: No. The `script-md-siblings` rule scopes to `scripts/` and `skills/**/scripts/`, not the flat `python/` tree; Phase 1 `python/*.py` modules carry no `.md` siblings. Module-level docstrings + `python/README.md` cover documentation.
- **Source**: codebase (.claude/rules/script-md-siblings.md, python/ layout)
