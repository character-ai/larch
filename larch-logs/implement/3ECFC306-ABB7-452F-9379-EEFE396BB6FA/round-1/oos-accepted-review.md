### OOS_1: [OUT_OF_SCOPE] Step 2b repo-root resolution lacks fail-loud guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-orchestration-output.txt, dyn-shell-robustness-output.txt, dyn-doc-coverage-output.txt
- **Severity**: important
- **Concern**: `git rev-parse --show-toplevel` is assigned without an explicit exit/non-empty check. Outside a git worktree or on git failure, Step 2b can pass an empty repo root to the drafter launcher or abort unexpectedly, producing a generic fallback instead of an operator-visible repo-root error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add explicit rev-parse guard with loud stderr/exit or a dedicated skip reason before launching the drafter.
  - From cursor-specialist-correctness-output.txt: After git -C "$PWD" rev-parse --show-toplevel, explicitly test exit status and non-empty _repo_root; print a loud **⚠ 2b:** error and skip drafter rather than treating it as launcher rc failure.
  - From cursor-specialist-edge-cases-output.txt: Capture rev-parse rc explicitly and emit a dedicated Step 2b warning or set _step2b_drafter_skip_reason before skipping the launcher
  - From dyn-orchestration-output.txt: Capture with an explicit guard before `set +e`, e.g. `_repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)"` followed by `[[ -n "$_repo_root" ]] || { printf ...; _drafter_rc=2; ... }`, matching the plan’s fail-loud intent.
  - From dyn-shell-robustness-output.txt: Resolve repo root with an explicit guard before `set +e`, e.g. `_repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)"` plus `[[ -n "$_repo_root" ]] || { printf …; _step2b_drafter_skip_reason=not-in-git-repo; _drafter_rc=2; }`, or run rev-parse only after `set +e` and branch on `$?`.
  - From dyn-doc-coverage-output.txt: After `rev-parse`, test `$?` (or `[[ -n "$_repo_root" ]]`) and emit an explicit operator-visible `**⚠ 2b:**` error before skipping the launcher or setting `_step2b_drafter_skip_reason`.


### OOS_2: [OUT_OF_SCOPE] Voting protocol docs conflict with dispatcher ownership and no-backfill policy
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-orchestration-output.txt
- **Severity**: latent
- **Concern**: `skills/shared/voting-protocol.md` still contains prose/direct wait examples that can make orchestrators re-run sentinel waits or expect unavailable external voters to be backfilled, conflicting with dispatcher-owned waiting and shrink-only panel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Remove the direct wait block or rewrite it as dispatcher-internal behavior documented in the dispatcher contracts.
  - From cursor-specialist-edge-cases-output.txt: Update example to match dispatch-plan-voters.sh sentinel set
  - From dyn-orchestration-output.txt: Align lines 55 and 71 with the #3207 policy (Claude always + available externals only; no Claude replacement for unavailable slots), and state explicitly that `dispatch-plan-voters.sh` owns sentinel waiting so orchestrators must not re-run `wait-for-reviewers.sh` on the `/design` plan path.


