### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:164-192
- **Concern**: Plan does not require renaming oos-3/oos-4 inputs from actual to kept items. Scenario: Items that pass actuality but are staged as pending merit rejection still match the skill's actual label; an orchestrator can feed them into deduplication or grouping before oos-4 confirmation
- **Proposed resolution**: In the FILES section, require oos-3 and oos-4 prose to use kept items (merit-pass, not blocked) and state explicitly that pending merit rejections are excluded until batch confirmation

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:208-209
- **Concern**: oos-4 partial-list approval semantics with merit rejections are undefined. Scenario: The plan adds a single merit batch gate but keeps apply specific groups or stale closures (list); selective apply can leave merit rejections unconfirmed, auto-applied, or applied while groups are skipped
- **Proposed resolution**: In oos-4 prose, define partial-list behavior: whether merit rejections require explicit yes/no on every path, and whether list selections apply only to groups and fully discarded closures

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/combine-issues/SKILL.md:190-220
- **Concern**: Rescue regroup does not require re-presenting a revised combination scheme. Scenario: Plan step 7 regroups after free-prose rescue but does not require showing the new groups; apply can run a scheme the operator never approved after rescued items change grouping
- **Proposed resolution**: Add oos-4 prose: after any rescue that changes kept-item membership or grouping, re-emit the combination proposal and require approval before oos-5 apply

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:190-220
- **Concern**: Free-prose merit rescue lacks a matching contract in oos-4. Scenario: Step 3 stages a stable display key but oos-4 only says free-prose rescue keeps named items; responses like keep the caching one can match the wrong item or be treated as cancel
- **Proposed resolution**: In oos-4, require rescue matching against the displayed stable key and issue number, default to keep on ambiguity, and never treat an unmatched rescue as batch approval

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:224-235
- **Concern**: oos-5 planned eligibility treats blocked-on-source items as closure-eligible. Scenario: The plan says a source may use --defer-close or qualify for close-sources when every item is stale, confirmed low-merit, consumed, or blocked on-source. A source with a blocked item plus confirmed low-merit or consumed items could be closed even though the plan's edge case says blocked items must keep the source open.
- **Proposed resolution**: Rewrite the oos-5 update so only stale auto-discarded, confirmed merit-rejected, and approved-group-consumed items count as consumed. State that any blocked, pending, rescued, or uncombined item keeps the source open and out of --source-issues.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:170-184
- **Concern**: Merit-pending runs must reach oos-4; oos-2 terminal halt still wins when zero kept items. Scenario: Current oos-2 ends at lines 170-180 when no actual items remain: it can close fully stale sources and stop before oos-4. After merit staging, zero kept items can coexist with pending low-merit items (all merit-rejected pending, or stale-only sources closed while other sources still have unconfirmed merit rejections). Those merit rejections never appear in the consolidated oos-4 list, so batch confirmation and honest fully-discarded closure cannot happen.
- **Proposed resolution**: In Files, replace the no-actual-items terminal branch: if any merit rejection is pending globally, do not close sources or stop in oos-2; continue to oos-3/oos-4 with zero kept items. Show Rejected items (merit) at oos-4 and run the single batch gate before any close-stale on fully discarded sources. Narrow or remove the oos-2-only close-and-stop path when merit pending exists.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:208-210
- **Concern**: Partial list approval leaves merit-rejection outcomes undefined. Scenario: Plan step 6 defines all-or-nothing merit approval, rescue, and cancel, but the skill keeps apply specific groups or stale closures (list). An operator can approve only some combination groups while merit rejections stay undefined: apply all rejections, apply none, or block combine until merit is decided. That breaks the acceptance criterion of one explicit batch decision per merit item.
- **Proposed resolution**: In oos-4 approval prose, pin partial-list semantics: merit rejections are decided only by the merit batch (approve all, free-prose rescue, or cancel). Partial group or stale selections must not confirm or apply any merit rejection. On cancel or partial group apply without an explicit merit decision, leave all merit rejections pending and do not close merit-affected sources.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:oos-4
- **Concern**: Free-prose rescue lacks a matching contract despite stable display keys. Scenario: Approach step 3 stages stable display keys and step 6 allows free-prose rescue, but the Files section does not require SKILL-level matching rules. Without them, keep the caching one or keep A and C can map to the wrong items or be treated as no match, violating default-keep bias and the operator rescue path.
- **Proposed resolution**: In oos-4, define rescue matching: accept issue number plus item title, the staged stable display key, or an unambiguous title substring; on ambiguous or no match, keep the item and ask once for clarification. Require the Rejected items (merit) list to show the same key on every line.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:235-243
- **Concern**: oos-5 fix makes blocked-on-source items count toward close eligibility. Scenario: The plan says a source may use --defer-close or qualify for close-sources when every item is stale, confirmed low-merit, consumed, or blocked on-source. If implemented literally, a source with a consumed item plus a blocked item can be listed for deferred closure and closed, losing the blocked item that current oos-2/oos-5 rules require keeping open.
- **Proposed resolution**: Revise the oos-5 plan text so only stale auto-discards, confirmed merit rejections, and consumed approved-group items count as consumed. Blocked-on-source items must stay close-blocking, remain in blocked_sources.json, and exclude the source from --source-issues and close-sources.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:208
- **Concern**: [ALREADY_ADDRESSED] oos-4 partial approval leaves merit-rejection outcomes undefined. Scenario: The plan adds batch merit confirm/rescue/cancel semantics but keeps the existing partial-apply prompt shape. An operator who applies only selected groups or stale closures can leave merit rejections unconfirmed or have them applied without an explicit batch decision.
- **Proposed resolution**: Add oos-4 prose: partial group/stale selection does not confirm merit rejections unless the operator explicitly approves them in the same response; otherwise merit stays pending, sources with pending merit stay open, and oos-5 cannot list them in --source-issues.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:164
- **Concern**: oos-2 step 4 must collect kept items only, excluding merit-pending. Scenario: The plan inserts the merit gate before flat-list collection but does not explicitly require replacing the current Collect all actual items bullet. Merit-pending items that passed actuality can still enter oos-3/oos-4 and be combined before operator confirmation.
- **Proposed resolution**: In the Files section, add an explicit edit to oos-2 step 4: collect only kept items (post-merit, not blocked) into the oos-3/oos-4 flat list; merit-pending items stay in the staged rejection list only.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/combine-issues/SKILL.md:243-326
- **Concern**: FINDING_1 incomplete: merit-pending sources need blocked_sources.json entries. Scenario: Plan step 10 updates oos-5 --source-issues rules but not blocked_sources materialization. Partially combined sources with merit-pending items can still reach close-eligible without a blocked_sources entry and be closed in oos-7.
- **Proposed resolution**: Add oos-5 prose: when materializing blocked_sources.json, include any source with pending merit items (or other unconsumed items) and a reason such as merit_pending; close-eligible must treat them as ineligible until merit is confirmed or rescued.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:oos-4
- **Concern**: oos-4 merit list must expose stable display keys for free-prose rescue. Scenario: The issue requires operators to rescue subsets via free prose (for example "keep A and C" or "keep the caching one"). The plan stages stable display keys in oos-2 but the Files checklist only requires one line per item with a cause, not that each listed row carry the stable key and issue ref shown in the acceptance example. Without visible keys and explicit rescue-matching rules, the orchestrator can misread prose and reject or keep the wrong items.
- **Proposed resolution**: Add to the Files section: each `Rejected items (merit):` line must prefix the stable display key and issue number (for example `A (#123)`), and oos-4 prose must define rescue matching priority (display key, then `#N`, then unique title substring) before any grouping or close steps run.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:235
- **Concern**: The oos-5 update treats "blocked on-source" items as a state that can qualify a source for --defer-close or close-sources.. Scenario: A source with one approved combined item and one blocked item can satisfy the proposed "every item is stale, confirmed merit-rejected, consumed, or blocked" rule, so the source can be sent to close-sources even though blocked items must remain open.
- **Proposed resolution**: Change oos-5 to say only stale auto-discards, confirmed merit rejections, and items consumed into approved groups count as consumed for deferred closure. Blocked items must remain close-blocking and be recorded in blocked_sources or left-open reasons.
