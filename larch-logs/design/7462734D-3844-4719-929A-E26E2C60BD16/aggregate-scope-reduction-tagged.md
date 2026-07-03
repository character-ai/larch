### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:161
- **Concern**: [SCOPE-REDUCTION] Gate C **When** paragraph is absent from the compression edit list even though issue scope covers per-gate instruction prose. Scenario: The **When** block is ~1.2KB of routing recap (Gate B settled paths, bypass statuses, re-entry) already carried in Gate C body bullets, SKILL.md Step 4b, and renderer option shaping. The plan only targets renderer-owned cap copy (`## Review-round cap`, `### Gate C tier cap`) plus Gate A/B dedupe. If those edits save less than ~1k closure tokens, the blocking acceptance gate tells the implementer to keep trimming renderer-duplicated prose only, with no authorized surface left except pinned literals.
- **Proposed resolution**: Add an explicit Gate C edit item: compress **When** to a short pointer (panel-init-failed never reaches; bypass paths continue 3b→4→4b; re-entry via Discuss further) while keeping Presentation, Prompt dispatch, persistence fail-closed, Other, and approve-is-not-a-halt. List it in the acceptance-gate remediation path when pre/post closure is short of ~1k.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:236-245
- **Concern**: [SCOPE-REDUCTION] The blocking ~1k-token closure gate only authorizes trimming renderer-duplicated gate prose, but approval-gates.md still eager-loads a misplaced Step 5c validator tail (lines 239-243) plus a compatibility note (245) that finalize-step5.md, validator-failure.md, and SKILL.md already own; test-design-structure.sh even requires Step 5c composition detail to live in finalize-step5, not approval-gates.. Scenario: If renderer-only compression falls short of ~1000 tokens, the plan gives no allowed next trim while this non-gate block stays in the design eager closure, so the PR can pass harnesses yet fail the issue’s stated acceptance gate or force more gate-prose cuts that risk pinned literals.
- **Proposed resolution**: Add an explicit edit bullet: delete lines 239-245 (Step 5c missing-composed-plan and --skip-validate recovery plus the settle compatibility note) from approval-gates.md; keep loop-mode Gate B contract at 236-237 only if not duplicated elsewhere after Gate B compression. Count this removal toward the pre/post closure acceptance measurement.
