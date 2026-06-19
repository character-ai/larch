# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: test_admission.py lacks plan-required gh remote-repo argv assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Plan-required CLI argv assertions for `gh remote-repo` were not added; tests still mock `_github_remote_repo`. A subprocess argv regression in `admission.fork_env` could pass CI while fork-env resolution fails in real runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Stub _run/subprocess.run and assert [sys.executable, cli.py, gh, remote-repo, remote] argv.


### FINDING_5: conflict-resolution.md Phase 4 invokes cli.py without python3
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: blocking
- **Concern**: Phase 4 continue instructions replaced the executable bash helper with a bare `${CLAUDE_PLUGIN_ROOT}/python/cli.py ...` command. `python/cli.py` is meant to be invoked via `python3`, and it is checked in without an executable bit or shebang, so any early-rebase or `ship_pr_pre_push` conflict that reaches Phase 4 will fail before continuing the rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Change the three Phase 4 commands to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push rebase --continue --no-push --keep-on-conflict`, including the retry after `git-rebase-skip.sh`, and pin this in the structural harness.


### FINDING_9: test-step-7a.sh checkpoint-probe stub omits ROUTE= emissions
- **Reviewer(s)**: dyn-step7a-harness-output.txt
- **Severity**: important
- **Concern**: The `push checkpoint-probe` dispatcher stub prints only `REBASE_OUTCOME` / `CONFLICT_FILES` / `REBASE_ERROR`, but production `python/push.py` always emits `ROUTE=continue|conflict|bail` (`_emit_rebase_checkpoint_keys`, lines 193-208). The same branch updates `skills/implement/SKILL.md` (line 739) to require the `/implement` orchestrator to read `ROUTE=` from `implement step-7a` relay stdout, yet no harness case asserts `ROUTE=` on green, conflict, failed, or unexpected-rc paths. A stub that omits `ROUTE=` can pass while breaking the 7a.r routing contract the skill now documents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step7a-harness-output.txt: Mirror production in the stub (`ROUTE=continue` on ok, `ROUTE=conflict` on conflict, `ROUTE=bail` on failed/unexpected) and add `assert_contains "ROUTE=…"` checks in `green`, `rebase-conflict`, `rebase-failed`, and `rebase-unexpected-rc`.


