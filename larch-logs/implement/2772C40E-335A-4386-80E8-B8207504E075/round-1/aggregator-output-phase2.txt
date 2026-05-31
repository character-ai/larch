Security affirmations (FINDING_12–16), plan-fidelity affirmations (FINDING_27), and branch metadata (FINDING_29) are informational only and are omitted from actionable findings. Positive security observations are not merged as fix items.

---

### FINDING_1: Duplicate carryover predicate in manifest builder
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `path_is_pre_coder_carryover` was extracted but `round_coder_delta_paths` still inlines the same carryover `cmp` logic. A later carryover rule change updates only the predicate; the manifest builder keeps excluding or including different paths than the guard, reviving false positives/negatives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Call `path_is_pre_coder_carryover` from `round_coder_delta_paths` instead of duplicating the grep/cmp block.

### FINDING_2: Near-duplicate carryover loops emit duplicate warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two near-identical loops differ only by manifest grep; both emit the same carryover warning. Carryover-only rounds log duplicate warnings per path (pre-commit then post-commit residue), adding noise without changing outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared pre_head load + carryover iteration; parameterize manifest filtering and downstream action.

### FINDING_3: Repeated carryover test fixture setup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: New orchestrator tests copy the same carryover repo setup. Future fixture tweaks require editing three blocks; one miss desynchronizes integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a `bootstrap_carryover_repo` helper used by all three cases.

### FINDING_4: [OUT_OF_SCOPE] Duplicate enumeration loops in cleanup.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: #3285 duplicates mktemp/find/read loops for cache and /tmp. Future enumeration changes must be applied twice on that file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared enumeration helper when editing cleanup.sh again.

### FINDING_5: Index-only coder changes misclassified as unchanged carryover (fail-open)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `path_is_pre_coder_carryover` uses worktree-only `git diff` vs snapshot; index-only coder mutations on index-only pre-dirt can be misclassified as unchanged carryover. Pre-dispatch `other.txt` dirty only in index (empty snapshot); coder `git add other.txt` with new content but worktree still matches `pre_head`; round exits `applied` while mutated index content for `other.txt` remains staged outside the manifest commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Compare index and worktree consistently in the predicate and snapshot (e.g. include `git diff --cached` in snapshot and cmp), if index-only coder changes must fail closed.
  - From cursor-specialist-edge-cases-output.txt: Snapshot and compare combined worktree+cached diff vs `pre_head` (or compare trees); add index-mutation regression in test-review-and-fix.sh.

### FINDING_6: Missing post-follow-up failure breadcrumb in docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan-required post-follow-up failure breadcrumb missing from documented breadcrumb list. Operator reads review-and-fix.md and does not see the string emitted at review-and-fix.sh:609 for persistent non-carryover residue after follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add bullet: ⚠ review-and-fix: round N left tracked changes uncommitted after follow-up.

### FINDING_7: No test for multi-round re-entry after manual commits (#3227)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No test for multi-round re-entry after main-agent manual commits (#3227 narrative). Production failure was described as manual commits between rounds with overlapping files; new tests only cover pre-dispatch carryover dirt, not clean-tree overlap after committed manual fixes. Production #3227 failure mode may differ from pre-dispatch carryover; fix could ship without covering that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a step5-starting-round or dispatch integration case: manual commit between rounds, then coder success on overlapping manifest paths.
  - From cursor-specialist-edge-cases-output.txt: Add multi-round resume integration test or document remaining gap vs issue narrative.

### FINDING_8: outside-manifest-break-carryover stub lacks worktree mutation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `outside-manifest-break-carryover` uses index/worktree split, not worktree mutation. Fail-closed coverage may not match a coder that actually edits a snapshotted path in the worktree; behavior also depends on git diff index vs worktree semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stub that mutates `other.txt` in the worktree, or assert manifest excludes `other.txt` in setup.

### FINDING_9: carryover-orchestrator omits commit-count assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Erroneous follow-up commit might not be detected if assertions on file list still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert rev-list count from initial HEAD is exactly 1.

### FINDING_10: No direct unit test for round_has_non_carryover_tracked_residue
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Post-commit gate regressions might only surface through heavier orchestrator paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add sed-extracted residue helper test with carryover-only vs hook-residue fixtures.

### FINDING_11: staged-carryover-orchestrator skips carryover warning assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Warning breadcrumb regression on staged carryover would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep for pre-existing dirty path carried over breadcrumb.

### FINDING_12: Unstaged carryover + git add/restore misclassified as outside-manifest dirt (fail-closed)
- **Reviewer(s)**: dyn-flag-removal-completeness-output.txt
- **Severity**: latent
- **Concern**: `path_is_pre_coder_carryover` classifies carryover using only `git diff "$pre_head" -- "$path"` (worktree vs `pre-coder-head`), while `capture_round_tracked_paths` also lists index-only dirt via `git diff --cached`. If pre-dispatch carryover was **unstaged** (non-empty snapshot) and the coder later runs the common `git add <path>` + `git restore --worktree` pattern—leaving the original staged blob in the index but a clean worktree—the worktree diff becomes empty, `cmp` no longer matches the snapshot, the path is treated as new outside-manifest dirt, and the round still fails closed with “dirty paths outside coder delta” even though the index content is unchanged carryover. The new `outside-manifest-break-carryover` harness deliberately exercises this shape; production coders can hit it without mutating carryover content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-removal-completeness-output.txt: When deciding carryover, treat a path as unchanged if either the worktree diff or the cached diff vs `pre_head` matches the snapshot (or snapshot both at dispatch with `git diff "$pre_head"` / `git diff "$pre_head" --cached` and compare both on the post-dispatch path), so index-only residue that still matches the pre-coder snapshot is not misclassified.

### FINDING_13: Carryover dirt may accumulate across Step 5 rounds
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Rounds may complete `applied` with warned carryover dirt left in the tree. Later Step 5 rounds or ship-pr assume a clean tree; carryover accumulates across rounds with only stderr warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit carryover path KVs or document/implement Step 5 cleanup expectations in implement SKILL.md.

### FINDING_14: Duplicate carryover warnings from guard and residue helper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Duplicate carryover warnings from guard and residue helper. Operators see duplicate breadcrumbs per path per round; noisy logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Warn once per path per round or only in the pre-commit guard.

### FINDING_15: outside-manifest-break-carryover stub diverges from plan-specified append
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `outside-manifest-break-carryover` stub uses git add/restore instead of plan-specified append to `other.txt`. Plan D says append during dispatch; impl uses index/worktree manipulation. Literal append would likely put `other.txt` in coder-stage-paths.txt and skip the outside-manifest guard via manifest continue, weakening fail-closed coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a short comment that the stub breaks carryover match while keeping other.txt outside the manifest; optional align plan text—no production change required.

### FINDING_16: [OUT_OF_SCOPE] External-coder round_dir write access to snapshots
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Codex dispatch grants write access to `$round_dir` alongside the repo root, so snapshot files written immediately before dispatch are not integrity-protected against a hostile external coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for #3272; a defense-in-depth improvement would snapshot to a read-only location the coder cannot reach, or re-read/recompute `pre-coder-head` and snapshots from git state after dispatch instead of trusting on-disk artifacts.

### FINDING_17: [OUT_OF_SCOPE] Session tmpdir cleanup deletes secrets without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Session tmpdirs under `~/.cache/larch/sessions/` may contain secrets and raw `CMD_JSON` argv; cleanup still deletes by age without redaction (documented in `SECURITY.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing operational posture; not introduced by this branch’s enumeration-warning change.

### FINDING_18: [OUT_OF_SCOPE] Enumeration failure warns and skips deletion (intentional fail-safe)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Enumeration failure now warns and skips instead of silent fail-open. Stale cache/tmp dirs may persist until find works; intentional fail-safe. Out of scope: intentional #3274 behavior with tests and SECURITY.md sync.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_19: [OUT_OF_SCOPE] LARCH_DESIGN_CONVERGENCE_THRESHOLD removal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Removed `LARCH_DESIGN_CONVERGENCE_THRESHOLD`; hardcoded non-nit max 5. Operators with old env exports see no effect; convergence semantics changed in prior work. Out of scope: intentional #3285 dead-config removal.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_20: [OUT_OF_SCOPE] #3272 does not address #3227 clean-tree manual-commit overlap
- **Reviewer(s)**: dyn-flag-removal-completeness-output.txt
- **Severity**: nit
- **Concern**: The branch correctly aligns the guard with `round_coder_delta_paths` for **dispatch-time** carryover; it does not change `run-step5-review.sh`. Failures from a fully clean tree after a manual commit (only committed overlap, no pre-dispatch porcelain) are a different mechanism and are not addressed here—consistent with the implementation plan.
- **Suggested revisions (informational for voters; coder decides)**:
