### FINDING_1: Fork and skip paths must not republish argv ISSUE_NUMBER in bootstrap stdout
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-kv-emit-table-sync, Codex-dyn-kv-emit-table-sync
- **Severity**: important
- **Concern**: Planned `emit_final_tail` (and related KV table) uses `${ISSUE_NUMBER_RESOLVED:-${ISSUE_NUMBER_OPT:-}}` so when fork carve-out / `forked-target-skip` (and optionally repo-unavailable) leaves `ISSUE_NUMBER_RESOLVED` empty while `--issue-number` still passes the upstream design id, stdout can emit a non-empty `ISSUE_NUMBER`, breaking GP3 expectations, fork “ISSUE_NUMBER unset” contract, and downstream Closes / PR routing that must not treat the upstream id as adopted local tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define a dedicated emitted field (e.g. ISSUE_NUMBER_KV) or use a sentinel unset vs empty convention (e.g. only fall back when a branch sets a use-argv flag); fork and repo-unavailable skips must force empty ISSUE_NUMBER on stdout regardless of argv.
  - From Codex-Arch: Make emit_final_tail suppress the ISSUE_NUMBER fallback when BRANCH_SELECTED=forked-target-skip, or add an explicit tracking-issue-adopted flag and only fallback for non-fork/no-tracking phases
  - From Cursor-Edge: For BRANCH_SELECTED forked-target-skip or repo-unavailable-skip emit empty ISSUE_NUMBER or add ISSUE_NUMBER_EMITTED key do not fall back to OPT on those paths
  - From Codex-Edge: Make ISSUE_NUMBER emission branch-aware: for BRANCH_SELECTED=forked-target-skip emit an empty ISSUE_NUMBER, and keep the GP3 assertion. Only use ISSUE_NUMBER_OPT fallback for non-fork parser-stability paths where that is intentional.
  - From Cursor-Innovation: When BRANCH_SELECTED=forked-target-skip (or FORKED_TARGET true), emit empty ISSUE_NUMBER or set a dedicated suppress flag parsed in emit_final_tail; align harness + SKILL fork note with that rule
  - From Codex-Innovation: Special-case forked-target-skip so ISSUE_NUMBER emits empty, and carry the upstream issue in a separate variable such as UPSTREAM_DESIGN_ISSUE
  - From Cursor-Pragmatic: Define tail emission rule: e.g. emit empty ISSUE_NUMBER when BRANCH_SELECTED=forked-target-skip (or when FORKED_TARGET=true), and align GP3 + implement-bootstrap.md + SKILL fork note with that rule
  - From Codex-Pragmatic: Add an explicit suppress/local-adoption flag for fork mode, or make emit_final_tail fall back to ISSUE_NUMBER_OPT only for infra/no-tracking paths and not when BRANCH_SELECTED=forked-target-skip.
  - From Cursor-Requirements: Emit empty ISSUE_NUMBER when BRANCH_SELECTED is forked-target-skip (or set ISSUE_NUMBER_RESOLVED to empty and disable OPT fallback for that branch) and align GP3 plus SKILL fork note with the same rule
  - From Codex-Requirements: Change emit_final_tail or phase_tracking to suppress ISSUE_NUMBER_OPT fallback for forked-target-skip, and keep the GP3 assertion
  - From Cursor-dyn-kv-emit-table-sync: Teach emit_final_tail (or carve-outs) to emit empty ISSUE_NUMBER on forked-target-skip (and document repo_unavailable-skip the same way if desired) or drop argv fallback on those branches; align plan.txt L210-211 and harness GP3 with the chosen rule
  - From Codex-dyn-kv-emit-table-sync: Make ISSUE_NUMBER emission branch-aware: for BRANCH_SELECTED=forked-target-skip emit empty even when ISSUE_NUMBER_OPT is set. Limit ISSUE_NUMBER_OPT fallback to infra/no-tracking and explicit preserve-subject bail paths, or add a TRACKING_ISSUE_SUPPRESSED flag and document it in scripts/implement-bootstrap.md.


### FINDING_10: Document and normalize `STEP_FAILED=get-issue-state` exit 2 for the new tracking bootstrap path
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Adding `STEP_FAILED=get-issue-state` exit 2 inside tracking bootstrap is not reflected in the infra bootstrap operator-facing exit-2 table / `_ib_rc==2` branching, so operators may see generic exit 2 without the keyed guidance used for other failure classes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend SKILL infra block (and implement-bootstrap.md exit table) with a third keyed STEP_FAILED=get-issue-state path plus normalized message; ensure collapsed Step0 tracking section references it
  - From Cursor-Requirements: Extend planned SKILL collapse with explicit rc=2 handling for STEP_FAILED=get-issue-state mirroring stderr guidance used for get-issue-state failures today


### FINDING_12: Plan harness sections disagree on case count and helper naming
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-kv-emit-table-sync, Codex-dyn-kv-emit-table-sync
- **Severity**: nit
- **Concern**: Plan text alternates seven vs eight new harness cases; lists may not match enumerated GP-adopt / GP2 / GP3 / B* rows; references `setup_sandbox()` while harness uses `build_sandbox()`—scope and grep targets drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reconcile lines plan.txt:239 plan.txt:252-262 plan.txt:333 to a single integer and ordered list.
  - From Cursor-Edge, Cursor-Innovation: Align prose to eight cases or enumerate seven explicitly excluding one
  - From Cursor-Pragmatic: Reconcile counts (GP-adopt GP2 GP3 B1 B2 B3 B5 B6 = 8) and use the real harness function name throughout
  - From Cursor-Requirements: Reconcile counts so every section lists the same eight cases GP-adopt GP2 GP3 B1 B2 B3 B5 B6
  - From Cursor-dyn-kv-emit-table-sync: Reconcile wording to eight new tracking cases plus B6 or define B6 inside the seven
  - From Codex-dyn-kv-emit-table-sync: Reconcile wording to eight new tracking cases plus B6 or define B6 inside the seven


### FINDING_13: Keep `test-implement-bootstrap.md` sibling in sync with harness and plan “files to modify”
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: nit
- **Concern**: Harness sibling markdown / case table not listed in plan FILES to modify risks `agent-lint` script-md-siblings or doc drift after large harness edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add sibling markdown updates alongside test-implement-bootstrap.sh per existing pattern in skills/implement/scripts/test-implement-bootstrap.md:1-7.
  - From Cursor-Innovation: Extend edit-in-sync to include sibling test-implement-bootstrap.md case table
  - From Cursor-Requirements: Add rows for GP-adopt GP2 GP3 B1 B2 B3 B5 B6 to test-implement-bootstrap.md in same PR


### FINDING_14: New `implement-bootstrap` flags must appear in `usage` / `die_usage` and docs tables
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: nit
- **Concern**: `--forked-target`, `--upstream-repo` (and related) not reflected in `usage()` strings hurts operator discoverability and harness copy-paste.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update usage text and die_usage examples in same PR as argv parser
  - From Cursor-Pragmatic: Add argv rows to usage() alongside implement-bootstrap.md table per repo convention


### FINDING_15: Align `RUN_ID` fallback between `phase_tracking` and `post-tracking-issue.sh` / sentinel writer
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: If `phase_tracking` initializes `larch-log` with a `LARCH_TOKEN_SESSION_ID` fallback when `session-id` is empty but `post-tracking-issue.sh` does not share that fallback, metadata/sentinel can fail after log init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update post-tracking-issue.sh to use the same LARCH_TOKEN_SESSION_ID fallback or require phase_tracking to repair session-id through the sanctioned writer before calling it


### FINDING_16: Emit explicit boolean defaults for `DEFERRED` and `STALL_TRACKING` (or normalize everywhere)
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-kv-emit-table-sync
- **Severity**: important
- **Concern**: Plan/tail may emit empty values while SKILL and downstream (`ship-pr`, finalize keys) treat these as strict booleans—risking validation failures or inconsistent routing when empty strings propagate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Initialize DEFERRED=false and STALL_TRACKING=false for tracking-phase runs, emit explicit booleans, and update tests to assert false except on true branches
  - From Codex-dyn-kv-emit-table-sync: Choose one contract. Prefer emitting DEFERRED=${DEFERRED:-false} and STALL_TRACKING=${STALL_TRACKING:-false}, set DEFERRED=true on tracking-init-failed if the retained SKILL text stays, and update planned harness assertions/tables. If empty means false is intended, update SKILL.md and downstream handoff docs/tests to require normalization before ship-pr state.


### FINDING_17: Add harness coverage for DECISION_1 / `POSTED=false` deferral path (B4-style)
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Plan may stub `post-tracking-issue.sh` failure without a case asserting `POSTED=false` maps to `DEFERRED=true`, no sentinel, no rename, exit 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a B4 POSTED=false case covering DECISION_1 and assert continued exit 0, DEFERRED=true, no parent-issue.md, and no tracking-issue-write rename call


### FINDING_18: Add `--up-to-phase tracking` coverage for repo-unavailable carve-out
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: `repo-unavailable` behavior may remain infra-only (e.g. GP4) while tracking boundary expects `BRANCH_SELECTED=repo-unavailable-skip`, `DEFERRED=true`, and no tracking helper calls—unvalidated at tracking phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a repo-unavailable --up-to-phase tracking case asserting no tracking helper calls, BRANCH_SELECTED=repo-unavailable-skip, DEFERRED=true, and no sentinel/log init


### FINDING_19: Parsing `ERROR=` with `awk -F=` drops content after embedded `=` signs
- **Reviewer(s)**: Cursor-dyn-sentinel-read-contract, Codex-dyn-sentinel-read-contract
- **Severity**: latent
- **Concern**: `awk -F= /^ERROR=/ {print $2}` (plan pseudocode / pattern) truncates when the error message itself contains `=` (e.g. query strings); same class of issue called out for `get-issue-state` vs sentinel read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-read-contract: use substr from first equals or grep -m1 ^ERROR= then strip prefix
  - From Codex-dyn-sentinel-read-contract: Parse ERROR with substr($0,index($0,"=")+1) instead of field 2


### FINDING_2: Branch 1 resume must be fail-closed on tracking-issue-read contract (rc, FAILED, ADOPTED, ids)
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-sentinel-read-contract, Codex-dyn-sentinel-read-contract, Cursor-dyn-kv-emit-table-sync, Codex-dyn-kv-emit-table-sync, Cursor-dyn-stub-output-fidelity, Codex-dyn-stub-output-fidelity
- **Severity**: important
- **Concern**: The proposed Branch 1 “resume” path can run when the sentinel read is unusable: non-zero `tracking-issue-read` rc, `FAILED=true`, empty or false `ADOPTED`, empty `ISSUE_NUMBER` or `RUN_ID`, or otherwise violating `scripts/tracking-issue-read.md` / plan edge cases—risking partial resume, skipped Branch 2 adoption, and bad `larch-log` init/rename behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate Branch 1 resume on tracking-issue-read exit 0 plus non-empty ISSUE_NUMBER and ADOPTED usable per scripts/tracking-issue-read.md contract (treat empty ADOPTED as unusable); otherwise rm sentinel optional and fall through to Branch 2 without calling larch-log init or rename on garbage.
  - From Codex-Arch: After tracking-issue-read.sh, require rc 0, no FAILED=true, non-empty ISSUE_NUMBER and RUN_ID, and usable ADOPTED before resuming; otherwise clear/ignore the sentinel and fall through to Branch 2, with a harness case for malformed sentinel
  - From Cursor-Edge: Require stdout not FAILED true non-empty ISSUE_NUMBER non-empty RUN_ID and non-empty ADOPTED before resume else treat as unusable clear sentinel fall through Branch 2
  - From Codex-Edge: After tracking-issue-read.sh, require rc 0, no FAILED=true, ADOPTED=true, numeric ISSUE_NUMBER, and non-empty RUN_ID before taking Branch 1. Otherwise warn, remove or quarantine the sentinel, and fall through to Branch 2 when target_issue is present; if no target issue exists, return a clear bail instead of branch-1-resume.
  - From Cursor-Innovation: After tracking-issue-read parse FAILED=true or empty ISSUE_NUMBER or ADOPTED not true branch to Branch 2 rm sentinel optional preserve logs same as mismatch
  - From Codex-Innovation: Treat any nonzero/FAILED=true, ADOPTED!=true, or missing ISSUE_NUMBER/RUN_ID as unusable; remove or quarantine the sentinel and fall through to Branch 2, with a harness case
  - From Cursor-Pragmatic: Mirror SKILL Branch1 logic: parse FAILED; require non-empty ISSUE_NUMBER and valid ADOPTED; otherwise rm sentinel (optional) and fall through to Branch 2 without early return
  - From Codex-Pragmatic: Check the tracking-issue-read rc or FAILED=true/empty ADOPTED before the resume branch; on unreadable/malformed sentinel remove or ignore the sentinel and fall through to Branch 2, and add a harness case for FAILED=true sentinel parsing.
  - From Cursor-Requirements: Riffle grep FAILED=true after read and if present or ADOPTED empty with no safe resume contract fall through to Branch 2 per read.sh header
  - From Cursor-Requirements: Add FAILED=true guard immediately after capture before mismatch or resume logic
  - From Codex-Requirements: Require rc=0, no FAILED=true, nonempty ISSUE_NUMBER/RUN_ID, and usable ADOPTED before Branch 1 resume; otherwise remove/ignore the sentinel and fall through to Branch 2
  - From Cursor-dyn-sentinel-read-contract: reject resume unless stdout lacks FAILED=true ISSUE_NUMBER non-empty ADOPTED is true or explicitly handle false per policy else clear sentinel and fall through to Branch2 matching plan Edge cases ~L310
  - From Codex-dyn-sentinel-read-contract: After tracking-issue-read.sh --sentinel, parse FAILED and require rc 0, non-empty ISSUE_NUMBER, non-empty RUN_ID, and ADOPTED=true before resuming; otherwise clear or ignore the sentinel and fall through to Branch 2
  - From Cursor-dyn-kv-emit-table-sync: Require nonempty _sent_issue (and RUN_ID if resume needs it) before resume; otherwise rm sentinel or fall through to Branch 2 to match Edge cases L310-311
  - From Codex-dyn-kv-emit-table-sync: After tracking-issue-read.sh, parse FAILED and require rc 0, ADOPTED=true, non-empty ISSUE_NUMBER, and non-empty RUN_ID before Branch 1 resume. Otherwise remove or ignore parent-issue.md and fall through to Branch 2. Use or remove _b1_rc and _sent_adopted so shellcheck does not flag unused variables.
  - From Cursor-dyn-stub-output-fidelity: After capturing _b1_out/_b1_rc, branch on non-zero rc or a FAILED=true line before mismatch logic: clear sentinel if appropriate and fall through to Branch 2
  - From Codex-dyn-stub-output-fidelity: Check _b1_rc and FAILED=true before the resume branch; clear or ignore the sentinel and fall through to Branch 2, and add a malformed-sentinel harness case


### FINDING_20: Document `--sentinel` stdout contract to include `RUN_ID` (or add tested fallback)
- **Reviewer(s)**: Codex-dyn-sentinel-read-contract
- **Severity**: latent
- **Concern**: Plan relies on `RUN_ID` from `--sentinel` stdout while header/contract text may only list `ISSUE_NUMBER` / `ADOPTED`; future contract edits could drop `RUN_ID` and break Branch 1 resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-read-contract: Include scripts/tracking-issue-read.sh in the plan and update its header contract to list RUN_ID for --sentinel, or add a fallback parser for RUN_ID from parent-issue.md with tests pinning stdout RUN_ID


### FINDING_21: Harness stubs must match real multi-line KV envelopes (`post-tracking-issue` success and failure)
- **Reviewer(s)**: Codex-dyn-sentinel-read-contract, Codex-dyn-stub-output-fidelity
- **Severity**: important
- **Concern**: One-line `POSTED=true COMMENT_URL=stub` style output breaks `awk '/^POSTED=/'` style parsers; failure stub should mirror real script’s separate lines (`POSTED=false`, empty `COMMENT_URL`, `ERROR=`, exit 1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-read-contract: Make the stub emit one KEY=value per line, e.g. printf 'POSTED=true\nCOMMENT_URL=stub\n', matching emit_kv under LARCH_QUIET_DISABLE=1
  - From Codex-dyn-stub-output-fidelity: Emit POSTED=false, COMMENT_URL=, and ERROR=stub-failure on separate stdout lines, then exit 1


### FINDING_22: Document GP2 sentinel fixture as newline-separated KEY=value lines
- **Reviewer(s)**: Cursor-dyn-stub-output-fidelity
- **Severity**: important
- **Concern**: Ambiguous space-separated `parent-issue.md` layout can mis-parse under real `extract_sentinel_key` / `grep ^ISSUE_NUMBER=` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stub-output-fidelity: Document GP2 fixture as three newline-separated KEY=value lines matching skills/implement/scripts/post-tracking-issue.sh:101 printf layout


### FINDING_26: SKILL `RUN_ID` prose vs post-bootstrap derivation (uuidgen legacy)
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: SKILL may still document `uuidgen` fallbacks while collapsed Step 0 derives `RUN_ID` only from session-id / token path—risk of orchestrators reintroducing divergent identifiers outside bootstrap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When collapsing SKILL state that post-infra bootstrap derives RUN_ID only from session-id token path and drop uuidgen block or mark it legacy non-bootstrap

---

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must **not** appear anywhere in this aggregation.

### FINDING_3: Avoid a second implement-bootstrap pass that re-runs infra and splits session state
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Plan adds tracking as an additional `--up-to-phase tracking` (or similar) bootstrap while `main` still runs `phase_infra` first; a second call can allocate another `IMPLEMENT_TMPDIR` / session surface and leave already-exported infra/session variables tied to the first run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the existing Step 0 bootstrap invocation to a single --up-to-phase tracking call that parses infra plus tracking KVs, or add an explicit reuse/skip-infra mode before keeping two calls
  - From Codex-Pragmatic: Revise the SKILL.md plan so Step 0 invokes implement-bootstrap once with --up-to-phase tracking and parses both infra and tracking KVs, or add an explicit reuse/skip-infra mechanism before proposing a second call.
  - From Codex-Requirements: Update the Step 0 integration to make a single --up-to-phase tracking call that replaces the infra-only call, or add an explicit reuse-existing-infra mode and document/test it


### FINDING_4: Fork upstream context fetch must match voted SKILL semantics (best-effort vs hard bail)
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-kv-emit-table-sync
- **Severity**: important
- **Concern**: Plan uses `|| true` / best-effort framing for fork upstream `get-issue-context` while live `skills/implement/SKILL.md` still describes hard bail / Step 18 routing on failure; reviewers cite L646–658 / L658 as contradicting soft-continue unless SKILL is explicitly rewritten as a binding behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL collapse explicitly replace the abort-and-skip-to-Step-18 requirement with best-effort logging only, or align bootstrap to emit a bail token when context fetch fails if product still wants a hard stop.
  - From Cursor-Innovation: Explicitly list SKILL rewrite of fork failure routing as a binding doc delta not a pattern match
  - From Cursor-Pragmatic: Make this an explicit voted behavior change: update SKILL fork section and implement-bootstrap.md risk notes accordingly, or preserve abort semantics inside phase_tracking when context fetch fails
  - From Cursor-Requirements: Replace rationale with explicit decision note that fork context fetch becomes best-effort and edit SKILL fork subsection to drop Step 18 abort for that failure class
  - From Cursor-dyn-kv-emit-table-sync: Retarget citation to the actual rename best-effort block or rewrite note to state this PR intentionally relaxes L658 fork fetch failures


### FINDING_5: `/implement --run-id` must flow through bootstrap and sentinel writers consistently
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: SKILL documents optional stable `--run-id`, but the plan adds other argv to `implement-bootstrap` and derives `RUN_ID` from session/token paths; an explicit `--run-id` could diverge from log roots and `parent-issue.md` / post-tracking writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add --run-id to implement-bootstrap argv and the SKILL.md invocation, prefer it on Branch 2, and update post-tracking-issue.sh or its call contract so the sentinel written after metadata success uses the same explicit RUN_ID
  - From Codex-Requirements: Extend implement-bootstrap.sh with --run-id validation, prefer it in Branch 2 RUN_ID derivation, and ensure post-tracking-issue.sh writes the same RUN_ID into parent-issue.md


### FINDING_6: `--forked-target` must persist into the sanctioned session-env contract before Step 2
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: `phase_tracking` may consume `--forked-target` while `write-session-env.sh` / Step 2 fork detection (`FORKED_TARGET` in session-env) does not get the flag—risking `main-branch-prohibited` or wrong fork routing after bootstrap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Extend the sanctioned writer path: add --forked-target true|false to write-session-env.sh, pass FORKED_TARGET from implement-bootstrap phase_infra, document it, and add a fork-mode bootstrap test that verifies session-env.sh contains FORKED_TARGET=true before Step 2.


### FINDING_7: Later bootstrap phases must not overwrite real tracking bail tokens from stubs
- **Reviewer(s)**: Cursor-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: After `phase_tracking` sets `IMPLEMENT_BAIL_REASON` / stall tokens for closed issue, PR exists, init failures, etc., subsequent `phase_plan_materialize` / `phase_coder_select` (or stubs) may assign placeholder bail reasons and break orchestrator routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Skip stub bail assignment when prior phase set a real bail token or preserve prior IMPLEMENT_BAIL_REASON in stubs until Phase 3 4 land
  - From Codex-Pragmatic: After each phase, if IMPLEMENT_BAIL_REASON is non-empty or STALL_TRACKING=true, skip remaining phases and emit the tail, or make later phase stubs preserve an existing bail reason.


### FINDING_8: Branch 1 must not swallow `larch-log` init failures (`|| true` / discarded output)
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: Resume path may pipe or discard `larch-log.sh init` errors and continue with `branch-1-resume` despite missing or corrupt manifest / unwritable log root—contradicting “committed run-log is source of truth” intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Capture larch-log init stdout/stderr in Branch 1 like Branch 2. If init fails, set IMPLEMENT_BAIL_REASON=tracking-init-failed and STALL_TRACKING=true, or otherwise append a Tool Failures entry and route explicitly; do not emit a happy branch-1-resume tail.
  - From Cursor-Innovation: Match SKILL visibility remove || true on failure or branch to tracking-init-failed STALL path when init returns non-zero


### FINDING_9: `append-tool-failure` invocation for rename failures must match argv contract and SKILL patterns
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Plan names `append-tool-failure` for rename failures without a concrete argv contract; mis-invocation risks `set -u` exits or silent loss of logging vs existing SKILL guidance on log site and message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify a concrete invocation (capture tracking-issue-write stdout/stderr to a temp file; pass --log --site --tool --exit-code --category Tool Failures --output-file; mirror patterns from skills/implement/SKILL.md:585-591) or delegate to a tiny helper script owned under scripts/.


