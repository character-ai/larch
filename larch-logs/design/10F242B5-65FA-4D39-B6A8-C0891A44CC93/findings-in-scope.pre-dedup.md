### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/discussion-rounds.md
- **Concern**: The per-file UPDATE subsection claims numbered steps 1–2 mirroring approval-gates.md step 8 but enumerates only step 2; round-4 accepted fix remains incomplete.. Scenario: An implementer following only the discussion-rounds bullets adds a variant pointer or paraphrase without the exact step 1 MANDATORY — READ ENTIRE FILE line test-design-structure.sh requires (plan lines 106–108, 120). Inline rc prose can remain or structure lint fails; four-way drift persists at Round 2.
- **Proposed resolution**: Add explicit numbered step 1 under the discussion-rounds UPDATE block, matching approval-gates.md: 1. MANDATORY — READ ENTIRE FILE: Read skills/design/references/settle-rc-dispatch.md completely. 2. Apply the Gate A / discussion-round2 variant row before branching on wrapper exit status ($?).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md
- **Concern**: The per-file UPDATE claims explicit numbered step 1 at both optional-trailer guards but lists only step 2 under Gate A (~411) and Gate B (~714); round-4 accepted fix remains incomplete.. Scenario: Implementers can ship pointer-only edits at both guards while inline Branch on wrapper rc enumeration survives, breaking harness assertions (plan lines 107–108, 130) and preserving four dispatch copies.
- **Proposed resolution**: Under each optional-trailer guard heading in the SKILL.md UPDATE subsection, add explicit numbered step 1: MANDATORY — READ ENTIRE FILE: Read skills/design/references/settle-rc-dispatch.md completely. Keep step 2 as the Gate A or Gate B variant-pointer directive.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md
- **Concern**: Round 4 fix still incomplete: per-file UPDATE lists only step 2 despite claiming numbered steps 1–2. Scenario: The `### UPDATED: discussion-rounds.md` block says it mirrors `approval-gates.md` step 8 with numbered steps 1–2 but enumerates only step 2 (variant pointer). Edge cases and failure modes require step 1 `MANDATORY — READ ENTIRE FILE` before branching; `test-design-structure.sh` will assert that phrase. An implementer following only the per-file subsection can ship a pointer without the mandatory read and fail structure lint or branch without the canonical table loaded.
- **Proposed resolution**: Add explicit numbered step 1 under the Round 2 **Plan revision authority** replacement: `1. **MANDATORY — READ ENTIRE FILE**: Read skills/design/references/settle-rc-dispatch.md completely.` then renumber the existing variant-pointer line as step 2, matching the `approval-gates.md` subsection in the same plan.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Round 4 fix still incomplete: both optional-trailer guards list only step 2 though plan claims explicit step 1 at both sites. Scenario: The `### UPDATED: skills/design/SKILL.md` block states "explicit numbered step 1 at **both** sites" but each guard subsection (Step 1e Gate A ~411, Step 3.5 Gate B ~714) lists only step 2. Failure modes and `test-design-structure.sh` require `MANDATORY — READ ENTIRE FILE` immediately before each branch directive. Pointer-only edits preserve four-way rc drift and break the planned harness assertions at both trailer guards.
- **Proposed resolution**: Under **Step 1e Gate A optional-trailer guard** and **Step 3.5 Gate B optional-trailer guard**, add numbered step 1: `1. **MANDATORY — READ ENTIRE FILE**: Read skills/design/references/settle-rc-dispatch.md completely.` Renumber the existing variant-row lines as step 2 at each site.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md
- **Concern**: The per-file UPDATE subsection claims numbered steps 1–2 mirroring approval-gates.md step 8 but enumerates only step 2; round-4 accepted fix remains incomplete.. Scenario: An implementer following only the discussion-rounds.md bullets adds a variant pointer without the exact step 1 MANDATORY — READ ENTIRE FILE line. Inline Branch on wrapper rc prose may remain or test-design-structure.sh mandatory-read-before-branch assertions fail.
- **Proposed resolution**: Add explicit numbered step 1 immediately before step 2: MANDATORY — READ ENTIRE FILE: Read skills/design/references/settle-rc-dispatch.md completely. Then step 2: apply the Gate A / discussion-round2 variant row before branching on wrapper exit status ($?).



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: The per-file UPDATE for both optional-trailer guards claims explicit numbered step 1 at each site but lists only step 2 under Gate A (~411) and Gate B (~714); round-4 accepted fix remains incomplete.. Scenario: An implementer following only the SKILL.md bullets can ship pointer-only edits at both guards, preserving four-way rc drift and failing the planned harness checks for mandatory read immediately before branch directives.
- **Proposed resolution**: Under each optional-trailer guard heading, add numbered step 1: MANDATORY — READ ENTIRE FILE: Read skills/design/references/settle-rc-dispatch.md completely. Keep step 2 as the Gate A or Gate B variant-pointer directive; remove all inline Branch on wrapper rc enumerations.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md
- **Concern**: The per-file UPDATE block still enumerates only numbered step 2 despite claiming steps 1–2 mirroring approval-gates.md step 8. Scenario: Round-4 accepted fix remains incomplete. An implementer following only the discussion-rounds subsection can add a variant pointer without the exact step 1 `MANDATORY — READ ENTIRE FILE` line that `scripts/test-design-structure.sh` will assert, leaving inline rc prose or failing structure lint while approval-gates.md is updated
- **Proposed resolution**: Add explicit numbered step 1 immediately before the existing step 2 in the discussion-rounds.md UPDATE subsection, matching approval-gates.md verbatim: `1. **MANDATORY — READ ENTIRE FILE**: Read skills/design/references/settle-rc-dispatch.md` completely.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: The per-file UPDATE block claims explicit numbered step 1 at both optional-trailer guards but lists only step 2 under Gate A and Gate B. Scenario: Round-4 accepted fix remains incomplete. The plan text at line 79 contradicts lines 81–85. An implementer can ship pointer-only edits at ~411 and ~714, preserving four-way rc drift and failing the harness mandatory-read-before-branch assertions at both SKILL.md guard sites
- **Proposed resolution**: Add explicit numbered step 1 under each guard heading before the existing step 2, mirroring approval-gates.md: `1. **MANDATORY — READ ENTIRE FILE**: Read skills/design/references/settle-rc-dispatch.md` completely; then step 2 applies the site-specific variant row before branching on wrapper exit status ($?).



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:119
- **Concern**: The prior accepted fix remains incomplete: the `discussion-rounds.md` plan subsection still enumerates only step 2, not explicit numbered step 1 with `MANDATORY — READ ENTIRE FILE`.. Scenario: An implementer can follow that subsection, add only the variant pointer, and leave the required read-before-branch contract absent or unparsable by `scripts/test-design-structure.sh`.
- **Proposed resolution**: Add numbered step 1 under the `discussion-rounds.md` subsection with the exact `MANDATORY — READ ENTIRE FILE` wording immediately before the existing step 2.



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:411,714
- **Concern**: The prior accepted fix remains incomplete: both `SKILL.md` optional-trailer guard bullets still list only step 2 and omit explicit numbered step 1 with `MANDATORY — READ ENTIRE FILE`.. Scenario: The Gate A and Gate B guard sites can retain pointer-only edits, leaving branch routing without the canonical snippet loaded and failing the planned immediate-read assertions.
- **Proposed resolution**: Add explicit numbered step 1 under both optional-trailer guard headings with the exact `MANDATORY — READ ENTIRE FILE` wording immediately before each variant-pointer step.



