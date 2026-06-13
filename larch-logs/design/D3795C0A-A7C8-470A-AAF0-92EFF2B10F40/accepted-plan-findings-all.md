### FINDING_1: Item 1 submodule tests omit stale transient-evidence precedence fixtures
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Item 1 harness work for `submodule-edit-required-out-of-scope` in `skills/implement/scripts/test-stall-recovery-report.sh` risks repeating the protected-path regression unless it mirrors `case7k2`/`case7k3`. Without stale evidence such as `NOTE=network timeout` in the state-file fixture (and, per protected-path precedent, a matching argv-only case), `classify_from_evidence()` can match transient-infra grep on stale evidence before the early submodule bail arm runs. Protected-path already guards this with `case7k2` (state file + stale note) and `case7k3` (argv-only); submodule coverage should assert `FAILURE_CLASS=submodule-restricted`, `MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token`, and `RESUME_HINT=step2-impl`, not transient-infra retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the Item 1 harness with a state-file case mirroring case7k2: evidence `NOTE=network timeout`, bail `submodule-edit-required-out-of-scope`; assert `FAILURE_CLASS=submodule-restricted`, `MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token`, and `RESUME_HINT=step2-impl`
  - From Cursor-Innovation: Mirror case7k2: write_state with submodule-edit-required-out-of-scope plus transient phrase in evidence; assert submodule-restricted and submodule-restricted-bail-token beat stale transient output
  - From Cursor-Pragmatic: Mirror protected-path case7k2/case7k3: add a state-file case with NOTE=network timeout plus argv-only case; assert FAILURE_CLASS=submodule-restricted, MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token, and RESUME_HINT=step2-impl




### FINDING_1: Step 18a escalation prose lacks a distinct submodule-restricted warning branch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan extends protected-path repeat-warning semantics to `FAILURE_CLASS=submodule-restricted`, but `skills/implement/SKILL.md` line 838 hardcodes only the protected-path `.claude-plugin/plugin.json` warning for `FAILURE_CLASS=protected-path` with `RESUME_HINT=step2-impl`. There is no parallel branch for `submodule-restricted`. On submodule-edit-required-out-of-scope recovery, Step 18a can re-emit the wrong operator text (the plugin.json protected-path line instead of a submodule-specific message).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the escalation-recording bullet, add an explicit branch for FAILURE_CLASS=submodule-restricted that repeats the Step 2 submodule warning (**⚠ /implement: implementer bailed on submodule-restricted path; Main Claude will implement inline.**), not the protected-path plugin.json line.
  - From Cursor-Pragmatic, Cursor-Requirements: Spell out that FAILURE_CLASS=submodule-restricted must repeat the Step 2 submodule warning (implementer bailed on submodule-restricted path), not the plugin.json protected-path line.


### FINDING_3: Submodule-restricted classification mirrors protected-path step2-impl recovery despite Main Claude submodule write block
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: External implementers emit `submodule-edit-required-out-of-scope` when the plan needs submodule edits. The plan classifies `submodule-restricted` with `RESUME_HINT=step2-impl` like `protected-path`, but `hooks/hooks.json` runs `block-submodule-edit.sh` for Main Claude too. Inline Step 2 cannot land required submodule edits, so recovery stalls after a misleading operator warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: skills/implement/references/stall-recovery.md:43-44 Add a resume_hint_for carve-out mapping submodule-restricted to none (or document that step2-impl only applies when the plan can be satisfied without submodule writes) and align operator warning prose in skills/implement/SKILL.md with the hook constraint

---

**Merge notes**

- **FINDING_1** merges original inputs 1 and 4 (same Step 18a warning-text gap; reviewers differ only in wording).
- **FINDING_2** stays separate (plan accuracy / classifier precedence, not operator prose).
- **FINDING_3** stays separate (recovery routing / `RESUME_HINT`, not Step 18a repeat text alone). It overlaps FINDING_1 on “misleading warning” but needs a different fix (`resume_hint_for` / `stall-recovery.md`, not only SKILL.md line 838).



