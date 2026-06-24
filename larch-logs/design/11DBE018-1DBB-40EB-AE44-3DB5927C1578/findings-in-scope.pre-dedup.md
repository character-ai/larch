### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:103-111
- **Concern**: Step 5c site spec still omits imperative load directive and confirmation_purpose. Scenario: Prior round 4 accepted this gap; the Step 5c block lists only inline parameters (breadcrumb, sentinel, after_present, extra_guards) and never the `Read and apply ## Immediate-background wait rule` line or `confirmation purpose: completion`. Final summary (plan 76-84), harness per-site table (160-161, 165-166), and failure modes (208, 214) require both. Literal plan-following can leave the full duplicated Immediate-background paragraph, skip loading the shared anchor, and drop completion probe wording while other sites migrate.
- **Proposed resolution**: In the **Step 5c** site spec, mirror Final summary: add `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.` before the inline parameter list, and add `confirmation purpose: completion` to that list.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:98-101
- **Concern**: Step 3 resume site uses passive cross-reference and spells only directive 2 of three. Scenario: Prior round 4 accepted incomplete resume parity. The resume block says "Apply the same three read-and-apply replacements as Step 3 first launch" but only expands item 2; directives 1 and 3 are absent. That conflicts with the plan's own rule (line 61) forbidding passive cross-references alone. Harness `LOAD_LITERAL` greps (158-160) require all three section names at the resume locus. An implementer editing only the resume fence can leave duplicated boundary/post-notification prose or a pointer stub and still think the site is done.
- **Proposed resolution**: Replace the resume cross-reference with the same three fully spelled read-and-apply lines as first launch (87-95), including directive 1 (task notification boundary) and directive 3 (post-notification sequence), plus the identical Immediate-background inline parameter block; add an explicit note to remove the duplicated `After the completion gate…` numbered list at the resume site (as line 96 requires for first launch).



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:103-111
- **Concern**: Step 5c site spec still omits imperative load directive and confirmation_purpose (prior round-4 fix incomplete). Scenario: The Step 5c UPDATED block lists only inline parameters (breadcrumb, sentinel, after_present, extra_guards) and never the `Read and apply ## Immediate-background wait rule` directive or `confirmation purpose: completion`. Final summary (plan lines 76-84), harness per-site table (lines 160-161, 165), failure modes (lines 207-208, 214), and harness docs (lines 188-191) require both. Literal plan-following can ship a parameter-only stub, skip the shared anchor, and still aim for harness path greps that the SKILL.md edit section never mandates.
- **Proposed resolution**: Mirror the Final summary block shape: add `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.` before the inline parameter list, and add `confirmation purpose: completion` alongside breadcrumb and terminal sentinel.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:98-101
- **Concern**: Step 3 resume site spec does not enumerate all three read-and-apply directives (prior round-4 fix incomplete). Scenario: The resume block claims byte-identical directives 1-3 but only spells out item 2 (Immediate-background wait rule plus parameters). Items 1 (task notification boundary) and 3 (post-notification sequence) are absent. The plan forbids passive cross-references alone, and harness LOAD_LITERAL checks expect all three section names at the resume locus (plan lines 160, 209). An implementer editing only the resume fence can leave duplicated boundary and post-notification prose while first launch is migrated.
- **Proposed resolution**: Expand the Step 3 resume block to list all three directives verbatim, matching lines 88-95 from first launch (boundary, Immediate-background with the same inline parameter block, post-notification sequence), then keep resume-specific NEXT_ACTION and wrapper-flag prose.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:103-111
- **Concern**: Step 5c site spec still omits imperative load directive and confirmation_purpose (prior accepted fix incomplete). Scenario: The `### UPDATED: skills/design/SKILL.md` Step 5c block lists only inline parameters (breadcrumb, sentinel, after_present, extra_guards) and never the `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.` line or `confirmation purpose: completion`. The same plan requires both at Final summary (lines 76-84), in Failure modes (lines 207-208), and in harness per-site checks (lines 161, 165, 188-191). Literal plan-following can replace the duplicated paragraph with a parameter-only stub, skip loading the shared anchor, drop premature-probe wording, and still aim for other sites—then fail `make lint` only if the implementer reads the harness section.
- **Proposed resolution**: Spell out Step 5c to mirror Final summary: add the imperative `Read and apply ## Immediate-background wait rule…` directive first, then the inline parameter block including `confirmation purpose: completion`, matching lines 76-84.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:98-101
- **Concern**: Step 3 resume site still incomplete versus harness anchored LOAD_LITERAL greps (prior accepted fix incomplete). Scenario: The resume block says “Apply the same three read-and-apply replacements as Step 3 first launch (byte-identical directives 1–3)” but only enumerates directive 2 inline. Plan line 61 forbids passive cross-references alone; Failure modes (lines 209-210) warn resume omitting boundary or post-notification reads. Harness lines 160 and 147-153 require all three `Read and apply ##` strings physically present at the resume locus via anchored greps—not inherited by reference from the first-launch section. An implementer editing only the resume fence can leave directives 1 and 3 as implicit cross-refs, keep duplicated boundary/post-notification prose, and fail harness or break turn-control parity.
- **Proposed resolution**: At Step 3 resume, explicitly list all three byte-identical directives (task notification boundary, Immediate-background wait rule with the same inline parameter block as first launch, post-notification sequence)—same literal strings as lines 88-95—not only directive 2 under a “same as first launch” stub.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:103-111
- **Concern**: Step 5c site spec still omits imperative load directive and confirmation_purpose. Scenario: The Step 5c block lists only inline parameters (breadcrumb, terminal sentinel, after_present, extra_guards) and never includes `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.` or `confirmation purpose: completion`. Final summary (plan lines 76-84), harness per-site table (lines 161 and 165), failure modes (lines 208-209 and 214), and harness docs (line 188) all require both. Literal plan-following can leave the full duplicated Immediate-background paragraph at skills/design/SKILL.md:864, skip loading the shared anchor, drop completion probe wording, and fail the planned `$CONFIRMATION_COMPLETION` grep even after other sites migrate.
- **Proposed resolution**: Add to the Step 5c site spec the same pattern as Final summary: the imperative `Read and apply ## Immediate-background wait rule...` line plus inline parameters including `confirmation purpose: completion`, matching harness locus 5 expectations.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:98-101
- **Concern**: Step 3 resume site still relies on passive cross-reference for two of three read-and-apply directives. Scenario: Prior-round fix added “byte-identical directives 1–3” but the resume block still enumerates only directive 2 and points at first launch for the rest. Plan line 61 forbids passive cross-references alone; harness lines 160-161 require anchored `Read and apply ##` literals for all three section names independently at the `--starting-round` resume locus. An implementer editing only the resume fence can keep duplicated ta<REDACTED-TOKEN> and post-notification prose (today at skills/design/SKILL.md:651-664), satisfy a partial migration, and fail dedup or LOAD_LITERAL checks.
- **Proposed resolution**: Spell out all three read-and-apply directives at the Step 3 resume site with the same literal text as first launch (lines 88-95), not only directive 2; keep resume-specific NEXT_ACTION prose around them.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:103-111
- **Concern**: Step 5c site spec still omits the required read-and-apply directive and confirmation purpose. Prior accepted fix is incomplete.. Scenario: The Step 5c replacement block lists only parameters. A literal implementation can leave no `Read and apply ## Immediate-background wait rule...` directive at the hot path and omit `confirmation purpose: completion`, violating the feature's all-five-sites load contract.
- **Proposed resolution**: Add the Step 5c read directive before its inline parameter block, and include `confirmation purpose: completion` in that block.



