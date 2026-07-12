### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/triage/SKILL.md
- **Concern**: Pin mutable git refs to an immutable commit SHA before enumerating or showing branch-only evidence. Scenario: The plan allows refs/pull/<n>/head and validated SHAs but does not require rev-parse pinning before ls-tree/git show. A mutable ref can advance between fetch and read, so triage can verify the wrong snapshot and emit a false valid, already-fixed, or duplicate verdict.
- **Proposed resolution**: Specify the design_pause pattern: fetch once, rev-parse to a commit SHA, enumerate and git-show only from that pinned SHA, and record the pinned SHA in evidence output.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage body section instead of parallel marker grammar. Scenario: The plan adds bespoke helper-owned triage block validation and replacement in triage.py while issue_wire already owns compose_named_block, strip_named_block, parse_named_block, and malformed detection for plan and design-pause markers. A second parser will drift and complicate idempotent replace/preserve-original-body behavior.
- **Proposed resolution**: Add triage to the shared named-block surface (for example extend _ALLOWED_MARKERS with triage) and delegate valid-body edits to issue_wire helpers; keep triage.py focused on verdict orchestration and postconditions.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/triage.py
- **Concern**: Protected lifecycle detection should delegate to existing issue_wire and clarify contracts instead of new ad-hoc scans. Scenario: The plan requires refusing valid or malformed larch:plan, pause, clarify, and other control markers, but assigns detection to new triage.py logic without mandating issue_wire.parse_named_block(marker=plan|design-pause), plan-block read malformed tokens, or clarify.LABEL_NAME (needs-design-clarification). A bespoke scanner can miss malformed markers that issue_wire already treats as protected and allow mutation of active design state.
- **Proposed resolution**: State in triage.py that protected-state checks must call issue_wire.parse_named_block for plan and design-pause, treat any malformed token as protected-state, and reuse clarify.LABEL_NAME for the clarify label gate.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: skills/triage/SKILL.md:48; python/larch/issue/triage.py:60
- **Concern**: Dependency mutation bypasses the explicit operator-authorization boundary. Scenario: `triage apply` requires `--operator-invoked`, but the separate `/block-issue` path has no equivalent authorization check and can mutate GitHub outside that boundary
- **Proposed resolution**: Add an authorization check to the dependency path, or apply dependencies inside the authorized triage helper



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/triage/SKILL.md:47-49; skills/shared/subskill-invocation.md:123-138; scripts/test-anti-halt-banners.sh:33-49
- **Concern**: The new skill is a stateful orchestrator but is absent from the anti-halt contract. Scenario: Triage invokes child skills and must continue to dependency handling, follow-up filing, terminal keys, and cleanup; without the required banner and call-site reminders it can halt after a child returns
- **Proposed resolution**: Add the orchestrator banner and continuation reminders, and register `skills/triage/SKILL.md` in the shared scope list and harness 1. **[security] Dependency authorization is incomplete.** The plan authorizes `triage apply` and `/issue`, but `/block-issue` remains a separate mutation path without `--operator-invoked` enforcement. 2. **[architecture] Add the required anti-halt wiring.** `/triage` performs work after child skill calls, so it must follow the repository’s orchestrator banner, reminder, scope-list, and harness contracts.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: skills/triage/SKILL.md:15,31-36
- **Concern**: Target issue body and comments lack an explicit size and count bound before model inspection. Scenario: A large issue with thousands of comments can exhaust the prompt or scratch budget, preventing reliable verification; the listed caps cover neighbors, logs, code, and command output but not the target issue
- **Proposed resolution**: Apply bounded body, comment-count, and total-content limits during the initial fetch, and record omitted content as evidence gaps



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/triage/SKILL.md:15,37; python/larch/issue/triage.py:63-64
- **Concern**: The main-code verification path is not tied to an immutable main ref. Scenario: A triage run from a feature branch or dirty worktree can inspect uncommitted code and falsely conclude that the issue is fixed or reproduce a root cause that is absent on main
- **Proposed resolution**: Resolve and record a main commit before investigation, read cited files and symbols through that commit, and fail closed if the exact main ref cannot be verified



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/cli.py
- **Concern**: Register a validated evidence/git inspection helper required by investigation. Scenario: The plan requires cited unmerged-branch and path-validated reads through a deterministic helper with argument-vector execution, but only registers triage apply and triage probe. Investigation cannot legally retrieve branch-only larch-logs without prompt-side git or an unspecified surface.
- **Proposed resolution**: Add a triage inspect (or equivalent) entry point in triage.py, register it in cli.py, validate refs/paths and fixed-remote fetch/show there, record missing refs as evidence gaps, and pin the helper in skills/triage/SKILL.md and scripts/test-triage-structure.sh.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/triage/SKILL.md
- **Concern**: Pin protected clarify refusal to needs-design-clarification. Scenario: The plan only says clarify label. A different literal or fuzzy match can miss issues in clarify state and allow triage to mutate an awaiting-clarification issue.
- **Proposed resolution**: Refuse mutation when the needs-design-clarification label is present using python/larch/design/clarify.py LABEL_NAME or python/cli.py clarify state; add the exact label to tests and the structural harness.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage section. Scenario: The plan adds separate helper-owned triage marker parsing and body splice logic in triage.py while issue_wire already owns compose_named_block and parse_named_block for plan and design-pause. Parallel marker logic adds drift risk without new capability.
- **Proposed resolution**: Extend issue_wire _ALLOWED_MARKERS with triage, reuse compose_named_block and parse_named_block for insert/replace/idempotency, and keep triage.py focused on verdict orchestration and sanitation.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:34-38,56-72,80-83
- **Concern**: 1. The promised unmerged-branch evidence helper has no reachable CLI surface. Scenario: The plan registers only apply and probe, while probe forbids network access. `/triage` therefore cannot safely perform the required git fetch and git show workflow for cited PR refs.
- **Proposed resolution**: Add a triage evidence verb that validates refs and paths, uses the fixed remote with argument-vector execution, and has focused tests.



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:47-48,63-64
- **Concern**: 2. The prior accepted freshness fix remains incomplete for dependency mutations. Scenario: The apply helper advances updatedAt, then `/block-issue` runs without that version. An intervening edit, close, or lifecycle transition can receive an unauthorized dependency edge.
- **Proposed resolution**: Pass the verified timestamp into a triage-controlled dependency mutation that rechecks freshness and protected state immediately before applying and reading back the edge.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:42-48
- **Concern**: [SCOPE-REDUCTION] 3. Dependency writes are not limited to the valid verdict path. Scenario: Already-fixed, invalid, and duplicate verdicts close the issue, but the next step can still add blocked-by edges to that closed issue.
- **Proposed resolution**: Apply dependency edges only for a verified valid verdict while the issue remains open.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/triage/SKILL.md
- **Concern**: Binding scope requires unmerged-branch larch-logs via git fetch and git show, but the plan only registers triage apply and triage probe in python/larch/cli.py and lists no helper or tests for that evidence path. Scenario: Cited run logs that exist only on an open PR never resolve on a typical clone unless a helper performs fetch plus show; investigation may fall back to prompt-side git or skip the evidence, yielding inconclusive or wrong valid verdicts
- **Proposed resolution**: Add a deterministic triage read-ref (or equivalent) verb in python/larch/issue/triage.py, register it in python/larch/cli.py, call it from skills/triage/SKILL.md for validated commit SHAs or refs/pull/N/head, and cover fetch-show success, rejection, and caps in python/tests/issue/test_triage.py and scripts/test-triage-structure.sh



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Plan specifies bespoke helper-owned triage block syntax instead of reusing issue_wire named-block parse, compose, and strip with marker triage. Scenario: A second malformed-block grammar can disagree with issue_wire on plan and design-pause markers and accept or reject protected bodies differently than the rest of larch
- **Proposed resolution**: Implement triage section splice via issue_wire.parse_named_block, compose_named_block, and strip_named_block with marker triage; keep compare-and-swap mutation only in triage apply ### 1. completeness — `skills/triage/SKILL.md` / `python/larch/cli.py` The binding scope anchor requires collecting cited `larch-logs/` from unmerged PR branches using `git fetch` plus `git show`. The plan mentions a deterministic ref helper in skill prose, but `### UPDATED: python/larch/cli.py` registers only `triage apply` and `triage probe`, and the planned `python/tests/issue/test_triage.py` coverage list has no fetch/show cases. That leaves the primary evidence path unspecified in the firm Python surface and untested. **Suggested revision:** Add and register a `triage read-ref` (or equivalent) helper, invoke it from the skill for validated SHAs or `refs/pull/<n>/head`, and pin behavior in unit and structural tests. ### 2. architecture — `python/larch/issue/triage.py` [SCOPE-REDUCTION] The plan tasks `triage.py` with validating “helper-owned triage block syntax” independently. `issue_wire.py` already owns named-block grammar (`<!-- larch:{marker}:start/end -->`) and malformed tokens for `plan` and `design-pause`. Duplicating that logic adds diff and drift risk against protected-state checks. **Suggested revision:** Reuse `issue_wire` parse/compose/strip with marker `triage` for section handling; keep `updatedAt` compare-and-swap and authorization in `triage apply` only.



### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/triage/SKILL.md:planned dependency and follow-up steps
- **Concern**: 1. Missing child-skill continuation and verification contract. Scenario: `/block-issue` can return terminal-looking output and halt triage before dependency read-back, cleanup, and machine keys. `/issue` follow-up failures also lack counter or sentinel verification.
- **Proposed resolution**: Add canonical anti-halt reminders, verify `/issue` through counters and a sentinel, and register triage in `skills/shared/subskill-invocation.md` and `scripts/test-anti-halt-banners.sh`.



### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/triage/SKILL.md:planned protected-state and verdict routing
- **Concern**: 2. Lifecycle rejection makes required title restoration unreachable. Scenario: `issue title-eligibility` rejects managed lifecycle prefixes before every mutable verdict, so an already-fixed or duplicate issue with such a prefix cannot restore its title and close as required.
- **Proposed resolution**: Reject active lifecycle state, but allow close verdicts to restore a stale prefix when no protected block or label remains. Test both paths.



### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/triage/SKILL.md:planned dependency application
- **Concern**: 3. The accepted per-mutation snapshot fix still omits dependency writes. Scenario: A collaborator can update the issue after `triage apply` succeeds but before `/block-issue`; triage then applies an edge based on stale analysis despite listing this race as an edge case.
- **Proposed resolution**: Thread the latest verified `updatedAt` into dependency application and make `issue_block.py` compare it immediately before mutation. Test that mismatch prevents the GraphQL mutation.



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/triage.py:planned triage probe
- **Concern**: 4. The probe policy excludes the specified external-tool reproduction path. Scenario: The blanket ban on networked, authenticated probes makes the cited Codex model probe and similar external-tool verification impossible, even when a fixed read-only experiment is safe.
- **Proposed resolution**: Allow narrowly named, fixed-destination, read-only external probes through existing credential-safe launch paths. Keep arbitrary commands, arguments, and destinations forbidden.



