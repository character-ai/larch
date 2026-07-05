### FINDING_1: Rescue matching must be key-only and ambiguity-safe
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-dyn-Prompt Contract Reviewer
- **Severity**: blocking
- **Concern**: The rescue prompt and matcher still let free-prose text drive rescue selection, so zero-match input can fall through without an explicit keep/pending default and multi-match input can stay ambiguous instead of forcing stable-key confirmation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make a zero-match rescue a no-op: keep all staged merit rejections pending, require explicit stable keys or cancel, and do not confirm any rejection from that text.
  - From Cursor-Innovation: Rewrite the line 222 Ask option to prefer stable display keys from the Rejected items (merit) list (e.g. rescue keys A, B). Mention free prose only as a fallback that triggers the new zero-match/multi-match confirmation rules.
  - From Cursor-Innovation: Add one bullet: rescue matching uses display keys only (accept #source/key when bare keys collide). Do not match item titles or description substrings. Zero or multiple key matches follow the plan default-keep and confirm-exact-keys paths.
  - From Cursor-dyn-Prompt Contract Reviewer: Require merit-pending only for multi-key ambiguity: matched items stay on the Rejected items (merit) list, are not rescued, and are not confirmed rejected until exact keys are confirmed; reserve default keep for zero-key rescue only


### FINDING_2: Merit approval must wait for fully resolved rescues
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The merit-batch outcome block still confirms or rejects items before rescue mapping is fully resolved, so rescued keys may never re-enter the kept set and unrescued items can still be treated as rejected too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the Files section, require rewriting the whole merit-batch outcome sub-list (lines 224-229) as one contract: batch approval confirms rejection only for keys neither rescued nor left pending from unresolved rescue matching; delete or replace the unrescued listed items are confirmed rejected unless the operator cancels bullet; state that merit batch cannot run while any multi-match rescue awaits key confirmation.
  - From Cursor-Innovation: Replace lines 226-227 together: merit rejections confirm only after rescue mapping is fully resolved; until then all unmatched and unrescued keys stay merit_pending and close-blocking. State that Apply all does not confirm merit rejections while any rescue text is zero-match or multi-match ambiguous.
  - From Cursor-Pragmatic: Preserve or restate in the new merit-batch bullets: confirmed rescued keys move from the staged rejection list to the kept-item set; merit batch approval rejects only merit items still listed after rescue resolution; cancel leaves all merit rejections pending.
  - From Cursor-Pragmatic: Add a bullet that merit batch approval runs only after rescue disambiguation is complete; until then all matched-but-unconfirmed items stay pending and their sources stay close-blocking; Apply all does not confirm rejections for ambiguous rescue matches.
  - From Cursor-Requirements: When superseding bullet 227, state explicitly: on an unambiguous unique-key rescue, apply the prior confirm-unrescued-rejections behavior; apply zero-key keep-all and multi-key re-confirm guards only when matching is ambiguous


### FINDING_3: Deduplication should rerun only after confirmed rescues
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The follow-up dedup/grouping step still runs after any rescue attempt, so a zero-key or multi-key rescue can refresh the rollup before the operator has confirmed the intended stable keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit SKILL.md edit: change line 231 to After confirmed rescues only, and drop the plan note that the current flow already requires confirmed rescues


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


