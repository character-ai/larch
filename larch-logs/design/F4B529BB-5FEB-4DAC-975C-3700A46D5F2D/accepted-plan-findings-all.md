### FINDING_1: oos-5 treats merit-rejected items as consumed
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Flow Contract
- **Severity**: blocking
- **Concern**: `oos-5` still needs explicit source-close rules for confirmed merit rejections, or deferred-close / `--source-issues` handling can treat rejected items as still uncombined and keep sources open incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add oos-5 prose (and `blocked_sources.json` carry-forward if needed): pending merit blocks deferred combination closure; confirmed merit-rejected items count as handled/discarded, not uncombined; only close when every item is stale, blocked, pending merit resolved, combined, or merit-rejected.
  - From Cursor-Innovation: Extend the oos-5 consumption rule so operator-confirmed merit rejections count as discarded/consumed like stale discards; keep blocked and pending-unconfirmed merit items as non-consuming
  - From Cursor-Pragmatic: Add explicit oos-5 prose that confirmed low-merit rejections count as discarded (like stale), not uncombined survivors; a source may defer-close only when every item is stale auto-discarded, merit-confirmed rejected, consumed into an approved group, or blocked on-source
  - From Cursor-Requirements: Extend the oos-5 eligibility bullet to treat operator-confirmed merit-rejected items like stale discards (fully accounted for, not uncombined) when deciding defer-close and blocked-source handling.
  - From Cursor-dyn-Prompt Flow Contract: Extend line 235: confirmed low-merit rejections count as consumed/non-surviving like stale discards; pending merit blocks listing; merit-emptied sources use close-stale at oos-4, never --source-issues / close-sources


### FINDING_2: Anti-pattern needs a merit-rejection carve-out
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The “never discard actionable content” anti-pattern is too broad for confirmed merit rejections; without a carve-out, the new gate can look forbidden even when the operator explicitly approved the discard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a carve-out: confirmed low-merit rejections after oos-4 batch approval are allowed discards; add "NEVER auto-apply merit rejections before oos-4 confirmation" beside the existing confirmation anti-patterns.
  - From Cursor-Innovation: Add a narrow anti-pattern exception: merit rejections confirmed in the oos-4 batch gate may discard items; combination bodies must still preserve every kept item’s actionable content
  - From Cursor-Pragmatic: Scope the anti-pattern to combined-body merges; state that operator-confirmed merit rejection at `oos-4` is permitted.


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


### FINDING_5: Closure eligibility must not consume blocked or pending items
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The oos-5 closure path can treat blocked-on-source or still-pending items as consumed, and the blocked-sources bookkeeping can miss sources that should remain open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Rewrite the oos-5 update so only stale auto-discarded, confirmed merit-rejected, and approved-group-consumed items count as consumed. State that any blocked, pending, rescued, or uncombined item keeps the source open and out of --source-issues.
  - From Cursor-Pragmatic: Add oos-5 prose: when materializing blocked_sources.json, include any source with pending merit items (or other unconsumed items) and a reason such as merit_pending; close-eligible must treat them as ineligible until merit is confirmed or rescued.
  - From Codex-Innovation: Revise the oos-5 plan text so only stale auto-discards, confirmed merit rejections, and consumed approved-group items count as consumed. Blocked-on-source items must stay close-blocking, remain in blocked_sources.json, and exclude the source from --source-issues and close-sources.
  - From Codex-Requirements: Change oos-5 to say only stale auto-discards, confirmed merit rejections, and items consumed into approved groups count as consumed for deferred closure. Blocked items must remain close-blocking and be recorded in blocked_sources or left-open reasons.


