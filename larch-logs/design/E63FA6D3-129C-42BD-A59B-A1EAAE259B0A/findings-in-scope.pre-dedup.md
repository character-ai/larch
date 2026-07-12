### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: Branch-name derivation must spell out ref-safe RUN_DATE sanitization. Scenario: The skill already captures `RUN_DATE` as `%Y-%m-%dT%H:%M:%SZ`, which contains `:` characters illegal in git ref names. The fragment only says "ref-safe" and shows `<timestamp>` without a transform, so a literal reuse of `RUN_DATE` makes `git worktree add -b` fail before any PR is created (accepted FINDING_3 fix is still incomplete).
- **Proposed resolution**: In the shared state-publication fragment, define a separate ref-safe token (for example `date -u +%Y%m%dT%H%M%SZ` or `RUN_DATE` with `:` removed) used only for `STATE_BRANCH`, keep ISO `RUN_DATE` for `write-state`, and add a structural assertion that the branch pattern cannot contain `:` or `/`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr.py:311-330
- **Concern**: `pr create` binds to process CWD, not `--root`. Scenario: `create_main`/`create_pr_parity` always use `cwd=None`, compare `--branch` to `git.try_current_branch` in the ambient directory, and return `PR_STATUS=push_failed` when they differ. Mentioning `STATE_WORKTREE` in prose or using `git -C "$ANALYSIS_ROOT"` for worktree lifecycle is insufficient; running `python3 … pr create --branch "$STATE_BRANCH"` from `ANALYSIS_ROOT` fails even with a clean disposable worktree (FINDING_2 regression).
- **Proposed resolution**: Require an explicit subshell rooted at `STATE_WORKTREE` around `write-state`, marker `git commit --only`, `cli.py pr create`, and `gh pr merge`; extend `_structure_learn_from_bugs_specialized.py` to assert that pattern (for example `( cd "$STATE_WORKTREE" &&`) adjacent to those commands, not merely the token `STATE_WORKTREE` elsewhere in the skill.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] State branch naming still lacks a concrete ref-safe transform. Scenario: Round 1 accepted branch-naming fix is only partial: the fragment says "ref-safe" but still derives the name from raw RUN_DATE (`date -u +%Y-%m-%dT%H:%M:%SZ`, which contains `:`) and from RUN_DIR (an absolute path with `/`). Larch's own ref validator allows only `[A-Za-z0-9._/-]+`, so `git worktree add -b` can fail before any marker commit or PR.
- **Proposed resolution**: Pin one transform in the shared fragment, preferably the smaller option: `STATE_BRANCH=chore/learn-from-bugs-state-$(basename "$RUN_DIR" | sed 's/[^A-Za-z0-9._-]/-/g')` (RUN_DIR is already run-unique). If RUN_DATE must appear, add an explicit sanitize step (for example strip `:` and `T`/`Z`) and keep the existing local/remote collision reject.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: Remote branch collision preflight is required but not operationalized. Scenario: The fragment says to reject an existing local or remote branch with the chosen name, but it does not name the remote check (`git ls-remote --heads origin "$STATE_BRANCH"`) before `git worktree add -b`. A leftover remote recovery branch from a prior handoff makes branch creation or push fail with a generic git error instead of the planned collision stop.
- **Proposed resolution**: Add an explicit preflight block: abort when `git show-ref --verify --quiet "refs/heads/$STATE_BRANCH"` or `git ls-remote --exit-code --heads origin "$STATE_BRANCH"` succeeds; only then create the disposable worktree/branch.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: PR success predicate should forbid non-open failure statuses explicitly. Scenario: Round 1 FINDING_9 is only partly closed: requiring a positive `PR_NUMBER` blocks `push_failed`, but `cli.py pr create` can also emit `PR_STATUS=needs-user` (exit 3) or `PR_STATUS=error` while still printing parseable KV rows. Treating any parsed PR row as success could reach merge/durability logic on a refused create.
- **Proposed resolution**: In the shared fragment, continue only when `PR_NUMBER>0`, `PR_URL` is non-empty, and `PR_STATUS` is exactly `created` or `existing`; on `needs-user`, `push_failed`, `error`, or missing/malformed rows, stop as publication failure with no merge attempt and no durability claim.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:177-208
- **Concern**: 1. PR validation does not bind an existing PR to STATE_BRANCH and DEFAULT_BRANCH. Scenario: A PR for the branch can target a different base; the workflow can merge it and report durable publication even though the marker did not land on the default branch.
- **Proposed resolution**: Before merging, query and validate the PR number, URL, head branch, base branch, and open state. Revalidate the same identity after merging.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/skills/_structure_learn_from_bugs_specialized.py:10-184
- **Concern**: 2. Structural checks do not exercise the new publication transaction. Scenario: Textual pins can pass while the shell fence uses the wrong cwd or leaves a worktree, branch, or handoff state after write, PR, or merge failures.
- **Proposed resolution**: Add a deterministic offline harness with fake git, gh, and cli commands that verifies cwd routing, marker-only commits, cleanup, and unmerged handoff behavior.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] Branch-name derivation is not actually ref-safe. Scenario: Round 1 FINDING_3 called for ref-safe naming, but the fragment only labels RUN_DATE plus a RUN_DIR token ref-safe while Step 4 already captures RUN_DATE as ISO-8601 with colons (for example 2026-07-12T21:29:30Z). Git ref names reject :, so chore/learn-from-bugs-state-<timestamp>-<token> fails at git worktree add -b or branch create before write-state, commit, or pr create.
- **Proposed resolution**: Pin an explicit derivation: use a colon-free timestamp (date -u +%Y%m%dT%H%M%SZ) or tr ':' '-' on a branch-only component; take the token from basename "$RUN_DIR" or the mktemp suffix only; reject empty or ref-invalid characters; assert the pattern in _structure_learn_from_bugs_specialized.py.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/git/pr.py:311-326
- **Concern**: pr create must run with cwd set to STATE_WORKTREE, not only git -C on Git wrappers. Scenario: create_main and create_pr_parity pass cwd=None, so git branch detection and assert_clean_worktree use the Python process cwd. A publication fence that only git -C "$STATE_WORKTREE" on git commit but invokes python3 ... pr create from ANALYSIS_ROOT still targets the wrong checkout and can fail the clean-worktree guard or push the wrong branch.
- **Proposed resolution**: Require an explicit subshell ( cd "$STATE_WORKTREE" && ... ) around write-state, marker commit, python3 ... pr create, and post-create validation; keep git -C "$ANALYSIS_ROOT" only for worktree add/remove lifecycle; add a structural assertion that pr create is not launched from ANALYSIS_ROOT cwd.



### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:179-206
- **Concern**: Publication can erase newer proposal history. Scenario: A stale `ANALYSIS_ROOT` builds reconciled proposals without a proposal already on the fetched default branch. `write-state` then deletes that proposal, and the PR merges cleanly because its branch already includes the newer base.
- **Proposed resolution**: Merge proposal history from the fetched marker with this run's reconciled inputs using stable-ID conflict rules before `write-state`; fail closed on conflicts.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md:54,177-206
- **Concern**: [SCOPE-REDUCTION] The non-detached checkout requirement needlessly breaks an existing input. Scenario: The current contract accepts any repository checkout. A detached `--root` would now fail even though publication creates its own branch from the fetched default ref and never needs the caller branch.
- **Proposed resolution**: Keep the existing checkout contract. Validate the repository, remote, and fetched default ref, but do not require `ANALYSIS_ROOT` to have a named branch.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] Branch name derivation from RUN_DATE is not ref-safe despite the plan label. Scenario: Step 4 captures RUN_DATE as 2026-07-12T14:29:00Z; embedding that timestamp in chore/learn-from-bugs-state-<timestamp>-<token> produces colons git rejects, so publication dies before pr create on every run
- **Proposed resolution**: Derive STATE_BRANCH from a ref-safe token only (for example date -u +%Y%m%dT%H%M%SZ or ${RUN_DATE//:/}); run git check-ref-format --branch on the candidate before worktree add; keep RUN_DATE unchanged for write-state metadata



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: Default-branch resolution is required but not pinned. Scenario: The fragment says resolve and validate the default branch yet names no command; hardcoding main breaks --repo runs against repos whose default is master or another name, mis-basing the worktree and PR
- **Proposed resolution**: Pin DEFAULT_BRANCH via git -C "$ANALYSIS_ROOT" symbolic-ref --short refs/remotes/origin/HEAD with a validated fallback (design_pause.py pattern) or gh repo view --json defaultBranchRef; fetch origin/$DEFAULT_BRANCH; pass --base "$DEFAULT_BRANCH" to cli.py pr create



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: write-state argv contract is underspecified in the shared fragment. Scenario: The fragment only names --root "$STATE_WORKTREE" plus existing reconciled proposal inputs; write-state_main requires eight flags and omits --proposals-file only when no prior proposal history exists, so a partial port fails at runtime
- **Proposed resolution**: Enumerate the full write-state invocation in the fragment (--repo --search --state --selected-count --highest-closed-issue-number-scanned --run-date --scan-started-at --proposals-file "$RECONCILED_PROPOSALS_PATH") with only --root switched to STATE_WORKTREE; add a structural assertion that all required flags remain present at each of the three call sites ### 1. [correctness] `skills/learn-from-bugs/SKILL.md` — Branch name must not embed raw `RUN_DATE` The shared fragment requires a ref-safe branch name but proposes deriving it from `RUN_DATE`, which the skill already captures as ISO-8601 with colons (`%Y-%m-%dT%H:%M:%SZ`). That format is not a valid git ref segment, so `git worktree add -b …` fails on every publication attempt. Round 1 accepted branch-naming underspecification (FINDING_3); this plan still does not close it. Add a separate ref-safe token (colon-free timestamp or sanitized `RUN_DATE`), validate with `git check-ref-format --branch`, and keep `RUN_DATE` for marker metadata only. ### 2. [correctness] `skills/learn-from-bugs/SKILL.md` — Pin default-branch resolution Fetching and basing on `origin/<default-branch>` is correct, but the plan does not say how to obtain `<default-branch>`. Hardcoding `main` breaks the skill’s existing `--repo` contract for repositories whose default branch is not `main`. Follow the established `design_pause.py` pattern (`symbolic-ref refs/remotes/origin/HEAD` plus fetch) or `gh repo view --json defaultBranchRef`, then thread the resolved name through worktree creation and `cli.py pr create --base`. ### 3. [correctness] `skills/learn-from-bugs/SKILL.md` — Shared fragment must preserve the full `write-state` surface `learn-from-bugs write-state` requires `--repo`, `--search`, `--state`, `--selected-count`, `--highest-closed-issue-number-scanned`, `--run-date`, `--scan-started-at`, and usually `--proposals-file` (see `python/larch/issue/learn_from_bugs.py`). The shared fragment only swaps `--root` and refers vaguely to “existing reconciled proposal inputs,” which invites dropping required flags when replacing the two direct `ANALYSIS_ROOT` tails. Spell out the complete argv in the fragment and extend `_structure_learn_from_bugs_specialized.py` to assert it at all three marker-producing paths. **Already addressed (no new findings):** disposable worktree publication, `STATE_WORKTREE` cwd for `pr create`, default-branch base (conceptually), branch-collision rejection, strict PR identity parsing, synchronous `--admin --merge` without `--auto`, merged-state validation before durable completion, manual-merge handoff, and filing `handoff-pending` semantics all match the binding issue and prior accepted ledger rows.



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:14-18
- **Concern**: Fetched-base proposal history can be overwritten. Scenario: The reconciled input comes from `ANALYSIS_ROOT`, but `write-state` replaces the fetched default-branch marker without merging its history. A concurrent merged run can lose proposals even though this PR merges cleanly.
- **Proposed resolution**: Before writing, require every fetched marker proposal to remain compatibly represented and ordered in the reconciled input. Fail closed on missing or conflicting records, and assert this guard in the structural test.



