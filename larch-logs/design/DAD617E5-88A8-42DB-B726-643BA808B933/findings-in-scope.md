### FINDING_1: Replace the legacy oos-4 rescue/merit prose in place
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The oos-4 update in `.claude/skills/combine-issues/SKILL.md:222-231` still reads like an add-on, so the old free-prose rescue prompt, confirm-all merit language, and after-any-rescue dedup prose can survive beside the new contract and contradict it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the oos-4 edit step, replace the whole Merit rejections require block and the After any rescue paragraph (224-231) with the new contract; delete bullets that conflict with zero-match keep-pending, multi-match re-confirmation, and confirmed-rescues-only dedup.
  - From Cursor-Pragmatic: In the oos-4 UPDATED steps, also replace the AskUserQuestion option with key-based rescue wording (e.g., rescue by stable key or #source/key) and drop "free prose."
  - From Cursor-Requirements: In oos-4, explicitly replace the approval prompt and the Merit rejections require an explicit merit batch outcome block (lines 222-231), not append beside it. Remove free-prose rescue wording. Align approval and dedup bullets with the new timing sections. State that legacy bullets must not remain.

### FINDING_2: Resolve rescue matches before merit confirmation
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Mixed rescue/approval replies can still be parsed in the wrong order, so zero-match or multi-match rescue text needs a rescue-first path before any merit confirmation; otherwise Apply all can reject keys the same message meant to rescue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the ### UPDATED checklist, require rewriting the approval AskUserQuestion at line 222 to rescue by stable keys only (e.g. A or #12/A), replace bullets at 226-227 so merit approval confirms only fully resolved non-rescued keys, and change line 231 to rerun dedup/grouping only after confirmed rescues.
  - From Cursor-Pragmatic: Add one merit-batch timing rule: in a single operator response, resolve rescue matching (and multi-match confirmation) before any merit-batch confirmation, including Apply all; exclude confirmed-rescued keys from rejection.

### FINDING_3: [OUT_OF_SCOPE] README catalog blurb still lags the merit gate
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The README `--oos` blurb still mentions actuality-only discard behavior and omits the merit gate, so the catalog will keep drifting from the updated skill description until a separate sync lands.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: [OUT_OF_SCOPE] Rejected-items display should show source keys on collisions
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: Showing bare keys in the `Rejected items (merit)` list can collide across sources; proactively showing `#source/key` would reduce ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: [OUT_OF_SCOPE] Frontmatter description still needs a char-budgeted draft
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The frontmatter `description:` follow-up can still use a candidate string with a char-budget note; the failure mode and lint commands are enough for implementation.
- **Suggested revisions (informational for voters; coder decides)**:
