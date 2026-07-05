### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:224-231
- **Concern**: Superseded oos-4 merit/rescue bullets are not explicitly removed when adding the new contract. Scenario: The plan adds key-matching, merit-batch timing, and dedup gates but only says to replace the free-prose rescue rule. Lines 224-231 still say batch approval confirms every rejection, unrescued items are confirmed rejected on rescue, and dedup runs after any rescue. An additive edit leaves contradictory instructions; zero-match or multi-match rescue can still confirm rejections or rerun dedup early.
- **Proposed resolution**: In the oos-4 edit step, replace the whole Merit rejections require block and the After any rescue paragraph (224-231) with the new contract; delete bullets that conflict with zero-match keep-pending, multi-match re-confirmation, and confirmed-rescues-only dedup. 1. **correctness** — `.claude/skills/combine-issues/SKILL.md:224-231`: Superseded oos-4 merit/rescue bullets are not explicitly removed when adding the new contract. The plan’s new sections address prior-round rescue, merit-timing, and dedup findings, but the existing block still contradicts them. An implementer who only appends the new bullets leaves line 227 (“unrescued listed items are confirmed rejected”) and line 231 (“After any rescue, rerun deduplication”) in force, which reintroduces the bugs this change is meant to fix. Revise the plan to require replacing or deleting lines 224-231, not only inserting new prose after them. [OUT_OF_SCOPE] **README.md:220** — The feature matrix `--oos` blurb still mentions actuality-only discard behavior and omits the merit gate. Item 1 scopes updates to frontmatter and `docs/skills.md` only, so this is not required for the stated follow-up, but README will keep drifting from the updated catalog until a separate sync lands.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:222-231
- **Concern**: Prior rescue-key fixes omit explicit rewrite of contradictory oos-4 operator prompt and merit-batch bullets. Scenario: The plan adds key-matching and merit-timing bullets but the Files checklist only says to replace the simple free-prose rescue rule inside the merit-batch section. Lines 222, 226, 227, and 231 still invite free-prose rescue, confirm every listed rejection on rescue, and rerun dedup after any rescue. An implementer can append the new contract and leave those lines, so zero-match or multi-match rescue can still confirm the wrong merit keys or regroup before disambiguation.
- **Proposed resolution**: In the ### UPDATED checklist, require rewriting the approval AskUserQuestion at line 222 to rescue by stable keys only (e.g. A or #12/A), replace bullets at 226-227 so merit approval confirms only fully resolved non-rescued keys, and change line 231 to rerun dedup/grouping only after confirmed rescues.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:222
- **Concern**: oos-4 AskUserQuestion still invites free-prose rescue. Scenario: The plan adds key-only rescue matching but does not require rewriting the oos-4 approval AskUserQuestion, which still offers "rescue named merit items in free prose." Operators will keep sending titles or prose; the new matcher will zero-match or multi-match more often and stall the run.
- **Proposed resolution**: In the oos-4 UPDATED steps, also replace the AskUserQuestion option with key-based rescue wording (e.g., rescue by stable key or #source/key) and drop "free prose."

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:224-231
- **Concern**: Same-response rescue must run before merit confirmation. Scenario: The plan gates ambiguous rescues but does not order parsing when one reply combines Apply all and rescue keys. Merit confirmation applied first can reject keys that the same message intended to rescue.
- **Proposed resolution**: Add one merit-batch timing rule: in a single operator response, resolve rescue matching (and multi-match confirmation) before any merit-batch confirmation, including Apply all; exclude confirmed-rescued keys from rejection.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:222-231
- **Concern**: oos-4 still has legacy merit/rescue/dedup bullets that contradict the new contract. Scenario: Plan adds key-only rescue, deferred merit confirmation, and confirmed-rescue dedup timing but only says to replace the simple free-prose rescue rule. Lines 222-231 still invite free-prose rescue, say merit batch approval confirms every listed rejection, treat free-prose rescue as confirming unrescued items, and rerun dedup after any rescue. An add-only edit leaves contradictory orchestrator rules, so zero-match or multi-match rescue can still confirm rejections or refresh grouping too early.
- **Proposed resolution**: In oos-4, explicitly replace the approval prompt and the Merit rejections require an explicit merit batch outcome block (lines 222-231), not append beside it. Remove free-prose rescue wording. Align approval and dedup bullets with the new timing sections. State that legacy bullets must not remain. ### 1. correctness — `.claude/skills/combine-issues/SKILL.md:222-231` The plan’s new oos-4 contract (key-only rescue, zero/multi-match pending, merit batch only after resolved rescues, dedup only after confirmed rescues) addresses accepted round-1 findings, but it does not require removing the existing contradictory prose at lines 222–231. That block still: - asks operators to “rescue named merit items in free prose” (line 222); - says merit batch approval “confirms every listed merit rejection” (line 226); - treats a free-prose rescue as confirming unrescued items (line 227); - reruns dedup “after any rescue” (line 231). If implementation only appends the new bullets, the skill will contain two incompatible rescue/merit/dedup contracts. That revives the round-1 breakage modes the plan is meant to fix. **Suggested revision:** In the plan’s `### UPDATED: .claude/skills/combine-issues/SKILL.md` section, require an explicit replace of lines 222–231 (approval prompt plus merit-batch outcome bullets), not a partial rescue-rule swap. Call out deletion of free-prose rescue, confirm-all-on-approval, and after-any-rescue dedup language. --- **[OUT_OF_SCOPE]** `.claude/skills/combine-issues/SKILL.md:207-212` — Prefer showing `#source/key` in the `Rejected items (merit)` list when bare keys would collide across sources. The plan already handles collision at rescue time via multi-match pending; proactive display formatting would reduce ambiguity but is not required for correct behavior. **[OUT_OF_SCOPE]** `.claude/skills/combine-issues/SKILL.md:3` — Draft a candidate frontmatter `description:` string with a char budget note. Failure mode and lint commands are enough; the implementer can iterate under the 200-char cap without a plan-supplied template.
