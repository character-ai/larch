### FINDING_1: code-quality: python/test_rebase.py
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] test_rebase.py omits most plan-listed parity cases (pre-pass multi-hop continue/skip version-regression changelog tail FIXER_ROLE argv) A stub-only suite may pass while regressions in drop-changelog rebump or conflict loops go undetected until Phase 7 integration Add the missing stub-runner tests from the plan including build_launch_argv role=resolve-conflict and conflict-files assertions
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: python/rebase.py:62-67,452-458
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Missing bash changelog_first_version_heading fallback when bump subject is not semver Bump dropped with non-template subject but valid ## [X.Y.Z] in CHANGELOG: bash stages bullets and drops companion commit; Python skips and can replay stale Update CHANGELOG during rebase Mirror ship_pr_record_old_bump_version using changelog.first_version_heading when subject parse fails
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: python/rebase.py:310-318
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] rebase never uses agents.build_launch_argv FIXER_ROLE or repo/run_id for fixer launches Future ship.py driver must reimplement launcher parity by hand; drift from launch-*-ci.sh flags is likely Add make_conflict_launch_fn using build_launch_argv and launch_tier as default wiring
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: python/git.py:290-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] unmerged_paths swallows git diff failures Failed git diff during in-progress rebase yields empty unmerged list and misleading abort/stall path Treat non-zero diff exit as error or Stalled with redacted output not as no conflicts
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: python/rebase.py:24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate bump subject regex vs version_bump Two regexes can diverge on subject format changes Share parse helper from version_bump
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: python/test_rebase.py:25-52
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated ScriptRunner harness Same argv-stub logic maintained in multiple test modules Extract shared stub runner for python tests
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: python/changelog.py
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Pre-existing RST parser inconsistencies Affects rebase CHANGELOG paths but not introduced by this branch Address in changelog phase follow-up
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] correctness: python/rebase.py:167-170
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Hardcoded MARKDOWN duplicate heading check in bullets path RST changelog rebump may mis-detect duplicates Use detect_format for duplicate_version_heading_count
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: python/git.py:290-297
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] unmerged_paths returns [] on git diff failure Misclassifies active conflicts as non-conflict abort or wrong continue/skip branch Treat non-zero diff exit as error; return [] only on success
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: python/rebase.py:310-327
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No in-process launch_tier/build_launch_argv wiring; repo/run_id unused Wrong or missing --role/--conflict-files when driver wires launch_fn naively Add factory using agents.build_launch_argv(FIXER_ROLE, conflict_files=...)
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: python/test_rebase.py:1-416
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Missing plan-mandated stub tests for multi-hop continue/skip/prepass/drop-bump/changelog Regressions in conflict loop or prepass ship untested Add remaining acceptance cases from implementation plan
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: python/rebase.py:524-527
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] new_version taken from target_version not apply_result.new_version apply_bump race-corrects version; changelog targets stale semver Use apply_result.new_version for changelog and RebaseResult
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: python/rebase.py:255
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] _sync_local_main ignores branch_force failure Stale local main skews classify_bump Check branch_force rc or mirror bash warning behavior
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: python/version_bump.py:566-578
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] apply_bump race guard hardcodes origin/main vs parameterized base in rebase Non-origin base_remote diverges between classify correction and apply race guard Parameterize apply_bump base or document origin-only contract
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: python/test_rebase.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan/acceptance list many rebase scenarios; diff implements only a subset. Regressions in drop-bump replay, deterministic prepass, continue/skip gating, rebump changelog tail, or version-regression guard can ship with green py-test. Add stub-runner tests for each plan bullet; use plan checklist before merge.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: python/test_rebase.py:26-52
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] ScriptRunner permissive=True auto-oks unlisted git argv in most integration tests. New or reordered git calls in rebase_and_rebump may not fail tests. Set permissive=False and assert full argv sequences on integration paths.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: python/rebase.py:310-338
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Conflict path does not use agents.build_launch_argv with FIXER_ROLE; tests only check CSV. Phase 7 wiring may omit --role resolve-conflict despite agents.py support. Wire launch through build_launch_argv and test --role and --conflict-files in argv.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: python/test_rebase.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for non-transient fetch failure to Stalled after abort. Wrong escalation or missing abort on generic fetch errors. Add fetch fail test without transient signature; assert abort and Stalled.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: python/test_rebase.py:322-347
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Force-push 5s retry path not tested; only OID noop short-circuit. Retry/sleep regression in _force_push_branch goes unnoticed. Test failed push, differing tips, sleep_fn(5), second push; double-fail Stalled.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: python/git.py:290-298
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] unmerged_paths returns [] on non-zero git diff exit. diff failures masquerade as no conflicts during _resolve_conflicts. Test non-zero diff exit; fail closed or stall instead of empty list.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: python/git.py:63-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] branch_force has no unit test. Incorrect -f argv for _sync_local_main undetected. Add test_branch_force_argv in test_git.py.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: python/test_rebase.py:63-71
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] IMPLEMENT_TMPDIR bullets path resolution untested. Env-based bullets path regression vs bash. monkeypatch ENV_IMPLEMENT_TMPDIR and assert _rebump_bullets_path.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: python/rebase.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No bash parity harness for Python rebase (plan unit-test only). Behavior drift vs rebase-push.sh/git-force-push.sh until Phase 7. Optional later: targeted bash comparison or harness slice.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] architecture: python/rebase.py:318-321
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Per-file fixer prompts from conflict-resolution.md not built. Agents may run without intended conflict context. Future phase: prompt builder + tests (not required for this review scope).
- **Suggested revision**: Address the concern above.

### FINDING_25: security: python/rebase.py:288-302
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Deterministic prepass calls git.add without -- before conflict paths. A conflicted file whose name starts with - can make git add interpret it as a flag and stage unintended paths before force-push. Use git add -- path (or extend git.add to always pass --) at all three prepass call sites.
- **Suggested revision**: Address the concern above.

### FINDING_26: security: python/rebase.py:324-327
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] conflict_csv is built from raw unmerged paths without larch_validate_vendor_conflict_csv parity. Custom launch_fn or comma/newline/.. paths can bypass launcher validation or mis-route the fixer agent. Validate each path in Python with the same rules as larch_validate_vendor_conflict_csv before join; stall on invalid segments.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: python/rebase.py:467-469
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] TransientNetworkError attaches unredacted fetch_result. A driver that logs exc.result may leak fetch stderr containing auth or infrastructure details. Redact fetch stdout/stderr on the exception or document and enforce redacted logging only.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: python/git.py:324-332
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] unmerged_paths returns [] on git diff failure. Failed diff is treated as no conflicts; rebase may continue or push with a broken index. Treat non-zero diff exit as error (Stalled) instead of returning an empty list.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: python/rebase.py:473-490
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No detection of in-progress rebase before git rebase base_target Retry after partial resolution aborts rebase and stalls losing staged resolutions Branch on rebase-merge state into _resolve_conflicts or rebase_continue instead of fresh rebase
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: python/test_rebase.py:1-416
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Missing tests for multi-hop continue skip gating prepass drop-changelog tail High-risk regressions pass CI undetected Add stub-runner cases from implementation plan acceptance list
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: python/rebase.py:310-344
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _resolve_conflicts ignores repo run_id and does not wire agents.launch_tier FIXER_ROLE Phase 7 driver may invoke fixers without resolve-conflict or conflict-files Provide factory wrapping launch_tier with FIXER_ROLE and conflict_files CSV
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: python/git.py:290-298
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] unmerged_paths returns empty list on git diff failure Failed diff during continue may trigger skip instead of conflict loop or stall Treat non-zero diff as indeterminate escalate Stalled or use ls-files -u
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: python/rebase.py:258-264
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] _is_empty_or_already_applied matches broad no changes substring Hook stderr containing no changes may cause inappropriate rebase --skip Narrow signatures to git empty-commit messages
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: python/rebase.py:536-544
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] RebaseResult always pushed True with empty detail Noop force-push indistinguishable from fresh push in logs Propagate noop vs pushed from _force_push_branch into result
- **Suggested revision**: Address the concern above.

### FINDING_35: **Important** `correctness` — Plan `_resolve_conflicts` step 3 / Round 1 “in-process fixer” (`rebase.py:310-344`) — The plan requires building the per-file fixer prompt from `conflict-resolution.md` (upstream/feature labels) and launching fixers via `agents.launch_tier` / `agents.build_launch_argv` with `role=config.FIXER_ROLE` and `--conflict-files`. `_resolve_conflicts` only forwards a CSV to an injected `launch_fn(tier, csv)` and discards `repo` / `run_id` (`_ = repo, run_id` at line 318). A future `ship.py` driver cannot recover parity without reimplementing prompt + argv wiring inside `rebase.py` or duplicating bash orchestrator logic. **Suggested fix:** Add prompt construction (at minimum path list + conflict context), a `default_conflict_launch_fn(runner, repo, run_id, …)` that calls `build_launch_argv`/`launch_tier` with `FIXER_ROLE` and `conflict_files`, and use it from `rebase_and_rebump` when the caller does not override.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** `correctness` — Plan `_resolve_conflicts` step 3 / Round 1 “in-process fixer” (`rebase.py:310-344`) — The plan requires building the per-file fixer prompt from `conflict-resolution.md` (upstream/feature labels) and launching fixers via `agents.launch_tier` / `agents.build_launch_argv` with `role=config.FIXER_ROLE` and `--conflict-files`. `_resolve_conflicts` only forwards a CSV to an injected `launch_fn(tier, csv)` and discards `repo` / `run_id` (`_ = repo, run_id` at line 318). A future `ship.py` driver cannot recover parity without reimplementing prompt + argv wiring inside `rebase.py` or duplicating bash orchestrator logic. **Suggested fix:** Add prompt construction (at minimum path list + conflict context), a `default_conflict_launch_fn(runner, repo, run_id, …)` that calls `build_launch_argv`/`launch_tier` with `FIXER_ROLE` and `conflict_files`, and use it from `rebase_and_rebump` when the caller does not override.
- **Suggested revision**: Address the concern above.

### FINDING_36: **Important** `correctness` — Plan “Testing strategy” / `python/test_rebase.py` acceptance — The plan lists many colocated cases; the branch only covers guards, already-fresh, `NONE`+push, transient fetch, waterfall exhaustion, non-conflict abort, `_is_empty_or_already_applied`, OID noop push, and invalid `old_version` staging. Still missing: drop-bump + versioned companion changelog drop (and Stalled on guarded refusal), deterministic pre-pass (CHANGELOG / `.claude-plugin/plugin.json` / `version.go` / `go.sum`, no `checkout_ours` on other paths), waterfall **win** → `rebase --continue`, multi-hop continue, continue-with-`U` re-loop, skip vs hook-failure abort, version-regression guard, post-rebump changelog tail (`write_changelog_entry`, `replaces_version`, duplicate-heading stall, `_changelog_ready_after_rebump`), non-transient fetch → `Stalled`, plain `--force-with-lease` + single 5s retry, and argv asserts for `--role resolve-conflict`. **Suggested fix:** Add the missing tests (stub runner + stub `launch_fn` returning success where needed), matching `test_version_bump.py` patterns.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Important** `correctness` — Plan “Testing strategy” / `python/test_rebase.py` acceptance — The plan lists many colocated cases; the branch only covers guards, already-fresh, `NONE`+push, transient fetch, waterfall exhaustion, non-conflict abort, `_is_empty_or_already_applied`, OID noop push, and invalid `old_version` staging. Still missing: drop-bump + versioned companion changelog drop (and Stalled on guarded refusal), deterministic pre-pass (CHANGELOG / `.claude-plugin/plugin.json` / `version.go` / `go.sum`, no `checkout_ours` on other paths), waterfall **win** → `rebase --continue`, multi-hop continue, continue-with-`U` re-loop, skip vs hook-failure abort, version-regression guard, post-rebump changelog tail (`write_changelog_entry`, `replaces_version`, duplicate-heading stall, `_changelog_ready_after_rebump`), non-transient fetch → `Stalled`, plain `--force-with-lease` + single 5s retry, and argv asserts for `--role resolve-conflict`. **Suggested fix:** Add the missing tests (stub runner + stub `launch_fn` returning success where needed), matching `test_version_bump.py` patterns.
- **Suggested revision**: Address the concern above.

### FINDING_37: **Important** `correctness` — Plan test requirement: “`launch_fn` asserts `--role resolve-conflict` and `--conflict-files` CSV” — `test_launch_fn_receives_conflict_csv` (`test_rebase.py:349-373`) only checks the CSV reaches the stub; `test_agents.py` covers `build_launch_argv` in isolation but nothing ties `rebase.py` to launcher argv. Production wiring is unverified and conflicts with the in-process fixer goal. **Suggested fix:** Either wire `rebase.py` through `build_launch_argv` and assert argv in an integration test, or add a `make_conflict_launch_fn` helper test that proves `--role` / `--conflict-files` when the default path runs.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Important** `correctness` — Plan test requirement: “`launch_fn` asserts `--role resolve-conflict` and `--conflict-files` CSV” — `test_launch_fn_receives_conflict_csv` (`test_rebase.py:349-373`) only checks the CSV reaches the stub; `test_agents.py` covers `build_launch_argv` in isolation but nothing ties `rebase.py` to launcher argv. Production wiring is unverified and conflicts with the in-process fixer goal. **Suggested fix:** Either wire `rebase.py` through `build_launch_argv` and assert argv in an integration test, or add a `make_conflict_launch_fn` helper test that proves `--role` / `--conflict-files` when the default path runs.
- **Suggested revision**: Address the concern above.

### FINDING_38: **Latent** `correctness` `python/rebase.py:346-350` — After `git rebase --continue` exits 0 with no `U` paths, `_resolve_conflicts` returns immediately. If git left a rebase in progress without unmerged entries (unusual), `rebase_and_rebump` would proceed to classify/rebump/push on a dirty rebase state. **Suggested fix:** After a successful continue, optionally verify `.git/rebase-merge` / `rebase-apply` is gone (or loop continue until finished), mirroring bash’s repeated `--continue` / `rebase-push --continue` episodes.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 4. **Latent** `correctness` `python/rebase.py:346-350` — After `git rebase --continue` exits 0 with no `U` paths, `_resolve_conflicts` returns immediately. If git left a rebase in progress without unmerged entries (unusual), `rebase_and_rebump` would proceed to classify/rebump/push on a dirty rebase state. **Suggested fix:** After a successful continue, optionally verify `.git/rebase-merge` / `rebase-apply` is gone (or loop continue until finished), mirroring bash’s repeated `--continue` / `rebase-push --continue` episodes.
- **Suggested revision**: Address the concern above.

### FINDING_39: **Nit** `correctness` `python/test_rebase.py` — Plan bullets_path resolution includes `IMPLEMENT_TMPDIR` env fallback (`_rebump_bullets_path` at `rebase.py:51-53`); tests cover explicit `tmpdir` and explicit `bullets_path` but not env-based resolution. **Suggested fix:** Add `monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, …)` and assert the resolved path.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 5. **Nit** `correctness` `python/test_rebase.py` — Plan bullets_path resolution includes `IMPLEMENT_TMPDIR` env fallback (`_rebump_bullets_path` at `rebase.py:51-53`); tests cover explicit `tmpdir` and explicit `bullets_path` but not env-based resolution. **Suggested fix:** Add `monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, …)` and assert the resolved path.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **architecture** — Acceptance requires `make py-lint` and `make py-test` green; this review did not execute those targets (read-only). Worth confirming in CI before merge.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **architecture** — `dd6f480ec` larch-logs flush is intentional per `docs/run-logs.md`; not a plan-fidelity issue for Phase 3. --- **Summary:** Core orchestration (`rebase_and_rebump`, deterministic pre-pass shape, NONE gate, force-push port, git helpers, `agents` `--conflict-files`) largely matches the plan structurally. Gaps are the in-process fixer prompt + `launch_tier` wiring, and most plan-listed `test_rebase.py` cases (including launcher argv parity and waterfall-success paths).
- **Suggested revision**: Address the concern above.

