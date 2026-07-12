### FINDING_1: Ref-safe state branch name
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The publication branch must not reuse ISO `RUN_DATE` containing `:` characters, which are invalid in Git ref names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the shared state-publication fragment, define a separate ref-safe token (for example `date -u +%Y%m%dT%H%M%SZ` or `RUN_DATE` with `:` removed) used only for `STATE_BRANCH`, keep ISO `RUN_DATE` for `write-state`, and add a structural assertion that the branch pattern cannot contain `:` or `/`.
  - From Cursor-Requirements: Add a separate ref-safe token (colon-free timestamp or sanitized `RUN_DATE`), validate with `git check-ref-format --branch`, and keep `RUN_DATE` for marker metadata only.


### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] State branch naming still lacks a concrete ref-safe transform. Scenario: Round 1 accepted branch-naming fix is only partial: the fragment says "ref-safe" but still derives the name from raw RUN_DATE (`date -u +%Y-%m-%dT%H:%M:%SZ`, which contains `:`) and from RUN_DIR (an absolute path with `/`). Larch's own ref validator allows only `[A-Za-z0-9._/-]+`, so `git worktree add -b` can fail before any marker commit or PR.
- **Proposed resolution**: Pin one transform in the shared fragment, preferably the smaller option: `STATE_BRANCH=chore/learn-from-bugs-state-$(basename "$RUN_DIR" | sed 's/[^A-Za-z0-9._-]/-/g')` (RUN_DIR is already run-unique). If RUN_DATE must appear, add an explicit sanitize step (for example strip `:` and `T`/`Z`) and keep the existing local/remote collision reject.


### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] Branch-name derivation is not actually ref-safe. Scenario: Round 1 FINDING_3 called for ref-safe naming, but the fragment only labels RUN_DATE plus a RUN_DIR token ref-safe while Step 4 already captures RUN_DATE as ISO-8601 with colons (for example 2026-07-12T21:29:30Z). Git ref names reject :, so chore/learn-from-bugs-state-<timestamp>-<token> fails at git worktree add -b or branch create before write-state, commit, or pr create.
- **Proposed resolution**: Pin an explicit derivation: use a colon-free timestamp (date -u +%Y%m%dT%H%M%SZ) or tr ':' '-' on a branch-only component; take the token from basename "$RUN_DIR" or the mktemp suffix only; reject empty or ref-invalid characters; assert the pattern in _structure_learn_from_bugs_specialized.py.


### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md:54,177-206
- **Concern**: [SCOPE-REDUCTION] The non-detached checkout requirement needlessly breaks an existing input. Scenario: The current contract accepts any repository checkout. A detached `--root` would now fail even though publication creates its own branch from the fetched default ref and never needs the caller branch.
- **Proposed resolution**: Keep the existing checkout contract. Validate the repository, remote, and fetched default ref, but do not require `ANALYSIS_ROOT` to have a named branch.


### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Shared state-publication fragment
- **Concern**: [SCOPE-REDUCTION] Branch name derivation from RUN_DATE is not ref-safe despite the plan label. Scenario: Step 4 captures RUN_DATE as 2026-07-12T14:29:00Z; embedding that timestamp in chore/learn-from-bugs-state-<timestamp>-<token> produces colons git rejects, so publication dies before pr create on every run
- **Proposed resolution**: Derive STATE_BRANCH from a ref-safe token only (for example date -u +%Y%m%dT%H%M%SZ or ${RUN_DATE//:/}); run git check-ref-format --branch on the candidate before worktree add; keep RUN_DATE unchanged for write-state metadata


