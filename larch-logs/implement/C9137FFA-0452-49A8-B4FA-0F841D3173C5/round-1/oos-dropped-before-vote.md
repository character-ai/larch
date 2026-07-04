### OOS_1: [OUT_OF_SCOPE] correctness: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Live Step 3 uses checks-commit-route which already stamps CLONE_PATH on markers; run-step-checks.sh is legacy-only per run-step-checks.md. Shipping only the shell printf does not change production /implement Step 3 markers; the stated highest-traffic cross-clone exposure was already closed on dispatch_commit_route. Document in issue closure that dispatch_commit_route is the live writer; treat shell work as legacy parity only.
- **Suggested revision**: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] correctness: python/larch/lint/lint_bg_wait_writer_parity.py:41-47
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] _has_clone_path_emission matches any non-comment CLONE_PATH= substring, not marker-write proximity. A future edit could remove CLONE_PATH from the marker printf but keep an unrelated CLONE_PATH= log/comment line and pass lint. Require CLONE_PATH= within the same function/block as the .bg-wait-active write, or pair with lint_bg_wait_coverage discovery.
- **Suggested revision**: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] correctness: python/larch/implement/dispatch_commit_route.py:1108-1115
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run_step_checks_main never arms a bg-wait marker for any --site value. Callers using implement run-step-checks --site step3 get checks with no hook bg-wait denial coverage. Route through checks-commit-route or share _write_bg_wait_marker when reviving this CLI path.
- **Suggested revision**: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] correctness: skills/implement/scripts/run-step-checks.sh:76
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Legacy shell Step 3 marker still uses TIMEOUT_S=10800 vs 15600 on live checks-commit-route path Reactivating run-step-checks.sh for Step 3 would arm a shorter timeout than the composite path Align TIMEOUT_S with dispatch_commit_route config if the shell path is restored
- **Suggested revision**: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md; python/larch/implement/dispatch_commit_route.py:75-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Live Step 3 already stamps CLONE_PATH via checks-commit-route; shell fix is legacy parity only Production cross-clone scoping for Step 3 was already correct on main; this diff does not change the active orchestration path Document legacy-only status in run-step-checks.md (partially done) or remove dead SITE=step3 block if legacy path is retired
- **Suggested revision**: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] correctness: python/larch/implement/step_7a.py:92-105; python/larch/implement/dispatch_commit_route.py:75-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate _write_bg_wait_marker implementations can drift independently Lint inventories both files but does not enforce shared helper or field parity between duplicates Extract shared marker writer helper used by both modules
- **Suggested revision**: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] correctness: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Live Step 3 path already stamps CLONE_PATH via Python composite Shell run-step-checks.sh fix does not affect production /implement Step 3 markers N/A for this branch; legacy parity only
- **Suggested revision**: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] risk-integration: python/larch/lint/lint_bg_wait_writer_parity.py:22-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Frozen inventory misses brand-new writers until manually updated New writer outside WRITERS tuple would not fail lint until inventory is updated Accept tradeoff or cross-check lint_bg_wait_coverage mappings later
- **Suggested revision**: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-bgwait-marker-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:441` / `python/larch/implement/dispatch_commit_route.py:75-88` — Active `/implement` Step 3 already writes `CLONE_PATH=` through `checks-commit-route` → `_write_bg_wait_marker()`; `test_dispatch_bg_wait_marker_copies_keepalive_clone_path` covers that path. The shell change in `run-step-checks.sh` only affects the legacy `--site step3` wrapper (`run-step-checks.md:7-8`, `dispatch_commit_route.py:1108-1115`), so this branch does not change production Step 3 marker behavior on current main.
- **Suggested revision**: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-bgwait-marker-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/run-step-checks.sh:76-77` — The legacy shell writer still stamps `TIMEOUT_S=10800` while the live composite uses `15600` for `implement-step3-checks` (`dispatch_commit_route.py:119-121`). That timeout skew predates this branch and only matters if the orphaned shell path is reactivated.
- **Suggested revision**: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-bgwait-marker-output.txt
- **Concern**: - **risk-integration** `python/larch/lint/lint_bg_wait_writer_parity.py:22-31` — The frozen writer inventory cannot detect a brand-new `.bg-wait-active` writer until the list is updated manually; cross-checking against `lint_bg_wait_coverage.KNOWN_BACKGROUND_COMMANDS` would close that drift mode but is outside this diff.
- **Suggested revision**: Address the concern above.

