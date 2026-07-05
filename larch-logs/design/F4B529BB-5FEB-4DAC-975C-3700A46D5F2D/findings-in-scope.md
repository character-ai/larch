### FINDING_1: Merit-pending items can be dropped before batch confirmation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: oos-2 can still collect or stop on the wrong item set when merit rejections are pending, letting items reach combination or closure without the required consolidated oos-4 confirmation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the FILES section, require oos-3 and oos-4 prose to use kept items (merit-pass, not blocked) and state explicitly that pending merit rejections are excluded until batch confirmation
  - From Cursor-Innovation: In Files, replace the no-actual-items terminal branch: if any merit rejection is pending globally, do not close sources or stop in oos-2; continue to oos-3/oos-4 with zero kept items. Show Rejected items (merit) at oos-4 and run the single batch gate before any close-stale on fully discarded sources. Narrow or remove the oos-2-only close-and-stop path when merit pending exists.
  - From Cursor-Pragmatic: In the Files section, add an explicit edit to oos-2 step 4: collect only kept items (post-merit, not blocked) into the oos-3/oos-4 flat list; merit-pending items stay in the staged rejection list only.

### FINDING_2: Partial approval semantics leave merit outcomes undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The oos-4 batch gate does not pin down what happens when an operator approves only some groups or stale closures, so merit rejections can be implicitly confirmed, left ambiguous, or applied without an explicit batch decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In oos-4 prose, define partial-list behavior: whether merit rejections require explicit yes/no on every path, and whether list selections apply only to groups and fully discarded closures
  - From Cursor-Innovation: In oos-4 approval prose, pin partial-list semantics: merit rejections are decided only by the merit batch (approve all, free-prose rescue, or cancel). Partial group or stale selections must not confirm or apply any merit rejection. On cancel or partial group apply without an explicit merit decision, leave all merit rejections pending and do not close merit-affected sources.
  - From Cursor-Pragmatic: Add oos-4 prose: partial group/stale selection does not confirm merit rejections unless the operator explicitly approves them in the same response; otherwise merit stays pending, sources with pending merit stay open, and oos-5 cannot list them in --source-issues.

### FINDING_3: Rescue-triggered regrouping must be re-approved
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After a rescue changes kept-item membership or grouping, the revised combination scheme can be applied without the operator ever approving the new grouping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add oos-4 prose: after any rescue that changes kept-item membership or grouping, re-emit the combination proposal and require approval before oos-5 apply

### FINDING_4: Free-prose rescue needs explicit matching keys
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Free-prose rescue can mis-target items unless the merit list shows stable display keys and oos-4 defines a clear matching order; otherwise ambiguous requests can keep or reject the wrong items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In oos-4, require rescue matching against the displayed stable key and issue number, default to keep on ambiguity, and never treat an unmatched rescue as batch approval
  - From Cursor-Innovation: In oos-4, define rescue matching: accept issue number plus item title, the staged stable display key, or an unambiguous title substring; on ambiguous or no match, keep the item and ask once for clarification. Require the Rejected items (merit) list to show the same key on every line.
  - From Cursor-Requirements: Add to the Files section: each `Rejected items (merit):` line must prefix the stable display key and issue number (for example `A (#123)`), and oos-4 prose must define rescue matching priority (display key, then `#N`, then unique title substring) before any grouping or close steps run.

### FINDING_5: Closure eligibility must not consume blocked or pending items
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The oos-5 closure path can treat blocked-on-source or still-pending items as consumed, and the blocked-sources bookkeeping can miss sources that should remain open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Rewrite the oos-5 update so only stale auto-discarded, confirmed merit-rejected, and approved-group-consumed items count as consumed. State that any blocked, pending, rescued, or uncombined item keeps the source open and out of --source-issues.
  - From Cursor-Pragmatic: Add oos-5 prose: when materializing blocked_sources.json, include any source with pending merit items (or other unconsumed items) and a reason such as merit_pending; close-eligible must treat them as ineligible until merit is confirmed or rescued.
  - From Codex-Innovation: Revise the oos-5 plan text so only stale auto-discards, confirmed merit rejections, and consumed approved-group items count as consumed. Blocked-on-source items must stay close-blocking, remain in blocked_sources.json, and exclude the source from --source-issues and close-sources.
  - From Codex-Requirements: Change oos-5 to say only stale auto-discards, confirmed merit rejections, and items consumed into approved groups count as consumed for deferred closure. Blocked items must remain close-blocking and be recorded in blocked_sources or left-open reasons.
