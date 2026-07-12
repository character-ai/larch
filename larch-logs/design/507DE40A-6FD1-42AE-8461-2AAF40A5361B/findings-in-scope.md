### FINDING_1: Pin mutable branch evidence to an immutable commit
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Branch-only evidence can change between fetch and inspection, allowing triage to verify the wrong snapshot and emit a false verdict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify the design_pause pattern: fetch once, rev-parse to a commit SHA, enumerate and git-show only from that pinned SHA, and record the pinned SHA in evidence output.

### FINDING_2: Reuse canonical protected-state checks
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Ad-hoc lifecycle-marker or label detection may miss malformed protected state or the exact clarification label, allowing mutation of an issue awaiting design clarification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State in triage.py that protected-state checks must call issue_wire.parse_named_block for plan and design-pause, treat any malformed token as protected-state, and reuse clarify.LABEL_NAME for the clarify label gate.
  - From Cursor-Pragmatic: Refuse mutation when the needs-design-clarification label is present using python/larch/design/clarify.py LABEL_NAME or python/cli.py clarify state; add the exact label to tests and the structural harness.

### FINDING_3: Authorize dependency mutations
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The separate `/block-issue` dependency path can mutate GitHub without the `--operator-invoked` authorization required by `triage apply`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an authorization check to the dependency path, or apply dependencies inside the authorized triage helper
  - From Codex-Arch: Add the orchestrator banner and continuation reminders, and register `skills/triage/SKILL.md` in the shared scope list and harness 1. **[security] Dependency authorization is incomplete.** The plan authorizes `triage apply` and `/issue`, but `/block-issue` remains a separate mutation path without `--operator-invoked` enforcement. 2. **[architecture] Add the required anti-halt wiring.** `/triage` performs work after child skill calls, so it must follow the repository’s orchestrator banner, reminder, scope-list, and harness contracts.

### FINDING_4: Wire triage into the anti-halt contract
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: Triage can halt after child skills return, skipping dependency read-back, follow-up verification, cleanup, and terminal machine keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the orchestrator banner and continuation reminders, and register `skills/triage/SKILL.md` in the shared scope list and harness 1. **[security] Dependency authorization is incomplete.** The plan authorizes `triage apply` and `/issue`, but `/block-issue` remains a separate mutation path without `--operator-invoked` enforcement. 2. **[architecture] Add the required anti-halt wiring.** `/triage` performs work after child skill calls, so it must follow the repository’s orchestrator banner, reminder, scope-list, and harness contracts.
  - From Codex-Requirements: Add canonical anti-halt reminders, verify `/issue` through counters and a sentinel, and register triage in `skills/shared/subskill-invocation.md` and `scripts/test-anti-halt-banners.sh`.

### FINDING_5: Bound target issue content
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Unbounded issue bodies and comment histories can exhaust the prompt or scratch budget and prevent reliable verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Apply bounded body, comment-count, and total-content limits during the initial fetch, and record omitted content as evidence gaps

### FINDING_6: Inspect code from an immutable main snapshot
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Investigation may inspect a feature branch or dirty worktree instead of main, producing false fixed or root-cause conclusions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Resolve and record a main commit before investigation, read cited files and symbols through that commit, and fail closed if the exact main ref cannot be verified

### FINDING_7: Provide a validated evidence-inspection CLI
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The required fetch-and-show workflow for unmerged branch evidence has no reachable, validated CLI surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a triage inspect (or equivalent) entry point in triage.py, register it in cli.py, validate refs/paths and fixed-remote fetch/show there, record missing refs as evidence gaps, and pin the helper in skills/triage/SKILL.md and scripts/test-triage-structure.sh.
  - From Codex-Pragmatic: Add a triage evidence verb that validates refs and paths, uses the fixed remote with argument-vector execution, and has focused tests.
  - From Cursor-Requirements: Add a deterministic triage read-ref (or equivalent) verb in python/larch/issue/triage.py, register it in python/larch/cli.py, call it from skills/triage/SKILL.md for validated commit SHAs or refs/pull/N/head, and cover fetch-show success, rejection, and caps in python/tests/issue/test_triage.py and scripts/test-triage-structure.sh

### FINDING_8: Recheck freshness before dependency writes
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Dependency application can use stale analysis after an intervening issue edit or lifecycle transition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Pass the verified timestamp into a triage-controlled dependency mutation that rechecks freshness and protected state immediately before applying and reading back the edge.
  - From Codex-Requirements: Thread the latest verified `updatedAt` into dependency application and make `issue_block.py` compare it immediately before mutation. Test that mismatch prevents the GraphQL mutation.

### FINDING_9: Preserve title restoration on close verdicts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Rejecting lifecycle-prefixed titles before verdict routing makes required title restoration unreachable for already-fixed or duplicate issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reject active lifecycle state, but allow close verdicts to restore a stale prefix when no protected block or label remains. Test both paths.

### FINDING_10: Permit narrowly scoped external-tool reproduction
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: A blanket ban on networked or authenticated probes prevents the specified safe external-tool reproduction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Allow narrowly named, fixed-destination, read-only external probes through existing credential-safe launch paths. Keep arbitrary commands, arguments, and destinations forbidden.

### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage body section instead of parallel marker grammar. Scenario: The plan adds bespoke helper-owned triage block validation and replacement in triage.py while issue_wire already owns compose_named_block, strip_named_block, parse_named_block, and malformed detection for plan and design-pause markers. A second parser will drift and complicate idempotent replace/preserve-original-body behavior.
- **Proposed resolution**: Add triage to the shared named-block surface (for example extend _ALLOWED_MARKERS with triage) and delegate valid-body edits to issue_wire helpers; keep triage.py focused on verdict orchestration and postconditions.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage section. Scenario: The plan adds separate helper-owned triage marker parsing and body splice logic in triage.py while issue_wire already owns compose_named_block and parse_named_block for plan and design-pause. Parallel marker logic adds drift risk without new capability.
- **Proposed resolution**: Extend issue_wire _ALLOWED_MARKERS with triage, reuse compose_named_block and parse_named_block for insert/replace/idempotency, and keep triage.py focused on verdict orchestration and sanitation.

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:42-48
- **Concern**: [SCOPE-REDUCTION] 3. Dependency writes are not limited to the valid verdict path. Scenario: Already-fixed, invalid, and duplicate verdicts close the issue, but the next step can still add blocked-by edges to that closed issue.
- **Proposed resolution**: Apply dependency edges only for a verified valid verdict while the issue remains open.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Plan specifies bespoke helper-owned triage block syntax instead of reusing issue_wire named-block parse, compose, and strip with marker triage. Scenario: A second malformed-block grammar can disagree with issue_wire on plan and design-pause markers and accept or reject protected bodies differently than the rest of larch
- **Proposed resolution**: Implement triage section splice via issue_wire.parse_named_block, compose_named_block, and strip_named_block with marker triage; keep compare-and-swap mutation only in triage apply ### 1. completeness — `skills/triage/SKILL.md` / `python/larch/cli.py` The binding scope anchor requires collecting cited `larch-logs/` from unmerged PR branches using `git fetch` plus `git show`. The plan mentions a deterministic ref helper in skill prose, but `### UPDATED: python/larch/cli.py` registers only `triage apply` and `triage probe`, and the planned `python/tests/issue/test_triage.py` coverage list has no fetch/show cases. That leaves the primary evidence path unspecified in the firm Python surface and untested. **Suggested revision:** Add and register a `triage read-ref` (or equivalent) helper, invoke it from the skill for validated SHAs or `refs/pull/<n>/head`, and pin behavior in unit and structural tests. ### 2. architecture — `python/larch/issue/triage.py` [SCOPE-REDUCTION] The plan tasks `triage.py` with validating “helper-owned triage block syntax” independently. `issue_wire.py` already owns named-block grammar (`<!-- larch:{marker}:start/end -->`) and malformed tokens for `plan` and `design-pause`. Duplicating that logic adds diff and drift risk against protected-state checks. **Suggested revision:** Reuse `issue_wire` parse/compose/strip with marker `triage` for section handling; keep `updatedAt` compare-and-swap and authorization in `triage apply` only.
