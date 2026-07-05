### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:412-413
- **Concern**: Step 3 post-loop routing prose is missing from the firm SKILL.md update list. Scenario: The plan updates anti-pattern #5 and Step 5c wait prose but leaves the Step 3 `NEXT_ACTION` preamble at ~413 saying to "yield or probe without parsing" on any premature notification. An orchestrator following that paragraph can still foreground-probe prefix-identical repeat notifications instead of silent-yielding first, so the #6309 Step 3 routing carve-out stays incomplete on the live control path.
- **Proposed resolution**: Add a firm `skills/design/SKILL.md` bullet to amend the Step 3 post-loop routing preamble (~413) with the same ordered contract as the updated anti-pattern: empty output → silent yield; prefix-identical repeat over the first 200 chars with absent `{terminal_sentinel}` → silent yield; first/changed non-empty premature output → at most one foreground probe.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: The proposed Step 3 pin targets anti-pattern #5 apply text, not the post-loop routing paragraph. Scenario: The harness item pins "the ordered premature-notification rule from the Step 3 NEVER #5 apply text," which lives in the Anti-patterns section, not in the Step 3 `NEXT_ACTION` routing block at ~413. CI can pass while the operational Step 3 routing paragraph still lacks repeat handling, reproducing the accepted contract-test gap.
- **Proposed resolution**: After adding the ~413 routing update, pin a substring unique to that paragraph (for example the ordered empty → prefix-identical repeat → probe rule). Do not treat anti-pattern #5 text alone as coverage for Step 3 post-loop routing. ## Findings ### 1. correctness — `skills/design/SKILL.md:412-413` The plan’s firm `skills/design/SKILL.md` edits cover anti-pattern #5 and Step 5c, but not the Step 3 post-loop `NEXT_ACTION` preamble. That paragraph still authorizes “yield or probe” on premature notifications without ordering prefix-identical repeat silent-yield first. Issue #6309 explicitly calls out Step 3 routing text; leaving ~413 unchanged means the feature can ship with the old probe-eligible path on repeat notifications. **Suggested revision:** Add a firm plan bullet to update ~413 with the ordered empty → prefix-identical repeat (first 200 chars) → probe contract, using the active wait’s terminal sentinel rather than a hardcoded Step 3 sentinel. ### 2. risk-integration — `scripts/test-design-structure.sh` The proposed Step 3 harness pin is labeled “post-loop routing” but sources literals from anti-pattern #5 apply text. That lets CI pass when only the Anti-patterns section mentions prefix-identical repeats, while the Step 3 routing paragraph at ~413 remains unchanged. This leaves the round-1 accepted contract-test goal incomplete for the surface orchestrators actually follow during Step 3 loop routing. **Suggested revision:** Pin the updated ~413 routing prose directly, or add an explicit plan step plus a `contains "$SKILL_MD"` check targeting that paragraph.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 post-loop routing is absent from the firm UPDATED list while the harness pins ordered prefix-identical repeat handling. Scenario: The plan adds a test-design-structure contains pin for Step 3 post-loop prefix-identical repeat routing but the ### UPDATED: skills/design/SKILL.md section only lists anti-pattern #5 and Step 5c edits. Line 413 still says treat premature notifications as yield or probe without ordering empty output prefix-identical repeat and first or changed non-empty output. An implementer can satisfy anti-pattern #5 and Step 5c yet leave the core Step 3 NEXT_ACTION gate probe-eligible on repeats.
- **Proposed resolution**: Add a firm bullet under ### UPDATED: skills/design/SKILL.md to rewrite the Step 3 post-loop premature-notification paragraph before the NEXT_ACTION table: empty output silent yield; prefix-identical repeat over the first 200 chars with the active terminal sentinel absent silent yield; first or changed non-empty premature output at most one foreground probe per shared rules; only then parse when the terminal sentinel is present.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81
- **Concern**: Planned anti-pattern #5 edits do not define the ordered rule the new harness pin references. Scenario: The harness calls for the ordered premature-notification rule from the Step 3 NEVER #5 apply text but the planned #5 edits only swap prefix-identical terminology and generalize the sentinel placeholder. They do not require an explicit empty then prefix-identical repeat then probe-on-first-changed sequence. CI can pass duplicated carve-out phrases while orchestrators still probe before evaluating repeat fingerprints.
- **Proposed resolution**: Extend the ### UPDATED: skills/design/SKILL.md anti-pattern #5 bullet to require a short ordered Apply block matching the Step 3 post-loop edit and align the test-design-structure pin to that exact substring so anti-pattern #5 and Step 3 routing share one decision tree.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 post-loop NEXT_ACTION preamble is not a firm deliverable. Scenario: The plan updates anti-pattern #5, shared wait prose, Tier-1 carve-outs, and Step 5c, but it never requires replacing the post-loop line that still says to treat a premature notification as yield or probe without parsing. That line is the routing gate after Step 3 review returns; it still authorizes a foreground probe on every non-empty premature notification, including prefix-identical repeats, so the reported re-notification loop can persist even after the other prose edits land.
- **Proposed resolution**: Add a firm ### UPDATED: skills/design/SKILL.md bullet to rewrite the post-loop premature-notification preamble with the ordered contract: empty output silent yield; prefix-identical repeat over the first 200 chars with absent active terminal sentinel silent yield; first or changed non-empty premature notification at most one foreground probe; sentinel present then post-notification routing.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: Harness pin targets ordered NEVER #5 text that the prose section does not define. Scenario: The plan tells test-design-structure.sh to pin the Step 3 post-loop prefix-identical repeat routing instruction from the Step 3 NEVER #5 apply text, but the NEVER #5 edit section only renames the title, swaps byte-identical for prefix-identical, and generalizes the sentinel. It does not require adding the ordered premature-notification decision tree that the harness label describes, so CI can pass while the pinned substring lives only in anti-patterns and the real post-loop routing bug at line 413 remains.
- **Proposed resolution**: Make the harness and prose edits agree: either add the ordered apply text to the NEVER #5 deliverable and pin that exact substring, or add a separate contains pin on the rewritten line-413 preamble so the harness guards the routing surface that actually drives post-loop behavior.



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh
- **Concern**: Step 3 and Step 5c repeat pins are global instead of context-bound. Scenario: The plan can pass by adding prefix-identical wording only to anti-pattern #5 while leaving the Step 3 post-loop or Step 5c routing text probe-first, so the accepted contract-test fix remains incomplete
- **Proposed resolution**: Use context-bound assertions around the Step 3 post-loop anchor and the Step 5c fence/routing anchor, and pin repeat-before-probe silent-yield text at each site



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 post-loop routing still says yield or probe without ordered repeat silent-yield handling. Scenario: The plan adds a harness pin for Step 3 post-loop prefix-identical repeat routing, but the `### UPDATED: skills/design/SKILL.md` bullets never require replacing the existing premature-notification sentence that tells orchestrators to yield or probe when `.completed/step-3-terminal` or `.step3-review-result.env` is absent. An implementer can add repeat prose elsewhere while this line still authorizes probing on prefix-identical repeats, recreating the original mis-route.
- **Proposed resolution**: In `skills/design/SKILL.md` Step 3 post-loop routing, replace yield or probe without parsing with an explicit ordered rule: empty output ends silently; prefix-identical repeat (first 200 chars) with absent `{terminal_sentinel}` ends silently; first or changed non-empty premature output gets at most one foreground probe; proceed only after the terminal sentinel is present.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: AGENTS.md:64
- **Concern**: AGENTS.md plan adds a repeat carve-out but does not qualify the leading non-empty probe rule. Scenario: The planned AGENTS.md edit only appends a prefix-identical repeat silent-yield sentence after an unconditional For `/design`, when a premature notification fires with non-empty task output, probe rule. The orchestrator-never.md edit explicitly preserves probe only for new or changed non-empty output, but AGENTS.md does not, so Tier-1 readers can still probe on every non-empty notification including repeats before reaching the carve-out.
- **Proposed resolution**: Qualify the AGENTS.md non-empty premature-notification sentence to first or changed non-empty output only, and state evaluation order: empty output silent yield; prefix-identical repeat (first 200 chars) with absent terminal sentinel silent yield; otherwise one foreground probe against the active wait terminal sentinel.



