# Review Round 2

- Mode: `diff`
- 13 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: python/voting.py:828-848
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Design tmpdir log-root resolver omits git rev-parse fallback from design_lifecycle._resolve_working_tree_root. /design Step 3 with unset LARCH_CONSUMER_REPO/CLAUDE_PROJECT_DIR and no REPO_ROOT in source-env.sh resolves larch-logs from plugin cwd; voter prompts get wrong or empty calibration from consumer corpus. Add git rev-parse fallback after source-env.sh read or share the design_lifecycle helper; test plugin cwd vs consumer repo without env anchors.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: python/test_plan_review_panel.py
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-mandated plan_review_panel.dispatch_voters integration tests are largely still missing. Consumer log-root miswiring, wrong per-tool prompts, or stale snapshot reuse on plan-review path can ship without failing CI. Extend dispatch_voters harness to assert snapshot --log-root, render --voter-tool/--calibration-stats-file, exact prompt paths, prompt_files manifest, no_fallback=True, and snapshot-failure paths.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: python/voting.py:883-885
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Snapshot CLI env window contract lacks dedicated tests. LARCH_VOTER_CALIBRATION_WINDOW parsing or malformed-env fallback could regress without CI signal. Add voter_calibration_snapshot_main tests with env-only window and malformed env values.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: python/voting.py:819-848
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Design-tmpdir resolver still falls through to cwd-based repo discovery after env and source-env misses Plan-review snapshot creation can read the plugin checkout larch-logs corpus instead of the consumer corpus when env anchors are absent Delegate to design_lifecycle._resolve_working_tree_root(design_tmpdir) or inline its git rev-parse fallback before any cwd-based fallback
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: python/voting.py:798-816
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Review-tmpdir resolver checks keepalive only after final_report fallback Implement Step 5 can still resolve the plugin larch-logs tree because final_report._implement_repo_root returns the cwd-based repo root first Check review keepalive before delegating, or make the delegated helper return None on cwd-based fallback so keepalive can win
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: python/test_plan_review_panel.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-mandated plan-review dispatch integration tests are largely still missing after round-1 feedback. Only kill-switch coverage exists; dispatch_voters harness does not assert snapshot argv consumer log-root per-tool render flags prompt_files manifest no_fallback or snapshot-failure paths so plan-review calibration wiring can regress silently. Extend dispatch_voters harness tests per the implementation plan checklist.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: python/test_agent_voters.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-mandated code-review dispatch calibration tests are incomplete. Existing tests cover helper log-root and per-tool render labels but not one-snapshot-per-dispatch manifest prompt_files calibration-stats-file on render codex-absent paths or stale snapshot after failure. Add dispatch-level tests asserting snapshot count manifest prompt_files render argv and failure cleanup.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: python/test_voting.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-listed voting snapshot edge-case tests are still absent. Flat review run-dir grouping design multi-round grouping unsupported TSV skip zero-severity empty output LARCH_CONSUMER_REPO default log-root and env-window CLI behavior are untested. Add temp-dir fixtures and voter_calibration_snapshot_main env-window tests.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: python/voting.py:828-848
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Design log-root resolution can still read plugin larch-logs when session anchors are empty. With no env anchors and no REPO_ROOT in source-env.sh plan-review snapshot uses consumer_repo_root from plugin cwd; no negative test guards this FINDING_2 residual. Add a failing-case test or persist consumer repo root into design source-env during session setup.
- **Suggested revision**: Address the concern above.


### FINDING_19: **correctness** `python/voting.py:798-815` — The accepted keepalive corpus-resolution fix is still incomplete. `_implement_repo_root_from_review_tmpdir()` treats `final_report._implement_repo_root()` as authoritative, but `python/final_report.py:143-160` falls back to `repo_roots.consumer_repo_root()` from the current cwd when implement-session anchors are missing or unusable. In `/implement` Step 5, that cwd is the plugin checkout, so a parent `session-env.sh` with no usable repo keys can make this helper return the plugin repo before it ever checks `review_tmpdir/.larch-keepalive`; likewise an implement `.larch-keepalive` `CLONE_PATH` that cannot be resolved as a Git worktree is not used as-is as the plan requires. Concrete failure: env anchors unset, plugin cwd, parent session file present but stale, and `review_tmpdir/.larch-keepalive` points at the consumer repo. The resolver returns `larch3/larch-logs`, so voters receive calibration from the plugin corpus instead of the consumer corpus. **Suggested fix:** Split the implement-anchor resolver so it only returns session-env or keepalive-derived roots, including cleaned `CLONE_PATH` as-is when `consumer_repo_root()` fails. Check implement session-env, implement keepalive, then review keepalive explicitly before falling back to cwd-based `consumer_repo_root()`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **correctness** `python/voting.py:798-815` — The accepted keepalive corpus-resolution fix is still incomplete. `_implement_repo_root_from_review_tmpdir()` treats `final_report._implement_repo_root()` as authoritative, but `python/final_report.py:143-160` falls back to `repo_roots.consumer_repo_root()` from the current cwd when implement-session anchors are missing or unusable. In `/implement` Step 5, that cwd is the plugin checkout, so a parent `session-env.sh` with no usable repo keys can make this helper return the plugin repo before it ever checks `review_tmpdir/.larch-keepalive`; likewise an implement `.larch-keepalive` `CLONE_PATH` that cannot be resolved as a Git worktree is not used as-is as the plan requires. Concrete failure: env anchors unset, plugin cwd, parent session file present but stale, and `review_tmpdir/.larch-keepalive` points at the consumer repo. The resolver returns `larch3/larch-logs`, so voters receive calibration from the plugin corpus instead of the consumer corpus. **Suggested fix:** Split the implement-anchor resolver so it only returns session-env or keepalive-derived roots, including cleaned `CLONE_PATH` as-is when `consumer_repo_root()` fails. Check implement session-env, implement keepalive, then review keepalive explicitly before falling back to cwd-based `consumer_repo_root()`.
- **Suggested revision**: Address the concern above.


### FINDING_20: **correctness** `python/voting.py:828-848` — Round 1’s design log-root fix is only partial. `_resolve_voter_calibration_log_root` reads `REPO_ROOT` from `source-env.sh` only when that key was written at session setup (`python/larch/state/session_env.py:952-954` copies `CLAUDE_PROJECT_DIR` / `REPO_ROOT` from the environment at write time and nothing else). When those env vars are unset during `write-design-env`, `source-env.sh` has no filesystem anchor, the inlined design branch does nothing, and resolution falls through to `consumer_repo_root()` from the plugin subprocess cwd. `plan_review_panel._fresh_calibration_stats_file` (`python/plan_review_panel.py:557-573`) runs with `cwd=_REPO_ROOT`, so plan-review snapshotting can still read the plugin checkout’s `larch-logs` instead of the consumer repo’s corpus. Round 2 also removed the interim `git rev-parse` fallback from the design branch, so there is no remaining tmpdir-local recovery on that path. **Suggested fix:** Persist a durable consumer repo root into design `source-env.sh` on every `/design` Step 0 write (for example always emit `REPO_ROOT` from `consumer_repo_root()` when env anchors are absent), or extend the design branch to reuse the same anchor keys implement uses (`REPO_CWD`, keepalive `CLONE_PATH`, or a shared helper). Add a regression test where plugin cwd hosts `larch-logs/`, the consumer tree hosts different data elsewhere, env anchors are unset, and `design_tmpdir/source-env.sh` lacks `REPO_ROOT`; assert snapshot `--log-root` targets the consumer tree.
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/voting.py:828-848` — Round 1’s design log-root fix is only partial. `_resolve_voter_calibration_log_root` reads `REPO_ROOT` from `source-env.sh` only when that key was written at session setup (`python/larch/state/session_env.py:952-954` copies `CLAUDE_PROJECT_DIR` / `REPO_ROOT` from the environment at write time and nothing else). When those env vars are unset during `write-design-env`, `source-env.sh` has no filesystem anchor, the inlined design branch does nothing, and resolution falls through to `consumer_repo_root()` from the plugin subprocess cwd. `plan_review_panel._fresh_calibration_stats_file` (`python/plan_review_panel.py:557-573`) runs with `cwd=_REPO_ROOT`, so plan-review snapshotting can still read the plugin checkout’s `larch-logs` instead of the consumer repo’s corpus. Round 2 also removed the interim `git rev-parse` fallback from the design branch, so there is no remaining tmpdir-local recovery on that path. **Suggested fix:** Persist a durable consumer repo root into design `source-env.sh` on every `/design` Step 0 write (for example always emit `REPO_ROOT` from `consumer_repo_root()` when env anchors are absent), or extend the design branch to reuse the same anchor keys implement uses (`REPO_CWD`, keepalive `CLONE_PATH`, or a shared helper). Add a regression test where plugin cwd hosts `larch-logs/`, the consumer tree hosts different data elsewhere, env anchors are unset, and `design_tmpdir/source-env.sh` lacks `REPO_ROOT`; assert snapshot `--log-root` targets the consumer tree.
- **Suggested revision**: Address the concern above.


### FINDING_22: **risk-integration** `python/voting.py:828-848` — Plan-review snapshot dispatch can still read the plugin checkout’s `larch-logs` when `LARCH_CONSUMER_REPO` / `CLAUDE_PROJECT_DIR` are unset and `source-env.sh` has no `REPO_ROOT`. The round-1 fix persists `REPO_ROOT` in `write-design-env` only when those env vars are present at Step 0; the inlined `design_tmpdir` branch does not call `design_lifecycle._resolve_working_tree_root` and falls through to `consumer_repo_root()` from plugin subprocess cwd. Voter prompts then get calibration feedback from the wrong corpus. **Suggested fix:** After reading `source-env.sh`, fail open only when no consumer anchor exists: persist `REPO_ROOT` on every design session from a single consumer-root probe (same authority as `final_report._implement_repo_root` / `consumer_repo_root` at session setup), or have `_resolve_voter_calibration_log_root` delegate the `design_tmpdir` branch to `design_lifecycle._resolve_working_tree_root` and reject plugin-root fallbacks for calibration snapshotting.
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **risk-integration** `python/voting.py:828-848` — Plan-review snapshot dispatch can still read the plugin checkout’s `larch-logs` when `LARCH_CONSUMER_REPO` / `CLAUDE_PROJECT_DIR` are unset and `source-env.sh` has no `REPO_ROOT`. The round-1 fix persists `REPO_ROOT` in `write-design-env` only when those env vars are present at Step 0; the inlined `design_tmpdir` branch does not call `design_lifecycle._resolve_working_tree_root` and falls through to `consumer_repo_root()` from plugin subprocess cwd. Voter prompts then get calibration feedback from the wrong corpus. **Suggested fix:** After reading `source-env.sh`, fail open only when no consumer anchor exists: persist `REPO_ROOT` on every design session from a single consumer-root probe (same authority as `final_report._implement_repo_root` / `consumer_repo_root` at session setup), or have `_resolve_voter_calibration_log_root` delegate the `design_tmpdir` branch to `design_lifecycle._resolve_working_tree_root` and reject plugin-root fallbacks for calibration snapshotting.
- **Suggested revision**: Address the concern above.


### FINDING_23: **risk-integration** `python/voting.py:828-848` — The round-1 fix for design-time log-root resolution is still incomplete. When `design_tmpdir` is set but `LARCH_CONSUMER_REPO`, `CLAUDE_PROJECT_DIR`, and `REPO_ROOT` are unset, and `source-env.sh` has no `REPO_ROOT` (normal when `session write-design-env` ran without `CLAUDE_PROJECT_DIR`/`REPO_ROOT` in the environment), the design block returns nothing and resolution falls through to `consumer_repo_root()` from the plugin subprocess cwd. Plan-review snapshot dispatch then reads the plugin checkout’s `larch-logs`, not the consumer repo’s corpus. **Suggested fix:** After the design-tmpdir branch, fail closed into “no feedback” when `design_tmpdir` was provided but no consumer root was resolved; or finish parity with `design_lifecycle._resolve_working_tree_root` and persist consumer `REPO_ROOT` into `source-env.sh` at session write. Add a regression test for design tmpdir with empty `source-env.sh` and plugin cwd.
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **risk-integration** `python/voting.py:828-848` — The round-1 fix for design-time log-root resolution is still incomplete. When `design_tmpdir` is set but `LARCH_CONSUMER_REPO`, `CLAUDE_PROJECT_DIR`, and `REPO_ROOT` are unset, and `source-env.sh` has no `REPO_ROOT` (normal when `session write-design-env` ran without `CLAUDE_PROJECT_DIR`/`REPO_ROOT` in the environment), the design block returns nothing and resolution falls through to `consumer_repo_root()` from the plugin subprocess cwd. Plan-review snapshot dispatch then reads the plugin checkout’s `larch-logs`, not the consumer repo’s corpus. **Suggested fix:** After the design-tmpdir branch, fail closed into “no feedback” when `design_tmpdir` was provided but no consumer root was resolved; or finish parity with `design_lifecycle._resolve_working_tree_root` and persist consumer `REPO_ROOT` into `source-env.sh` at session write. Add a regression test for design tmpdir with empty `source-env.sh` and plugin cwd.
- **Suggested revision**: Address the concern above.


