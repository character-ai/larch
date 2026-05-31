All four inputs target different scripts and failure modes, so they stay as four separate findings with no merge.

### FINDING_1: apply_bump raises Stalled on unmerged instead of machine-readable APPLIED=false
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: On unmerged paths, `apply_bump` raises `Stalled`, which breaks the KV/stdout contract that `apply-bump.sh`, `ship-pr`, and parity tests expect (`APPLIED=false` with exit 4). Raising `Stalled` drops machine-readable output and conflates unmerged (bash exit 4) with dirty-tree (bash exit 1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Return ApplyResult(applied=False, error=...) for unmerged; reserve Stalled for bump_branch_guard. Document Phase 7 exit-code mapping to 4.

### FINDING_2: Transparent idempotency spec omits bash path guards and depth cap
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan’s transparent-idempotency behavior for `classify_bump` does not match bash: `classify_bump.sh` only treats “Update CHANGELOG” / `chore(larch-logs)` as transparent when changed paths are CHANGELOG-only or under `larch-logs/**` (lines 89–113), walks at most three commits (`IDEMPOTENCY_DEPTH=3`, lines 117–118), and subject-only spoofing must remain MINOR (`test-classify-bump.sh` 116–133). Omitting path guards and the depth cap would allow incorrect bump classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document and implement the same path guards and IDEMPOTENCY_DEPTH=3 in classify_bump; add a StubRunner/unit case mirroring test 5

### FINDING_3: check-bump-version.sh pre-mode not on Python surface
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `check-bump-version.sh` is only partially ported as post-mode `verify_bump_commit_count`. Round-1 scope and issue #3235 require all eight scripts; bash `--mode pre` (HAS_BUMP, COMMITS_BEFORE/STATUS, `.bump-version-armed`) is used in the Rebase + Re-bump sub-procedure but is absent from the Python API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add pre-mode API (or an explicit `check_bump_version_pre` helper) covering the full `scripts/check-bump-version.sh` contract, including optional armed-sentinel side effect

### FINDING_4: drop_bump_commit Guard 4 subset semantics diverge from bash equality rules
- **Reviewer(s)**: Cursor-dyn-cutover-boundary
- **Severity**: important
- **Concern**: The plan describes Guard 4 as changed-files ⊆ allowed set, but bash `drop-bump-commit.sh` (186–199) requires exact sorted `diff-name-only` equality to `.claude-plugin/plugin.json` only, or that file plus `CHANGELOG.md`; the `LARCH_BUMP_FILES` path also requires at least one non-CHANGELOG bump file unless `--allow-changelog-only`. Implementing ⊆ semantics would accept commits that touch only extra allowed paths or CHANGELOG-only without the flag, diverging from live rebase/rebump behavior and bash-parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cutover-boundary: Document and implement default-path exact multiset equality (LC_ALL=C sort) plus custom-path membership with BUMP_FILE_FOUND / allow-changelog-only rules matching drop-bump-commit.sh
