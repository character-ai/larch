### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:MAY_UPDATE
- **Concern**: Blocking ~1k-token gate remediation is narrower than the savings budget the file can still yield. Scenario: The MAY_UPDATE procedure says to keep compressing renderer-duplicated prose if savings fall short. Inline Gate A/C question strings are already gone (`test-design-structure.sh` `not_contains` checks). Remaining high-yield prose is operational: **When**, large-plan summary mode under Presentation, Gate A loop-exit duplicates, and State invariants. Authorizing only renderer dedupe after the planned cap-section rewrite can stall the PR or push edits into grep-pinned Gate B / settle / resume literals.
- **Proposed resolution**: Extend acceptance-gate step 2: after renderer-owned excision, allow minimum-change trims explicitly named in edit items 3–5 plus Gate C **When**/Presentation summary tightening before any retained-literal edits; fail closed if the target is still missed.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:45-45
- **Concern**: FINDING_6 follow-up: retained-literal list paraphrases the Gate A missing-plan warning instead of pinning the exact string. Scenario: Required literals say the warning text must survive but do not quote `**⚠ plan.txt missing or empty; nothing to show.**`. Edit item 3 allows folding the subsection into Shape 2; paraphrase during compression drops the fail-closed recovery contract even though routing to `--without-see-full-plan` remains.
- **Proposed resolution**: Add that warning string verbatim to Required retained literals (same tier as the `FINDING_IDS` sentence) and to edit item 3 as non-paraphrasable text.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:13-15
- **Concern**: Edit item 1 replaces ## Review-round cap with a renderer pointer but only names three orchestration bullets to keep; it does not explicitly retain the Step 3 cap short-circuit contract (enforce on every Step 3 entry and emit the cap-hit breadcrumb before Step 3b/4/Gate C).. Scenario: The dense paragraph at lines 13-15 is the sole normative copy of those behaviors inside approval-gates.md; a renderer-only rewrite can drop them while SKILL.md keeps only a shorter cap guard, changing operator-visible cap-hit routing even though render-gate output stays byte-identical.
- **Proposed resolution**: In edit item 1, add retained orchestration literals: Step 3 enforces the cap on every entry (initial, Gate C re-run, Gate A Ready for review) and prints the existing cap-hit breadcrumb before skipping the panel; keep SKILL.md as sole counter-writer and plan_review.py stateless for review-round-count.txt.
