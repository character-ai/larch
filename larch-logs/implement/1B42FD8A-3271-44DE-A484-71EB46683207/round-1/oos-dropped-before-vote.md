### OOS_1: [OUT_OF_SCOPE] chore(larch-logs) flush
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Commit `8e7ebe697` flushes larch run logs; reviewers flagged it as outside the scope of code review for this change.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] archetype generator count doc drift
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `.claude/rules/reviewer-archetype-generation.md:29` still says "four archetype generators" while a fifth generator (`conflict-resolution-code-reviewer`) is now listed above. That line was not updated in the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Rephrase to exclude the conflict fragment generator or count five agent/fragment generators explicitly.

### OOS_3: [OUT_OF_SCOPE] Claude fallback vs fragment prompt parity
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Phase 3d loads the fragment for template-based externals, but Claude fallbacks still use `subagent_type: larch:code-reviewer` (the generated agent with resolved placeholders). That split predates this PR and was not changed here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: No change required for this PR; consider aligning Claude conflict-review prompts with the fragment substitution contract in a follow-up if parity matters.

### OOS_4: [OUT_OF_SCOPE] `test_generate_check_accepts_verb_registry` bypasses untracked-artifact guard
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/test_rendering.py:124-143` (and `:138-142`) monkeypatches `git ls-files --error-unmatch` to always succeed for `skills/shared/reviewer-templates-code-reviewer.md`, so pytest no longer exercises the untracked-artifact guard for that path locally. If the fragment is removed from the git index but left on disk, the test can pass while CI `generate check` fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Drop the mock now that the file is committed and tracked; rely on `generate_check_main`'s real `git ls-files` check, or add a dedicated test that asserts failure when the artifact is untracked.
  - From cursor-specialist-testing: Drop the monkeypatch now that the file is committed and tracked.

### OOS_5: [OUT_OF_SCOPE] structure harness does not pin Phase 2/3 routing or Phase 3d fragment load
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-generator-registry
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh:419-441` still only checks that `caller_kind=ship_pr_pre_push` and `caller_kind=early_rebase` appear in `conflict-resolution.md`; it does not pin the new Phase 2 routing prose, the Phase 3 entry gate, or the `reviewer-templates-code-reviewer.md` reference in 3d. A future edit could revert the live-path gate and CI would not catch it until manual grep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `require()`/`forbid()` needles for the Phase 2 split, the `early_rebase`-only Phase 3 skip, and the fragment path (plan marked this optional).

### OOS_6: [OUT_OF_SCOPE] `BACKTICKED_FOCUS_FILES` and `BACKTICKED_FILES` remain manually duplicated
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-generator-registry
- **Severity**: nit
- **Concern**: `python/larch/review/voting.py:49-61` and `.github/workflows/ci.yaml:419-431` (or `:419-430`) keep hand-duplicated `BACKTICKED_FOCUS_FILES` / `BACKTICKED_FILES` lists. This PR updates both, but there is still no mechanical sync test or single-source guard against future drift when another generated prompt surface is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a lint or pytest that asserts the two lists match (pre-existing hygiene, not introduced by this branch).

### OOS_7: [OUT_OF_SCOPE] re-enabled Phase 3 for `ship_pr_pre_push` increases operational exposure
- **Reviewer(s)**: dyn-dyn-generator-registry
- **Severity**: latent
- **Concern**: Re-enabling Phase 3 for `ship_pr_pre_push` is intentional and correctly wired (Phase 2 routes to Phase 3 entry; trivial-all still skips the panel), but it does amplify operational exposure: CI-fix rebase runs with high-confidence non-trivial auto-resolutions can now enter the 3-reviewer panel, voting loop, and two-round bail-to-Step-18 path that `early_rebase` still avoids. That is expected product behavior, not a wiring bug.
- **Suggested revisions (informational for voters; coder decides)**:

