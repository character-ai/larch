### OOS_1: [OUT_OF_SCOPE] architecture — duplicated `Fixes #N:` prefix
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-release-flow
- **Severity**: latent
- **Concern**: The `^Fixes #([0-9]+):` companion prefix is duplicated in `python/larch/release/release_prepare.py:22` and `python/larch/implement/ship_pr.py:56` instead of a shared `config.py` constant. A future change to one side could break companion resolution silently (fallback to PR title). Pre-existing informal contract; not introduced by this branch's logic change.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] risk-integration — README `/release` arguments drift
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-release-flow
- **Severity**: nit
- **Concern**: The `/release` arguments column was updated for `--approve|-a`, but the README description row (`README.md:209`, `README.md:224-226`) still omits auto-approve behavior, companion-issue title sourcing, and no-PR-diff semantics that `docs/skills.md` already documents. README-only doc drift; behavior lives in the skill and prepare helper.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] correctness — companion resolution title-prefix coverage gap
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Companion resolution in `python/larch/release/release_prepare.py:22` only matches a `Fixes #N:` PR title prefix. PRs that link issues only via `Closes #N` in the body (common outside the `/implement` ship path) still get PR titles in notes. That matches the approved plan, but it is a known coverage gap for manual PRs.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] risk-integration — per-PR `gh issue view` API load and latency
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Each `Fixes #N:` PR adds a sequential `gh issue view` call during operator `release prepare` (`python/larch/release/release_prepare.py:58-74`). Failures degrade safely to PR-title fallback (tested), but a large release window adds API load, latency, and `gh` rate-limit exposure not covered by tests. Not a functional bug under current design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: accept as documented degraded path; only batch/cache if releases routinely hit limits.

### OOS_5: [OUT_OF_SCOPE] risk-integration — no mechanical regression test for `--approve` / `PR_COUNT=0` safety
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `--approve` / `PR_COUNT=0` safety is specified only in skill prose (`.claude/skills/release/SKILL.md:116-136`); there is no mechanical regression test (design reviewers suggested one, but the approved plan scoped Python tests to companion-title resolution only). A future Step 4 edit could reintroduce auto-confirm on empty windows without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: add a lightweight skill-contract test (markdown lint or flag-parser harness) if this gate becomes recurring.

### OOS_6: [OUT_OF_SCOPE] risk-integration — partition doc cites retired test path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `scripts/lint-harness-pytest-partition.md:47` still cites retired path `python/test_release.py` while tests live at `python/tests/release/test_release.py`. Pre-existing doc drift; does not affect this branch's CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: update the partition doc path in a housekeeping PR.

