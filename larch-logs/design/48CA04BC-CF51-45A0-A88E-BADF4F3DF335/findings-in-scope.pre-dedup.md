### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py:436-477
- **Concern**: Partition close-original still performs direct gh comment/close outside the authorization contract. Scenario: The plan gates salvage reconciliation and partition /larch:issue filing but does not list `decompose.py`. `decompose close-original` still posts `gh issue comment` and `gh issue close` on the approved-partition path (`decompose-panel.md` §8), so tests or unauthorized /design runs can mutate the original issue even when create-one and the cross-repo helper refuse
- **Proposed resolution**: Add `### UPDATED: python/larch/design/decompose.py` (and matching tests): validate `$DESIGN_TMPDIR/source-env.sh` before any gh call in `close_original_issue`, refuse with bounded local failure on denial, and extend `test_design_lifecycle.py` or `python/test_decompose.py` to prove zero gh invocations without authorization



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:832-879
- **Concern**: Deferred-work disposition gates only `issue create-one`, not follow-on mutations. Scenario: The plan’s `scope_disposition.py` update covers create-one forwarding only. `_append_cross_links` still calls `tracking-issue append-comment` and `_add_block_relation` still calls `issue add-blocked-by`, both of which mutate real issues via gh without any authorization input
- **Proposed resolution**: Extend the `scope_disposition.py` change to require the active `/implement` mutation context before append-comment and add-blocked-by, forward that context into those CLI calls (or central gates on those verbs), surface refusal through the existing `ShipError` path, and add `test_scope_disposition.py` cases proving zero gh calls when unauthorized



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/issue/issue_create.py:695-754
- **Concern**: `issue add-blocked-by` remains outside the create-one authorization gate. Scenario: The plan updates `create-one` only. `add_blocked_by_main` still resolves repos and POSTs `gh api .../dependencies/blocked_by` with no session/operator authorization, and `/issue` Step 6 plus `scope_disposition.py` invoke it after (or apart from) gated creates; tests can mutate dependency edges directly
- **Proposed resolution**: Gate `add_blocked_by_main` with the same session-context/operator-mode contract as `create-one`, update `skills/issue/SKILL.md` Step 6 and deferred-work callers to forward the guarded context, and add focused tests in `test_issue_create.py` proving refusal emits designated KVs with zero gh calls ## Findings ### 1. [architecture] `python/larch/design/decompose.py:436-477` — Partition close-original bypasses authorization The plan covers salvage reconciliation (`design_terminal.py`) and partition batch filing (`decompose-panel.md`), but `decompose close-original` is a separate direct-mutation path. After partition approval it comments on and closes the original issue via `gh` with no session-backed check. That matches the bug class where development flows mutate production issues outside the filing choke points. **Suggested revision:** Add `decompose.py` to firm plan files, gate `close_original_issue` on validated `source-env.sh`, and pin unauthorized zero-`gh` tests. ### 2. [correctness] `python/larch/implement/scope_disposition.py:832-879` — Deferred-work filing is only half-gated Partial-scope disposition is more than `issue create-one`. The follow-up flow also posts cross-link comments (`tracking-issue append-comment`) and dependency edges (`issue add-blocked-by`). The plan’s single-sentence `scope_disposition.py` update does not cover those calls, so a gated create could still be followed by unauthorized comments and blocker mutations, or tests could reach those subcommands independently. **Suggested revision:** Thread the `/implement` mutation context through the full disposition sequence and extend `test_scope_disposition.py` accordingly. ### 3. [risk-integration] `python/larch/issue/issue_create.py:695-754` — `add-blocked-by` is an unguarded mutation verb Round 1 flagged this path; the updated plan still omits it. Gating `create-one` alone leaves `add_blocked_by_main` as a standalone gh mutation surface used by `/issue` Step 6 and implement disposition. The plan wires session context into nested `create-one` commands but not into blocker-edge application, so the “cover every known issue-mutation path” goal is incomplete. **Suggested revision:** Apply the shared authorization checker to `add_blocked_by_main`, forward context from `/issue` Step 6, and add refusal tests alongside the planned `create-one` coverage.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/issue/tracking_issue.py:815-1040
- **Concern**: Direct tracking-issue mutators remain outside the planned authorization boundary. Scenario: The design terminal still invokes `tracking-issue upsert-summary`, and this module also exposes create, comment, rename, and comment-patch paths that call GitHub directly. A test, fixture, or development probe invoking these commands with inherited credentials can create or mutate a real issue without the explicit live-run or operator authorization required by the feature.
- **Proposed resolution**: Extend the authorization contract to every direct tracking-issue mutation entry point, including `create-issue`, `append-comment`, `rename`, `mark-false-positive`, and `upsert-summary`, and pass the guarded design or implement context from their live callers. Refuse before repository resolution or any `gh` call, while keeping read-only and dry-run paths available.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:857-915
- **Concern**: Design Step 5b annotate still has direct gh label mutations outside the planned gates. Scenario: After create-one is gated, file-oos-annotate label-only retry and priority provisioning still call _run_gh for gh label create and gh issue edit without any session authorization check; harnesses with fixture sentinel URLs can label real issues
- **Proposed resolution**: Add ### UPDATED: python/larch/design/design_oos.py to validate $DESIGN_TMPDIR/source-env.sh before any _run_gh label work; extend ### UPDATED: python/tests/design/test_design_oos.py with unauthorized annotate cases that assert zero gh calls



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:436-481
- **Concern**: Partition close-original still bypasses the authorization contract. Scenario: Plan updates decompose-panel.md only, but close_original_issue still posts gh issue comment and gh issue close directly; an unauthorized decomposition test or replay can mutate the original issue even when create-one and the reporter helper refuse
- **Proposed resolution**: Add ### UPDATED: python/larch/design/decompose.py to require validated source-env.sh before comment/close; add focused regression coverage in python/tests/design/test_design_lifecycle.py or a decompose test module



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py:695-763,1008-1038
- **Concern**: issue create-one gating leaves sibling /issue mutators ungated. Scenario: Plan extends create-one only; add-blocked-by still POSTs gh api dependencies and cleanup-failed still gh issue close without authorization, so /issue Step 6 edges and failed-create cleanup can mutate production issues from direct CLI or test invocations
- **Proposed resolution**: Gate add_blocked_by_main and cleanup_failed_main with the same session or operator authorization inputs, or document and test that /issue orchestration never invokes them without prior authorized create-one



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan Goal / Approach §10
- **Concern**: [SCOPE-REDUCTION] Goal claims every known mutation path but the file list omits several live mutators. Scenario: Step 10 requires inventory yet tracking_issue, clarify, combine_issues, and report_tokens_issue are absent; implementers may ship partial coverage while the goal still reads as exhaustive
- **Proposed resolution**: Narrow Goal acceptance to the enumerated choke points, or add explicit ### MAY_UPDATE: exclusions plus a short residual-path table in SECURITY.md



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_report.py:739-805 and python/larch/design/design_terminal.py:914-920
- **Concern**: Tier-A dedup still performs GitHub work before the planned authorization gate is specified for that entrypoint. Scenario: `file_tier_a_after_compose` calls `dedup_tier_a_report_main` with only `helper_common()` args; `dedup_tier_a_report` then runs `gh repo view` and a `--dedup-only` helper lookup before any mutation-context argument exists. Unauthorized design failure-report fixtures that reach the dedup branch can still hit `gh` even when create filing is gated.
- **Proposed resolution**: Name `dedup_tier_a_report` in the plan; require mutation-context validation at its entry before repo resolution or helper invocation; pass `$DESIGN_TMPDIR/source-env.sh` (and the implement equivalent) through the dedup argv; assert zero `gh` calls on refusal in `test_design_lifecycle.py` / `test_stall_recovery.py`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/file-failure-report-cross-repo.sh:1-328 and python/larch/cli.py
- **Concern**: [SCOPE-REDUCTION] Shell authorization validation has no pinned Python CLI delegate, inviting duplicated Bash rules. Scenario: Approach item 2 calls for a shell-compatible validation route but the file list does not add a `python/cli.py` entrypoint. The helper is likely to reimplement symlink, session-root, boolean, and run-id checks separately from `issue_create.py`, which can drift and fail open on one side only.
- **Proposed resolution**: Add one `python/cli.py` authorization-check verb (implemented in `session_env.py`); have `file-failure-report-cross-repo.sh` call it and map refusal KVs; keep Bash limited to argument plumbing.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py:695-763,1008-1038
- **Concern**: Planned `issue_create.py` work gates only `create-one`; `add-blocked-by` and `cleanup-failed` stay ungated sibling entrypoints. Scenario: Live `/issue` Step 6 and dep-link recovery call `issue add-blocked-by` and `issue cleanup-failed` immediately after `create-one`; if only `create-one` accepts session/operator authorization, legitimate blocked-by wiring and orphan cleanup refuse while unauthorized callers can still mutate or close issues directly
- **Proposed resolution**: Extend the `issue_create.py` update to apply the same fail-closed authorization check and argv contract to `add_blocked_by_main` and `cleanup_failed_main`; update `skills/issue/SKILL.md` Step 6 dep wiring/cleanup commands, `oos_filer.py`, and `scope_disposition.py` to forward the same session or operator context



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:832-879
- **Concern**: `scope_disposition.py` plan only threads authorization into deferred-work `create-one`. Scenario: Partial-scope disposition also calls `tracking-issue append-comment` and `issue add-blocked-by` to post cross-links and dependency edges; those comment/edge mutations are outside the planned change, so dev probes can still reach GitHub or live disposition fails once sibling verbs are gated
- **Proposed resolution**: Expand the `scope_disposition.py` update to pass the active `/implement` mutation context into `_append_cross_links` and `_add_block_relation`, with refusal surfaced through the existing `ShipError` path



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/issue/SKILL.md:388-404
- **Concern**: `/larch:issue` guidance plans authorization forwarding for nested `create-one` only, not Step 6 dependency wiring. Scenario: After the gate lands, batch filing can create authorized issues then fail every `add-blocked-by` edge because Step 6 command templates omit the required session-context or operator literal, leaving broken blocked-by chains or closed orphans via ungated `cleanup-failed`
- **Proposed resolution**: Document and emit the same authorization argument on every Step 6 `issue add-blocked-by` and `issue cleanup-failed` invocation, mirroring the nested `create-one` contract



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: Plan Goal section
- **Concern**: [SCOPE-REDUCTION] Goal claims coverage of every known issue-mutation path while firm files omit several live surfaces. Scenario: Binding issue acceptance only requires filing choke-point refusal plus reporter regression; keeping the broad Goal without `tracking_issue.py`, `decompose.py` close-original, or `clarify.py` updates either over-scopes the 865-line plan or leaves a false completeness claim
- **Proposed resolution**: Narrow the Goal to the binding acceptance surfaces explicitly listed in approach steps 3-9, or add firm `### UPDATED:` rows for each remaining live mutation module before claiming full-path coverage



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/design/design_oos.py:857-915,943-982
- **Concern**: Prior accepted OOS authorization fix is incomplete because the plan gates `python/larch/issue/oos_filer.py` but omits `/design` OOS label mutations in `design_oos.py`. Scenario: The Step 5b annotate or label-only retry path can run `gh label create` and `gh issue edit` without validating `$DESIGN_TMPDIR/source-env.sh`, so a fixture or development invocation can still mutate real issues
- **Proposed resolution**: Add `python/larch/design/design_oos.py` and its Step 5b caller to the firm changes. Pass and validate the design session context before repository resolution or `_run_gh`, and add a zero-GitHub unauthorized label-only regression test



