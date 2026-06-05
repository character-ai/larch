### FINDING_1: Python OOS routing may read the wrong state source
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Python OOS checkpoint routing is planned to read finalize-state, but OOS exits currently persist OOS_PENDING, FORKED_TARGET, and REPO_UNAVAILABLE only in ship-pr-state. This can miss continuation or skip-gate inputs when finalize-state is absent or incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep OOS_PENDING, FORKED_TARGET, and REPO_UNAVAILABLE as scoped ship-pr-state reads for Python OOS checkpoint routing, matching the existing helper, or explicitly add finalize-state writes/schema for every OOS exit path


### FINDING_2: Shared RecordingRunner migration would drop test_run_logs git_commits behavior
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Multiple reviewers identified that python/test_run_logs.py’s local RecordingRunner tracks git_commits and increments it for git commit argv, while the planned shared RecordingRunner import swap lacks that behavior. A blind migration would fail existing assertions or remove commit-count coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Leave a tiny test_run_logs-local subclass that extends the shared queue runner with git_commits tracking, or add an explicit optional call hook/counter to test_support and update those assertions accordingly
  - From Cursor-Edge: Keep a thin local subclass extending test_support.RecordingRunner with git_commits (and commit argv hook), or document that field in test_support.py; do not treat test_run_logs.py as import-only
  - From Codex-Innovation: Keep this file's tiny local subclass over test_support.RecordingRunner with git_commits, or replace those assertions with direct call-list checks during the swap.
  - From Codex-Pragmatic: Keep a small local subclass or fixture in test_run_logs that extends test_support.RecordingRunner with git_commits counting, or leave this file's runner local; avoid expanding the shared helper unless needed
  - From Cursor-Requirements: Exclude test_run_logs.py from consolidation (keep local runner with git_commits) or extend test_support with optional git_commits counting; update the nine-file count and acceptance wording accordingly
  - From Codex-Requirements: Add git_commits to test_support.RecordingRunner with the same git commit argv increment semantics before migrating test_run_logs.py, or leave test_run_logs.py on its local runner


### FINDING_3: XDG_CACHE_HOME helper may accept relative cache roots
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The planned XDG cache helper may treat a relative XDG_CACHE_HOME as an allowlisted root, making cleanup and tmpdir validation cwd-relative contrary to XDG expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use XDG_CACHE_HOME only when it is non-empty and absolute; otherwise fall back to Path.home() / ".cache"


### FINDING_4: Gap-fill can overwrite preserved PR metadata on post-merge flush-skip stalls
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The gap-fill plan lacks a regression for post-merge flush-skip stale-context behavior. A naive write from main() ctx can erase PR_NUMBER or related finalize-state metadata after run_postmerge_phase has already written newer state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add test_ship regression for post-merge flush-skip stall asserting STALL_TRACKING=true and PR_NUMBER preserved; gap-fill must read-merge-write existing finalize-state and prefer result.pr_number/pr_url/merge_result over main ctx


### FINDING_5: Quiet initialization can hide operator-visible warnings and breadcrumbs
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: After quiet_init redirects stderr, call sites that force quiet=False may write ship breadcrumbs, CI progress, or secret-scrub warnings only to the redirected log instead of the caller-visible stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Route operator-visible Python breadcrumbs and warnings through the quiet-aware path: remove quiet=False from progress/security warning call sites or add a dedicated fd4 warning helper; add a regression that a secret-scrub warning or ship breadcrumb reaches original stderr after self-initialized quiet


### FINDING_6: Contract JSON tests target stdout instead of the caller-visible FD 3 stream
- **Reviewer(s)**: Cursor-dyn-quiet-fd-contract
- **Severity**: important
- **Concern**: Planned acceptance and regression prose says contract JSON reaches stdout, but after quiet_init the contract stream is FD 3. Tests that only inspect stdout can miss swallowed contract output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-quiet-fd-contract: Rename acceptance/edge language to caller-visible contract stream via contract_stream() (FD 3 after quiet_init, sys.stdout before); add an explicit test that dup-captures FD 3 after quiet_init for journal-failure and happy-path emit_result


### FINDING_7: Plan references finalize.read_finalize_state without defining the helper
- **Reviewer(s)**: Cursor-dyn-stall-gap-fill-boundary, Codex-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Concern**: The stall gap-fill plan tells ship.py to use finalize.read_finalize_state, but finalize.py currently lacks that helper and the described finalize.py updates do not add it. Implementers may call a nonexistent API, duplicate private parsing, or rewrite finalize-state from stale context and drop preserved keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stall-gap-fill-boundary: Add read_finalize_state (thin key-based wrapper, no sourcing) under ### UPDATED: python/finalize.py alongside cache_sessions_root()
  - From Codex-dyn-stall-gap-fill-boundary: Either add read_finalize_state plus an atomic dict writer to finalize.py, or change the plan to require a local key-based parser/writer in ship.py and test preservation of existing keys.


### FINDING_8: Stall gap-fill rules are not exhaustive for pre-finalize STALLED paths
- **Reviewer(s)**: Cursor-dyn-stall-gap-fill-boundary, Codex-dyn-stall-gap-fill-boundary
- **Severity**: important
- **Concern**: The gap-fill plan focuses on one early ensure_pr example and omits or underspecifies other valid-tmpdir STALLED exits, including exception conversions and rebase Stalled paths. These paths can lack finalize-state or PR metadata, causing Step 18 to miss stall recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stall-gap-fill-boundary: In _persist_stall_metadata_if_needed populate PR_NUMBER/PR_URL/MERGE_RESULT from non-empty ShipResult fields then key-parse ship-pr-state.sh (ctx.state_file) when finalize-state lacks them; add one regression for rebase Stalled without pre-existing finalize-state.sh
  - From Codex-dyn-stall-gap-fill-boundary: Define the rule generically: for any Outcome.STALLED after run_ship/exception conversion with an allowed tmpdir and no existing STALL_TRACKING=true, write merged stall metadata, with invalid-tmpdir as the explicit no-write exception. Add at least one regression outside ensure_pr.


### FINDING_9: Invalid-tmpdir Exit 4 path lacks a pinned JSON fallback/no-write regression
- **Reviewer(s)**: Codex-dyn-stall-gap-fill-boundary
- **Severity**: latent
- **Concern**: The plan describes invalid tmpdir behavior as JSON-only, but the test strategy does not pin that finalize-state must remain absent and routing must fall back to JSON details. Future edits could accidentally require finalize-state on a path that deliberately refuses to write it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stall-gap-fill-boundary: Add a minimal structural pin for “finalize-state absent → JSON detail fallback” on the Python Exit 4 path, and a unit test that invalid tmpdir returns STALLED JSON without writing finalize-state.

