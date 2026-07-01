### OOS_1: [OUT_OF_SCOPE] code-quality: python/larch/implement/implement_dispatch.py:141
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] _pathspec_clean_relative_to_head is imported in implement_dispatch but only executed from dispatch_commit_route module globals; tests patch both modules. No runtime breakage; slightly confusing test setup only. Re-export explicitly or test via dispatch_commit_route only.
- **Suggested revision**: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] correctness: python/larch/implement/dispatch_commit_route.py:602-609
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Porcelain-clean pathspec is treated as already-committed but also matches paths reverted to HEAD after pathspec capture. Main agent captures pathspec at Step 2.4 then reverts those files during Step 3 checks; Step 4 noops instead of stalling, so the run may continue without the intended implementation commit. Optionally combine porcelain check with a baseline diff (e.g. compare pathspec files against step2-prelaunch digests) before nooping; only needed if revert-during-checks should stall.
- **Suggested revision**: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] risk-integration: python/tests/implement/test_implement_dispatch.py:2896-2923
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Recovery-branch already-committed noop has no dedicated test though recovery pathspec uses the same short-circuit. Regression in recovery-only flows would rely on manual review rather than a targeted test. Add a test mirroring test_run_step4_commit_leg_already_committed_by_main_agent_short_circuits_noop using recovery-metadata and step2-recovery-paths-final.nul.
- **Suggested revision**: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] architecture: python/larch/implement/dispatch_commit_route.py:606
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] _pathspec_clean_relative_to_head uses ad-hoc _run git status instead of typed git.status_porcelain_paths. No immediate breakage; diverges from G-Py-7 typed git wrapper guidance. Refactor to git.status_porcelain_paths when touching adjacent commit-route git probes.
- **Suggested revision**: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `skills/implement/SKILL.md:442` — Step 4 docs still mention only the `dispatcher-committed` skip breadcrumb, not the new `already-committed` reason. **Why OOS:** behavior is covered by unit tests; SKILL drift does not affect CI or regression risk for this change.
- **Suggested revision**: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `python/tests/implement/test_implement_dispatch.py:2922` — `assert "already-committed" in captured.out` is ambiguous because the fixture filename is `already-committed.txt`, so the assertion would pass even if the breadcrumb reason were wrong. **Why OOS:** weak assertion quality, not a missing risk-bearing path; the test still asserts `outcome == "noop"` and `calls == []`.
- **Suggested revision**: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **risk-integration** `python/larch/implement/dispatch_commit_route.py:602-609` — `_pathspec_clean_relative_to_head` uses `_run([GIT_BIN, "status", ...])` without an explicit `cwd=repo_root`, same as the existing Step 4 commit leg. **Why OOS:** pre-existing cwd assumption, not introduced or amplified by this diff.
- **Suggested revision**: Address the concern above.

