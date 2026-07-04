### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/skill_closure_ledger.py
- **Concern**: --since-tag ref validation must use the resolved --root as git cwd. Scenario: FINDING_3 pins cwd=root for log_path_commits and show_file only. Tag filtering still calls git rev-parse --verify separately. Running from another checkout while passing --root can validate a tag in the ambient repo (or fail) while history reads use root, yielding empty or wrong post-tag summaries.
- **Proposed resolution**: In the Tag filtering section, require tag rev-parse --verify (and any follow-on git calls) through the same ProcRunner/git._run path with cwd=resolved root, matching log_path_commits and show_file.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/lint/test_skill_closure_ledger.py
- **Concern**: Missing fixture proving --root decouples from process cwd. Scenario: --root exists so operators can aim history reads at a specific tree. Fixture tests initialize the repo and likely run with cwd aligned to root, so omitting cwd on tag rev-parse would not be caught.
- **Proposed resolution**: Add one ledger test that keeps the process cwd outside the fixture repo, passes --root to the repo path, and asserts correct history or a since-tag failure for a tag that exists only in that repo.

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/skill_closure_ledger.py planned via plan.txt:51-53
- **Concern**: Prior accepted since-tag fix remains incomplete: non-ancestor tags are not rejected. Scenario: `--since-tag` on a tag that resolves to a commit outside `HEAD` history still lets `TAG..HEAD -- python/skill-closure-baseline.json` return a set difference, so the summary can include most of history instead of commits after the tag
- **Proposed resolution**: After resolving `TAG^{commit}`, reject when the peeled commit is not an ancestor of `HEAD`, then build the rev range from the peeled SHA, for example `peeled..HEAD`; reuse existing git ancestry plumbing rather than adding broader machinery

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/skill_closure_ledger.py
- **Concern**: Since-tag mode still omits the ancestry check accepted in FINDING_2. Scenario: The plan peels and validates the tag with `rev-parse --verify '<TAG>^{commit}'` and ranges with `<TAG>..HEAD`, but never requires that the peeled commit is an ancestor of `HEAD`. A tag that resolves but is not on the current branch history can make `TAG..HEAD` include commits that are not "since release," so `--since-tag` summaries misattribute per-target deltas for release planning.
- **Proposed resolution**: After resolving the peeled SHA, call existing `git.is_ancestor(runner, peeled_sha, "HEAD", cwd=root)`; exit 2 with a stderr message naming the tag when false. Add a fixture where the tag points at a non-ancestor commit and assert exit 2.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:51-53
- **Concern**: Accepted since-tag ancestry fix is incomplete. Scenario: An unrelated or sibling tag that resolves to a commit still passes rev-parse; TAG..HEAD can then report a misleading full or partial ledger instead of rejecting an invalid release baseline.
- **Proposed resolution**: After peeling the tag with rev-parse TAG^{commit}, verify the peeled commit is an ancestor of HEAD via existing git.is_ancestor or merge-base --is-ancestor, then build the rev range from the peeled commit.
