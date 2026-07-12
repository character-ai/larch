### FINDING_1: Publication cannot pass the clean-worktree guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-State Pr Flow Auditor, Codex-dyn-State Pr Flow Auditor
- **Severity**: major
- **Concern**: Filing artifacts and unrelated working-tree changes remain outside the marker-only commit, but `python/cli.py pr create` requires a clean worktree. Publication therefore fails after the local marker commit.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Spell out a minimum-change remediation before `pr create` (e.g. `git -C "$ANALYSIS_ROOT" stash push --message learn-from-bugs-filing -- larch-logs/shared/learn-from-bugs-filing/` with bounded pop/restore after PR creation, or another approach that preserves retry artifacts without shipping them on the marker branch); pin it in the shared fragment and structural tests
  - From Codex-Arch: Publish from an isolated clean worktree, or add a narrowly scoped publication path that preserves unrelated changes without weakening the global guard
  - From Cursor-Innovation: Before pr create, add an explicit pre-publication step: snapshot retry artifacts under RUN_DIR, remove or relocate learn-from-bugs-filing/ from ANALYSIS_ROOT porcelain, then run pr create; retain RUN_DIR copies for retry until merge or handoff completes
  - From Codex-Innovation: Publish from an isolated clean worktree containing only the marker commit, while preserving the caller checkout and filing retry artifacts.
  - From Cursor-Pragmatic: In the shared publication fragment, stash or temporarily relocate `learn-from-bugs-filing/` paths (or otherwise clear porcelain) immediately before `pr create`, then restore; or defer durable filing copies until after PR creation while keeping retry state in `$RUN_DIR` until `/issue` succeeds
  - From Codex-Pragmatic: Publish from a temporary worktree based on the remote default branch. Run write-state and PR creation there, then clean it up while preserving ANALYSIS_ROOT.
  - From Codex-Requirements: Publish from a disposable worktree based on the resolved default branch, preserving the operator checkout
  - From Cursor-dyn-State Pr Flow Auditor: In filing mode, spell out how the publication fragment leaves a clean tree: e.g. include the three filing paths in the same --only commit on the state branch, isolate marker work in a git worktree (python/larch/design/design_log_publish_flow.py:450-507), or keep retry copies in RUN_DIR until after merge and stop writing them into ANALYSIS_ROOT before pr create.
  - From Codex-dyn-State Pr Flow Auditor: Move retry artifacts outside the checkout or fail before `write-state` when the tree is dirty. Do not rely on the clean guard after preserving dirty files.
  - From Cursor-Pragmatic: Document a hard precondition or add a preflight `git -C "$ANALYSIS_ROOT" status --porcelain` check with a clear stop message before branch creation


### FINDING_2: Publication commands must use the analysis checkout
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-State Pr Flow Auditor
- **Severity**: major
- **Concern**: `pr create` uses the process working directory rather than `ANALYSIS_ROOT`, so branch detection and publication can target the wrong checkout.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Mandate a subshell such as `( cd "$ANALYSIS_ROOT" && python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr create --repo "$REPO" --branch "$STATE_BRANCH" ... )` for every publication path; add a structural assertion that `cd "$ANALYSIS_ROOT"` (or equivalent) precedes `pr create`
  - From Cursor-Pragmatic: Wrap branch/commit/`pr create`/`gh pr merge` in an explicit `git -C "$ANALYSIS_ROOT"` or `(cd "$ANALYSIS_ROOT" && …)` subshell in the shared fragment; pin that in `_structure_learn_from_bugs_specialized.py`
  - From Cursor-Requirements: Wrap the publication fence in `(cd "$ANALYSIS_ROOT" && python3 ... pr create ...)` (or equivalent), pin `--branch` to the state branch, and add a structural assertion that `pr create` is anchored to `ANALYSIS_ROOT`
  - From Cursor-dyn-State Pr Flow Auditor: Make the shared fragment cd "$ANALYSIS_ROOT" once (or use a subshell) before checkout, marker commit, pr create, and gh pr merge; pin this in the SKILL bash fence and structural tests. Do not mix git -C for some steps and uncwd pr create for others.


### FINDING_3: Branch base and naming are underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-State Pr Flow Auditor
- **Severity**: major
- **Concern**: The proposed branch can inherit unrelated commits, use an invalid date token, or collide on repeated runs.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Add explicit Bash steps: verify non-detached HEAD in `ANALYSIS_ROOT`, `git -C "$ANALYSIS_ROOT" fetch origin main` (or documented base), `checkout -B`/`checkout -b` with a collision suffix (timestamp or `RUN_DIR` token), then marker-only commit; reject and stop when branch creation fails
  - From Cursor-Innovation: Add create-branch-from-base steps: fetch origin/main, reject detached HEAD, create the state branch from origin/main (or document python/cli.py pr create-branch with base-remote/base-ref), then write-state, marker-only commit, and pr create on that branch
  - From Cursor-Innovation: Pin a ref-safe suffix (for example UTC YYYY-MM-DD or a RUN_ID slug) and document same-day collision handling (suffix counter or reuse existing open PR) in the shared fragment and structural tests
  - From Codex-Pragmatic: Include a sanitized RUN_DATE timestamp or another unique run suffix in the branch name.
  - From Cursor-Requirements: Add explicit steps: `git -C "$ANALYSIS_ROOT" fetch origin main`, create the state branch from `origin/main` (or `main`), then `write-state`, marker-only commit, and PR create on that branch only
  - From Codex-Requirements: Use a unique timestamp or run identifier in the branch name and retain recovery branches only when needed
  - From Codex-dyn-State Pr Flow Auditor: Use a run-unique branch name, or reuse a colliding branch only after verifying its expected marker commit and route it through parsed existing-PR handling.


### FINDING_5: Merge success must be synchronous and validated
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: `--auto` may only schedule a later merge, and `--admin --auto` may be an invalid flag combination. Treating command success as merged durability is unsafe.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Verify `mergedAt` or merged state after the command; otherwise retain pending state and provide the PR URL as a manual or pending-merge handoff
  - From Codex-Pragmatic: Remove --auto for the admin attempt, or verify the PR is merged before recording success. Treat every unmerged state as a manual handoff.
  - From Codex-Requirements: Use `gh pr merge "$PR_NUMBER" --repo "$REPO" --admin --merge` and update the structural assertion


### FINDING_6: Durability and pending-state completion are stated too early
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-State Pr Flow Auditor, Codex-dyn-State Pr Flow Auditor
- **Severity**: major
- **Concern**: Contract prose and default-mode progression can treat a local marker or PR creation as durable even though the marker is not merged into the default branch.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Update Contract exception (a) and both marker tails to require the shared publication fragment (PR created, then merge success or manual-merge handoff) before durability/pending completion; extend structural checks for the new pending-completion wording
  - From Cursor-Innovation: Gate default-mode Step 5 on merge success or an explicit manual-merge handoff; synchronously run merge (or ci wait plus merge pr) before Step 5, and do not treat PR creation alone as durable publication
  - From Cursor-Innovation: Define completion criteria: clear pending-state only after confirmed merge, or after a failed merge handoff that records PR_URL and leaves pending-state status handoff-pending for operator retry
  - From Cursor-Requirements: Update bullet (a) to durable marker publication (PR created, plus merge or explicit manual-merge handoff) and align the Step 4 / filing-mode headings that still say "marker commit"
  - From Cursor-dyn-State Pr Flow Auditor: Update exception (a) to require successful publication (PR created plus merge or explicit manual-merge handoff), not write-state or local commit alone.
  - From Codex-dyn-State Pr Flow Auditor: Keep pending state pending until parsed PR identity exists and a PR read proves `MERGED`; otherwise retain it or emit a valid manual-handoff state with the PR URL.


### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Approach
- **Concern**: [SCOPE-REDUCTION] `--auto` on merge is not required by the issue and can report success before main updates. Scenario: Issue asks for admin merge or manual operator merge; `gh pr merge --admin --merge --auto` can exit 0 while only enabling auto-merge, so pending-state/durability may clear before `learn-from-bugs-state.json` lands on main
- **Proposed resolution**: Use `gh pr merge --admin --merge` first; reserve manual handoff on failure; treat `--auto` only as an explicit fallback, and verify `state=MERGED` (or keep pending state) before marking filing complete


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: [SCOPE-REDUCTION] `--auto` on merge conflicts with issue merge semantics. Scenario: Issue asks to merge with `--admin` when available, otherwise hand off; `--auto` only enables deferred auto-merge and can exit without landing the marker on main while claiming publication success
- **Proposed resolution**: Attempt immediate `gh pr merge "$PR_NUMBER" --repo "$REPO" --admin --merge`; on failure, preserve the open PR URL and ask the operator to merge manually


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


