### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:259-266
- **Concern**: No test for pattern check on REVIEWER_FILE retry rewrite. Scenario: Retry path checks original output; silent acceptance of bad retry file
- **Proposed resolution**: Add collect stub or integration case where STATUS=OK and REVIEWER_FILE points at *-retry.txt with/without heading


### [Plan Review] FINDING_22

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-caller-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:69;scripts/dispatch-with-waterfall.md
- **Concern**: Sketch and plan-review out-of-scope exclusions live only in issue body and plan Approach not in any planned .md update. Scenario: Implementors reading touched docs will not know why dispatch-plan-review-panel.sh and sketch paths were not migrated; future adopters may duplicate post-call grep without understanding boundary
- **Proposed resolution**: Add an explicit Non-adopters / out-of-scope paragraph to scripts/dispatch-with-waterfall.md naming sketch-phase (no waterfall caller) and plan-review collectors (collect-agent-results downstream validation); mirror one line in skills/design/references/decompose-panel.md


### [Plan Review] FINDING_25

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-caller-audit
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:241-247,387-398,516-520; skills/design/references/plan-review.md:38-40,87-90
- **Concern**: Plan-review collector exclusion is not recorded in any proposed markdown update. Scenario: Repository grep shows plan-review dispatch is an unlisted dispatch-with-waterfall caller and its collector path performs downstream structured grep/validation; the plan leaves the exclusion only in plan prose/issue-body rationale, so future adopters lack a durable contract explaining why this caller does not opt into --require-result-pattern
- **Proposed resolution**: Add an explicit adoption-scope paragraph to a modified md file such as scripts/dispatch-with-waterfall.md: decompose callers opt in; plan-review collectors stay on collect-agent-results --structured-reviewer-validation plus plan-review-loop parsing; sketch phase does not use dispatch-with-waterfall


### [Plan Review] FINDING_27

### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:43-51 (proposed stub) and plan.txt:49
- **Concern**: Proposed positive case asserts ALL_OUTPUT_TOOLS=codex and FALLBACK_COUNT=0 only, not DISPATCH_OK=true. Scenario: A partial dispatcher regression could leave DISPATCH_OK=false while the planned KVs still look plausible in some failure shapes
- **Proposed resolution**: Also assert_line DISPATCH_OK=true in the new --require-result-pattern case alongside the existing KV checks


