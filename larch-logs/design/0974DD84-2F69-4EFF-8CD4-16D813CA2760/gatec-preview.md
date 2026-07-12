## Final Design Plan

## Plan

### UPDATED: python/larch/review/snapshot.py

- Add prefix-aware snapshot artifact helpers parameterized by `snap_dir: Path` and `prefix: str` for head, inventories, patch directory, and per-path patch files.
- Route both snapshot writers, patch capture/matching, inventory reads, and validation through those helpers while retaining the existing public and private facade names, signatures, roots, and prefixes:
  - Pre-coder: `pre_coder_snapshot_dir(round_dir)`, `pre-coder`.
  - Self-review: `_self_review_snapshot_dir(implement_tmpdir)`, `pre-self-review`.
- Keep pre-coder-only lifecycle behavior outside the shared family core: refusal to overwrite, `head_untracked`, attempt artifacts, snapshot identity revalidation, cleanup/restore, and permission hardening.
- Keep self-review-only lifecycle behavior in its facade: replacement of prior artifacts, `self-review-accepted.md` gating, empty-HEAD return, and fail-soft collection for missing or invalid snapshots.

## Drift convergence for review

- Use `_safe_patch_name()` and raw `_git_stdout()` patch bytes for both families. Capture and match each family’s patch artifacts with the same byte-preserving mechanism.
- Share tracked-delta classification over a caller-supplied tracked-path list (or enumeration callback) and a `patch_match_ref`; the shared loop must not select a probe or call `_tracked_paths_vs_ref()` itself.
  - Pre-coder supplies `_tracked_paths_vs_ref(diff_base)` and passes the original snapshot head as `patch_match_ref` when collecting since a post-coder commit.
  - Self-review supplies its current single worktree `git diff --name-only <pre_head>` result and passes its pre-head as `patch_match_ref`.
- Do not converge tracked-path probe policy. Pre-coder retains `_tracked_paths_vs_ref()`’s worktree-plus-cached union; self-review retains its current single worktree enumeration and must not gain a cached probe.
- Reuse `_snapshot_inventory()` validation for self-review inventories, including rejection of absolute, traversal, NUL-bearing, and duplicate entries. Preserve self-review’s fail-soft conversion of validation failures into no staging paths.
- Do not converge overwrite policy, missing-HEAD handling, pre-coder patch completeness, attempt snapshots, or cleanup behavior.

## Edge cases

- Preserve empty tracked and untracked inventories and ordered deduplication across tracked and untracked paths.
- Reject patch-name collisions before trusting patch artifacts.
- Keep pre-existing staged and unstaged edits excluded from the relevant family’s collected deltas.
- Preserve self-review’s worktree-only tracked discovery, including its staged-index behavior, rather than widening collection through a cached scan.
- Keep missing or unsafe self-review artifacts fail-soft at collection; pre-coder validation remains fail-closed.

## Failure modes

- A wrong root or prefix can silently write or read a different artifact family. Build every shared artifact path from the passed root and prefix.
- Collapsing `diff_base` and snapshot-head comparison would misclassify pre-existing dirty paths after a coder commit. Keep caller-selected enumeration separate from the patch-match reference.
- Letting the shared classifier choose `_tracked_paths_vs_ref()` would reintroduce a cached probe to self-review and change commit-route scope. Require each facade to enumerate paths before calling it.
- Over-generalizing validation can weaken pre-coder integrity or make self-review fatal. Retain facade-specific completeness and error handling.
- Removing private facade functions can break callers, monkeypatch seams, or downstream imports. Keep them as thin wrappers.

## Testing strategy

- Extend `python/tests/review/test_review_and_fix.py` with an executable nonempty self-review snapshot test using the git fixture: capture a tracked baseline, assert `pre-self-review` artifact paths and patch files, verify the baseline edit is excluded, and verify a later edit is collected.
- Add regression coverage that pre-coder collection since a committed coder result supplies `_tracked_paths_vs_ref(diff_base)` but matches the baseline patch with the earlier snapshot head.
- Add self-review probe-policy coverage for staged-only and unstaged-only post-snapshot changes, asserting the self-review facade supplies only its worktree `git diff --name-only <pre_head>` paths, does not call `_tracked_paths_vs_ref()`, and does not stage cached-only changes.
- Run existing snapshot-focused review-and-fix cases unchanged, including capture, revalidation, cleanup, dirty-state exclusion, self-review fallback, and staging fallback.
- Run `python/tests/review/test_review_pipeline.py` and `python/tests/agents/test_external_dispatch.py`, plus scoped lint and type checks for `python/larch/review/snapshot.py`.
- Confirm net line reduction and review every drift-convergence item above against the resulting tests.

Confidence: high
difficulty: MODERATE
diff_added: 125
diff_deleted: 155
mechanical_churn: false
diff_lines: 280
