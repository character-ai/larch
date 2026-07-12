---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3: Preflight local and remote branch collisions
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Branch-collision rejection is not operationalized for existing remote branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit preflight block: abort when `git show-ref --verify --quiet "refs/heads/$STATE_BRANCH"` or `git ls-remote --exit-code --heads origin "$STATE_BRANCH"` succeeds; only then create the disposable worktree/branch.


### [Plan Review] FINDING_4

### FINDING_4: Require a successful PR status
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Parseable PR output is insufficient; `needs-user`, `push_failed`, and `error` statuses must not proceed to merge or durability claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the shared fragment, continue only when `PR_NUMBER>0`, `PR_URL` is non-empty, and `PR_STATUS` is exactly `created` or `existing`; on `needs-user`, `push_failed`, `error`, or missing/malformed rows, stop as publication failure with no merge attempt and no durability claim.


### [Plan Review] FINDING_5

### FINDING_5: Validate PR identity and branches
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: A PR must be verified as open and bound to both `STATE_BRANCH` and `DEFAULT_BRANCH` before merging, then revalidated after merging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Before merging, query and validate the PR number, URL, head branch, base branch, and open state. Revalidate the same identity after merging.


### [Plan Review] FINDING_6

### FINDING_6: Exercise the publication transaction structurally
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: Textual structural pins do not verify CWD routing, marker-only commits, cleanup, or unmerged handoff behavior across failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a deterministic offline harness with fake git, gh, and cli commands that verifies cwd routing, marker-only commits, cleanup, and unmerged handoff behavior.


### [Plan Review] FINDING_8

### FINDING_8: Pin default-branch resolution
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The workflow must resolve the repository’s actual default branch rather than assuming `main`, and use it consistently for fetch, worktree creation, and PR base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin DEFAULT_BRANCH via git -C "$ANALYSIS_ROOT" symbolic-ref --short refs/remotes/origin/HEAD with a validated fallback (design_pause.py pattern) or gh repo view --json defaultBranchRef; fetch origin/$DEFAULT_BRANCH; pass --base "$DEFAULT_BRANCH" to cli.py pr create
  - From Cursor-Requirements: Follow the established `design_pause.py` pattern (`symbolic-ref refs/remotes/origin/HEAD` plus fetch) or `gh repo view --json defaultBranchRef`, then thread the resolved name through worktree creation and `cli.py pr create --base`.


### [Plan Review] FINDING_9

### FINDING_9: Preserve the complete write-state argument contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: Replacing the existing marker-writing paths must retain every required `write-state` argument and only change the root to `STATE_WORKTREE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Enumerate the full write-state invocation in the fragment (--repo --search --state --selected-count --highest-closed-issue-number-scanned --run-date --scan-started-at --proposals-file "$RECONCILED_PROPOSALS_PATH") with only --root switched to STATE_WORKTREE; add a structural assertion that all required flags remain present at each of the three call sites
  - From Cursor-Requirements: Spell out the complete argv in the fragment and extend `_structure_learn_from_bugs_specialized.py` to assert it at all three marker-producing paths.


---LARCH-REJECTED-END---
