## Review Phase Detail

No review rounds completed.

## Exec Issues and Warnings
Exec Issues (0):
Warnings (11):
  1. The change achieves its stated target and is well built, but it carries one meaningful guideline deviation on the git side.
  2. ## What the change does well
  3. It is a sound application of G-Skill-2: the ~232-line inline publication fence in `skills/learn-from-bugs/SKILL.md` is replaced by a thin fence that delegates the whole flow to a new `learn-from-bu...
  4. ## Deviation: G-Py-7 (wrap git/gh as typed functions over the injected Runner; avoid ad-hoc returncode checks)
  5. The new code in `python/larch/issue/learn_from_bugs.py` imports only `gh` from `larch.git`, then introduces a local `_git(runner, root, args)` shim that returns a raw `CommandResult` and performs m...
  6. `_reserve_branch` and `_cleanup_worktree` run `show-ref --verify --quiet refs/heads/<branch>` raw; this is exactly `git.local_branch_exists`.
  7. `_commit_marker` runs `diff-tree --no-commit-id --name-only -r HEAD` raw; this is exactly `git.diff_tree_name_only`.
  8. `_reserve_branch` runs `ls-remote --exit-code --heads origin refs/heads/<branch>` raw and hand-codes the rc==0 / rc!=2 trichotomy; this reimplements `git.remote_branch_state` and, in doing so, drop...
  9. `_resolve_default_branch`'s `fetch origin <refspec>` and `_commit_marker`'s `add`/`commit --only` bypass `git.fetch`, `git.add`, and `git.commit`; the raw `add`/`commit` also skip the `_assert_bran...
  10. The result is internally inconsistent within the same new function set: gh operations go through the typed seam while git operations go through ad-hoc returncode checks, which is the exact "call si...
  11. This is bounded and non-blocking. G-Py-7 is aspirational; the code is functionally correct; and some raw calls (`rev-parse --is-inside-work-tree`, `remote get-url`, `check-ref-format`, `switch -c`,...

## Architectural invariants

This change is clean against the architectural invariants.

The change migrates the `/learn-from-bugs` state-publication flow out of the inline Bash fence in `skills/learn-from-bugs/SKILL.md` and into a new `learn-from-bugs state-publish` verb in `python/larch/issue/learn_from_bugs.py`, registered in `python/larch/cli.py`, with offline tests and an updated structure test. Nothing in the changed code weakens a workflow, run-log, panel, agent-contract, or ship-lifecycle guarantee:

- The merge-durability decision in `_resolve_pr_outcome` is computed from independently re-read GitHub state (`pr view --json state` and `--json mergedAt`), never from metadata the publishing flow declared about itself, so no hard gate is disarmed by self-reported data.
- The disposable-worktree publish and cleanup paths (`_publish_in_worktree`, `_cleanup_worktree`) remove only the local worktree and, where appropriate, the local branch; they perform no rebase, force-push, reopen, or other pre-merge mutation against an already-created, merged, or closed pull request, and a pull request that is not `OPEN` is refused rather than mutated.
- The old on-disk phase sentinels (`state-publication-phase`, `-committed`, `-pr-created`) are replaced by in-memory `_PublishProgress` state consumed within the same invocation, so no persisted result is reused against inputs that have since changed.
- The remaining invariants govern surfaces this change does not touch: pause snapshots, run-log flush completeness, committed-artifact field embedding, committed in-flight outcome labels, per-slot panel records, and machine-ingested agent verdicts.

## Architectural guidelines

This change is clean against the architectural guidelines; the git-wrapping deviation the prior assessment raised is resolved.

The prior note flagged that the new code drove GitHub operations through the typed `larch.git` seam while six git operations went through a local `_git` shim with ad-hoc `returncode` checks, duplicating helpers that already exist in the shared typed git module. The current diff routes each of those six operations through its typed equivalent:

- the local-branch collision checks in `_reserve_branch` and `_cleanup_worktree` now call `git.local_branch_exists`;
- the remote-branch collision check in `_reserve_branch` now calls `git.remote_branch_state` instead of hand-coding the `ls-remote` exit-code trichotomy;
- the marker-only commit verification in `_commit_marker` now calls `git.diff_tree_name_only`;
- the default-branch fetch in `_resolve_default_branch` now calls `git.fetch`; and
- the marker staging and `--only` commit in `_commit_marker` now call `git.add` and `git.commit`.

I confirmed each of these helpers exists in `python/larch/git/git.py` (`local_branch_exists`, `remote_branch_state`, `diff_tree_name_only`, `fetch`, `add`, `commit`). The local `_git` shim remains, but only for operations that have no typed wrapper in that module: the `rev-parse --is-inside-work-tree`, `remote get-url`, `check-ref-format`, and `rev-parse --verify` existence/validity probes (which the code deliberately converts into precise domain error tokens rather than the shared read helper's generic raise), and the `switch -c`, `worktree add`/`remove`, and `branch -D` mutations. A repository grep for wrappers named for these operations returns none, so each is a genuine one-shot probe or mutation with no typed equivalent, which is exactly the residual case the guideline permits. The gh side already routes through `gh.command` and `gh.pr_merge`, so the internal inconsistency the prior note described is gone.

The rest of the change is a sound application of the keep-logic-in-Python-behind-`cli.py` direction and reads well against the other guidelines: the ~232-line inline fence collapses to a thin delegation to `learn-from-bugs state-publish`; the flow is fully injectable through the `Runner` seam with offline tests covering the success, collision, remote-check-failure, worktree-collision, PR-create-failure, and unmerged-handoff branches; composite inputs and outputs are frozen dataclasses; status and reason tokens are single-definition module `Final` constants; the merge outcome is decided by re-reading the mutated PR; failures are caught narrowly (`StatePublishError`) and re-raised after cleanup; and the `PUBLICATION_STATUS`/`PUBLICATION_RESULT` to `STATE_PUBLISH_STATUS` grammar rename is swept atomically across the SKILL fence, its prose consumers, and `python/tests/skills/_structure_learn_from_bugs_specialized.py`, with the new machine-stdout key registered and the old inline publication Bash asserted absent.

## /implement run FF5BBC91-EBEF-450E-B70F-22646B2E6D20: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 01:22:21
- **Cost**: 💰 TOTAL ~$35.57: Claude $35.19, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.38  |  Tokens: 36395k
- **Issue**: #7317: https://github.com/character-ai/larch/issues/7317
- **Plan review**: N/A
- **Plan coverage**: 0/0 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: N/A
- **Code review**: 0/1 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 11
- **Run logs**: `larch-logs/implement/FF5BBC91-EBEF-450E-B70F-22646B2E6D20/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 53.1.5

<!-- larch:run-summary v=1 -->
