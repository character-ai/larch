### [Plan Review] FINDING_1

### FINDING_1: Partition close-original bypasses authorization
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan gates salvage reconciliation and partition `/larch:issue` filing but does not cover `decompose close-original`. After partition approval, `close_original_issue` still posts `gh issue comment` and `gh issue close` on the original issue with no session-backed authorization check, so tests or unauthorized `/design` runs can mutate production issues even when gated create paths refuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/design/decompose.py` (and matching tests): validate `$DESIGN_TMPDIR/source-env.sh` before any gh call in `close_original_issue`, refuse with bounded local failure on denial, and extend `test_design_lifecycle.py` or `python/test_decompose.py` to prove zero gh invocations without authorization
  - From Cursor-Innovation: Add ### UPDATED: python/larch/design/decompose.py to require validated source-env.sh before comment/close; add focused regression coverage in python/tests/design/test_design_lifecycle.py or a decompose test module


### [Plan Review] FINDING_2

### FINDING_2: Deferred-work disposition only half-gates follow-on mutations
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The planned `scope_disposition.py` change gates only `issue create-one`. The deferred-work path also calls `tracking-issue append-comment` and `issue add-blocked-by` via `_append_cross_links` and `_add_block_relation`, which mutate real issues through `gh` without authorization input. A gated create can still be followed by unauthorized comments and blocker edges, or tests can reach those subcommands directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `scope_disposition.py` change to require the active `/implement` mutation context before append-comment and add-blocked-by, forward that context into those CLI calls (or central gates on those verbs), surface refusal through the existing `ShipError` path, and add `test_scope_disposition.py` cases proving zero gh calls when unauthorized
  - From Cursor-Requirements: Expand the `scope_disposition.py` update to pass the active `/implement` mutation context into `_append_cross_links` and `_add_block_relation`, with refusal surfaced through the existing `ShipError` path


### [Plan Review] FINDING_3

### FINDING_3: `issue add-blocked-by` and `cleanup-failed` remain unguarded sibling mutators
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan updates `issue create-one` only. `add_blocked_by_main` still POSTs `gh api .../dependencies/blocked_by` and `cleanup_failed_main` still calls `gh issue close` without session or operator authorization. `/issue` Step 6, dep-link recovery, and implement disposition invoke these paths after (or apart from) gated creates, leaving a standalone mutation surface and risking broken blocked-by chains or orphan cleanup once `create-one` is gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate `add_blocked_by_main` with the same session-context/operator-mode contract as `create-one`, update `skills/issue/SKILL.md` Step 6 and deferred-work callers to forward the guarded context, and add focused tests in `test_issue_create.py` proving refusal emits designated KVs with zero gh calls
  - From Cursor-Innovation: Gate add_blocked_by_main and cleanup_failed_main with the same session or operator authorization inputs, or document and test that /issue orchestration never invokes them without prior authorized create-one
  - From Cursor-Requirements: Extend the `issue_create.py` update to apply the same fail-closed authorization check and argv contract to `add_blocked_by_main` and `cleanup_failed_main`; update `skills/issue/SKILL.md` Step 6 dep wiring/cleanup commands, `oos_filer.py`, and `scope_disposition.py` to forward the same session or operator context


### [Plan Review] FINDING_4

### FINDING_4: Direct tracking-issue mutators remain outside authorization boundary
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The design terminal invokes `tracking-issue upsert-summary`, and `tracking_issue.py` also exposes create, comment, rename, and comment-patch paths that call GitHub directly. Tests, fixtures, or development probes invoking these commands with inherited credentials can create or mutate real issues without the explicit live-run or operator authorization required by the feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the authorization contract to every direct tracking-issue mutation entry point, including `create-issue`, `append-comment`, `rename`, `mark-false-positive`, and `upsert-summary`, and pass the guarded design or implement context from their live callers. Refuse before repository resolution or any `gh` call, while keeping read-only and dry-run paths available.


### [Plan Review] FINDING_5

### FINDING_5: Design Step 5b annotate label mutations bypass authorization
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: The plan gates `oos_filer.py` but omits `/design` OOS label work in `design_oos.py`. After create-one is gated, Step 5b annotate label-only retry and priority provisioning still call `_run_gh` for `gh label create` and `gh issue edit` without validating `$DESIGN_TMPDIR/source-env.sh`, so fixture or development invocations can still mutate real issue labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/larch/design/design_oos.py to validate $DESIGN_TMPDIR/source-env.sh before any _run_gh label work; extend ### UPDATED: python/tests/design/test_design_oos.py with unauthorized annotate cases that assert zero gh calls
  - From Codex-Requirements: Add `python/larch/design/design_oos.py` and its Step 5b caller to the firm changes. Pass and validate the design session context before repository resolution or `_run_gh`, and add a zero-GitHub unauthorized label-only regression test


### [Plan Review] FINDING_7

### FINDING_7: `/larch:issue` Step 6 omits authorization forwarding for dependency wiring
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `/larch:issue` guidance plans authorization forwarding for nested `create-one` only, not Step 6 dependency wiring. After the gate lands, batch filing can create authorized issues then fail every `add-blocked-by` edge because Step 6 command templates omit the required session-context or operator literal, leaving broken blocked-by chains or closed orphans via ungated `cleanup-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document and emit the same authorization argument on every Step 6 `issue add-blocked-by` and `issue cleanup-failed` invocation, mirroring the nested `create-one` contract


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan Goal / Approach §10
- **Concern**: [SCOPE-REDUCTION] Goal claims every known mutation path but the file list omits several live mutators. Scenario: Step 10 requires inventory yet tracking_issue, clarify, combine_issues, and report_tokens_issue are absent; implementers may ship partial coverage while the goal still reads as exhaustive
- **Proposed resolution**: Narrow Goal acceptance to the enumerated choke points, or add explicit ### MAY_UPDATE: exclusions plus a short residual-path table in SECURITY.md


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/file-failure-report-cross-repo.sh:1-328 and python/larch/cli.py
- **Concern**: [SCOPE-REDUCTION] Shell authorization validation has no pinned Python CLI delegate, inviting duplicated Bash rules. Scenario: Approach item 2 calls for a shell-compatible validation route but the file list does not add a `python/cli.py` entrypoint. The helper is likely to reimplement symlink, session-root, boolean, and run-id checks separately from `issue_create.py`, which can drift and fail open on one side only.
- **Proposed resolution**: Add one `python/cli.py` authorization-check verb (implemented in `session_env.py`); have `file-failure-report-cross-repo.sh` call it and map refusal KVs; keep Bash limited to argument plumbing.


