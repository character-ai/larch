### OOS_1: [OUT_OF_SCOPE] Implement test harnesses pass but do not validate compressed conflict-resolution semantics
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-contract-pins
- **Severity**: latent
- **Concern**: `bash scripts/test-implement-structure.sh` and `bash scripts/test-implement-fence-shape.sh` both pass on this branch, as do `pre-commit run markdownlint --files <active-scope>` and `python3 python/cli.py lint skill-closure-growth --skill implement` (exit 0). Pinned harness substrings and fence shapes are preserved, but the harnesses do not fully validate compressed procedural semantics such as per-exit-code stall seeding or conflict-type classification cues.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Unrelated run-log commit adds churn outside plan scope
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-contract-pins
- **Severity**: nit
- **Concern**: The branch contains commit `73cd3515f` (`chore(larch-logs): flush run log`), which is unrelated to the reference compression work and adds run-log churn outside the plan's active scope.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] self-review.md step numbering gap predates compression
- **Reviewer(s)**: dyn-dyn-contract-pins
- **Severity**: nit
- **Concern**: `skills/implement/references/self-review.md` still skips step 8 in its numbered list (7 → 9 → 10 → 11). That numbering gap predates this compression pass and is not introduced by it.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Scope pruning matches committed A1 artifact
- **Reviewer(s)**: dyn-dyn-scope-pruning
- **Severity**: nit
- **Concern**: Scope pruning matches the committed A1 artifact. `larch-logs/measure-references-heatmap/2026-07-01.tsv` retains only `skills/implement/references/conflict-resolution.md` and `skills/implement/references/stall-recovery.md` among conditional candidates. The branch edits exactly those two plus the three firm eager paths (`ship-pr-exit-matrix.md`, `self-review.md`, `step18-cleanup.md`). `step2-dispatch.md`, `checks-repair-loop.md`, and `codex-manifest-schema.md` are untouched; `skills/implement/SKILL.md` and runtime Python/Bash surfaces are unchanged aside from expected `larch-logs/` run artifacts.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] a1-retained-paths.txt not present in repo diff
- **Reviewer(s)**: dyn-dyn-scope-pruning
- **Severity**: nit
- **Concern**: `a1-retained-paths.txt` is not in the repo diff. The plan stores it under `$IMPLEMENT_TMPDIR`, so absence from git is expected. Post-merge scope audit relies on the committed heatmap TSV rather than a durable retained-paths sidecar.
- **Suggested revisions (informational for voters; coder decides)**:

