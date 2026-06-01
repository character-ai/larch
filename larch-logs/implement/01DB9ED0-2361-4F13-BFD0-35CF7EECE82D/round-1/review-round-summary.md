# Review Round 1

- Mode: `diff`
- 15 accepted, 12 rejected (12 exonerated)

## Accepted Findings

### FINDING_1: code-quality: python/test_rebase.py
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] test_rebase.py omits most plan-listed parity cases (pre-pass multi-hop continue/skip version-regression changelog tail FIXER_ROLE argv) A stub-only suite may pass while regressions in drop-changelog rebump or conflict loops go undetected until Phase 7 integration Add the missing stub-runner tests from the plan including build_launch_argv role=resolve-conflict and conflict-files assertions
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: python/rebase.py:310-327
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No in-process launch_tier/build_launch_argv wiring; repo/run_id unused Wrong or missing --role/--conflict-files when driver wires launch_fn naively Add factory using agents.build_launch_argv(FIXER_ROLE, conflict_files=...)
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: python/rebase.py:524-527
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] new_version taken from target_version not apply_result.new_version apply_bump race-corrects version; changelog targets stale semver Use apply_result.new_version for changelog and RebaseResult
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: python/test_rebase.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan/acceptance list many rebase scenarios; diff implements only a subset. Regressions in drop-bump replay, deterministic prepass, continue/skip gating, rebump changelog tail, or version-regression guard can ship with green py-test. Add stub-runner tests for each plan bullet; use plan checklist before merge.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: python/rebase.py:310-338
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Conflict path does not use agents.build_launch_argv with FIXER_ROLE; tests only check CSV. Phase 7 wiring may omit --role resolve-conflict despite agents.py support. Wire launch through build_launch_argv and test --role and --conflict-files in argv.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: python/test_rebase.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for non-transient fetch failure to Stalled after abort. Wrong escalation or missing abort on generic fetch errors. Add fetch fail test without transient signature; assert abort and Stalled.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: python/git.py:290-298
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] unmerged_paths returns [] on non-zero git diff exit. diff failures masquerade as no conflicts during _resolve_conflicts. Test non-zero diff exit; fail closed or stall instead of empty list.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: python/git.py:324-332
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] unmerged_paths returns [] on git diff failure. Failed diff is treated as no conflicts; rebase may continue or push with a broken index. Treat non-zero diff exit as error (Stalled) instead of returning an empty list.
- **Suggested revision**: Address the concern above.


### FINDING_3: architecture: python/rebase.py:310-318
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] rebase never uses agents.build_launch_argv FIXER_ROLE or repo/run_id for fixer launches Future ship.py driver must reimplement launcher parity by hand; drift from launch-*-ci.sh flags is likely Add make_conflict_launch_fn using build_launch_argv and launch_tier as default wiring
- **Suggested revision**: Address the concern above.


### FINDING_31: architecture: python/rebase.py:310-344
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _resolve_conflicts ignores repo run_id and does not wire agents.launch_tier FIXER_ROLE Phase 7 driver may invoke fixers without resolve-conflict or conflict-files Provide factory wrapping launch_tier with FIXER_ROLE and conflict_files CSV
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: python/git.py:290-298
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] unmerged_paths returns empty list on git diff failure Failed diff during continue may trigger skip instead of conflict loop or stall Treat non-zero diff as indeterminate escalate Stalled or use ls-files -u
- **Suggested revision**: Address the concern above.


### FINDING_35: **Important** `correctness` — Plan `_resolve_conflicts` step 3 / Round 1 “in-process fixer” (`rebase.py:310-344`) — The plan requires building the per-file fixer prompt from `conflict-resolution.md` (upstream/feature labels) and launching fixers via `agents.launch_tier` / `agents.build_launch_argv` with `role=config.FIXER_ROLE` and `--conflict-files`. `_resolve_conflicts` only forwards a CSV to an injected `launch_fn(tier, csv)` and discards `repo` / `run_id` (`_ = repo, run_id` at line 318). A future `ship.py` driver cannot recover parity without reimplementing prompt + argv wiring inside `rebase.py` or duplicating bash orchestrator logic. **Suggested fix:** Add prompt construction (at minimum path list + conflict context), a `default_conflict_launch_fn(runner, repo, run_id, …)` that calls `build_launch_argv`/`launch_tier` with `FIXER_ROLE` and `conflict_files`, and use it from `rebase_and_rebump` when the caller does not override.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** `correctness` — Plan `_resolve_conflicts` step 3 / Round 1 “in-process fixer” (`rebase.py:310-344`) — The plan requires building the per-file fixer prompt from `conflict-resolution.md` (upstream/feature labels) and launching fixers via `agents.launch_tier` / `agents.build_launch_argv` with `role=config.FIXER_ROLE` and `--conflict-files`. `_resolve_conflicts` only forwards a CSV to an injected `launch_fn(tier, csv)` and discards `repo` / `run_id` (`_ = repo, run_id` at line 318). A future `ship.py` driver cannot recover parity without reimplementing prompt + argv wiring inside `rebase.py` or duplicating bash orchestrator logic. **Suggested fix:** Add prompt construction (at minimum path list + conflict context), a `default_conflict_launch_fn(runner, repo, run_id, …)` that calls `build_launch_argv`/`launch_tier` with `FIXER_ROLE` and `conflict_files`, and use it from `rebase_and_rebump` when the caller does not override.
- **Suggested revision**: Address the concern above.


### FINDING_36: **Important** `correctness` — Plan “Testing strategy” / `python/test_rebase.py` acceptance — The plan lists many colocated cases; the branch only covers guards, already-fresh, `NONE`+push, transient fetch, waterfall exhaustion, non-conflict abort, `_is_empty_or_already_applied`, OID noop push, and invalid `old_version` staging. Still missing: drop-bump + versioned companion changelog drop (and Stalled on guarded refusal), deterministic pre-pass (CHANGELOG / `.claude-plugin/plugin.json` / `version.go` / `go.sum`, no `checkout_ours` on other paths), waterfall **win** → `rebase --continue`, multi-hop continue, continue-with-`U` re-loop, skip vs hook-failure abort, version-regression guard, post-rebump changelog tail (`write_changelog_entry`, `replaces_version`, duplicate-heading stall, `_changelog_ready_after_rebump`), non-transient fetch → `Stalled`, plain `--force-with-lease` + single 5s retry, and argv asserts for `--role resolve-conflict`. **Suggested fix:** Add the missing tests (stub runner + stub `launch_fn` returning success where needed), matching `test_version_bump.py` patterns.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Important** `correctness` — Plan “Testing strategy” / `python/test_rebase.py` acceptance — The plan lists many colocated cases; the branch only covers guards, already-fresh, `NONE`+push, transient fetch, waterfall exhaustion, non-conflict abort, `_is_empty_or_already_applied`, OID noop push, and invalid `old_version` staging. Still missing: drop-bump + versioned companion changelog drop (and Stalled on guarded refusal), deterministic pre-pass (CHANGELOG / `.claude-plugin/plugin.json` / `version.go` / `go.sum`, no `checkout_ours` on other paths), waterfall **win** → `rebase --continue`, multi-hop continue, continue-with-`U` re-loop, skip vs hook-failure abort, version-regression guard, post-rebump changelog tail (`write_changelog_entry`, `replaces_version`, duplicate-heading stall, `_changelog_ready_after_rebump`), non-transient fetch → `Stalled`, plain `--force-with-lease` + single 5s retry, and argv asserts for `--role resolve-conflict`. **Suggested fix:** Add the missing tests (stub runner + stub `launch_fn` returning success where needed), matching `test_version_bump.py` patterns.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: python/git.py:290-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] unmerged_paths swallows git diff failures Failed git diff during in-progress rebase yields empty unmerged list and misleading abort/stall path Treat non-zero diff exit as error or Stalled with redacted output not as no conflicts
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: python/git.py:290-297
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] unmerged_paths returns [] on git diff failure Misclassifies active conflicts as non-conflict abort or wrong continue/skip branch Treat non-zero diff exit as error; return [] only on success
- **Suggested revision**: Address the concern above.


