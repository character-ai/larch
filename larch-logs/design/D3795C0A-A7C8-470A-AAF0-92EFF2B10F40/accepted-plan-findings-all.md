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




### FINDING_1: `resume_hint_for()` must short-circuit `submodule-restricted` before step-based routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `resume_hint_for()` only returns `none` early for `contract-failure|same-cause-repeat|unrecoverable`. Any other class at `STALL_STEP=2` hits `2) printf 'step2-impl\n'` before phase fallbacks. If `submodule-restricted` is added only as a late class arm (or left unspecified in the plan), Step-2 submodule stalls still emit `RESUME_HINT=step2-impl`, promising inline recovery Main Claude cannot perform because submodule edits are blocked by the hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: Merge `submodule-restricted` into the first `case "$class"` arm with `contract-failure|same-cause-repeat|unrecoverable` and `return 0`, before the `case "$step"` block. Keep harness `RESUME_HINT=none` assertions.
  - From Cursor-Pragmatic: Add `submodule-restricted` to the first `case "$class"` in `resume_hint_for()` (alongside `unrecoverable`), before the `case "$step"` block. Mirror `protected-path` precedence tests but assert `RESUME_HINT=none`.
  - From Cursor-Requirements: Insert submodule-restricted) printf 'none\n' ;; in the opening case "$class" block before case "$step" (same pattern as contract-failure|unrecoverable)


### FINDING_2: `stall-recovery.md` Step 18a first-detection warning omits `submodule-restricted`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 4 in `stall-recovery.md` authorizes only the protected-path first-detection warning (`.claude-plugin/plugin.json` / `protected-path-edit-required-out-of-scope`). If classification adds `submodule-restricted` elsewhere but this reference is not updated, Step 18a can classify submodule stalls without the submodule-specific “no inline recovery” warning. Operators may see generic stall text or the wrong protected-path message from the existing `FAILURE_CLASS=protected-path` branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend step 4 (and step 5 dispatch prose) in `stall-recovery.md` to authorize the submodule-restricted warning, state `RESUME_HINT=none` (no `step2-impl` dispatch or `record-escalation` for that path), and cross-reference the SKILL.md escalation branch so protected-path and submodule-restricted warnings stay distinct.


### FINDING_4: Step 2 coder-scout normalization uses plan-review reserved-slug filtering
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `normalize_coder_scout_manifest()` in `step2-implement.sh` calls `python/cli.py scout filter-manifest`, which routes through `filter_plan_manifest()` with `mode="plan-review"` hardcoded. That reserves review-mode slugs such as `arch` and `requirements` (`PLAN_RESERVED = REVIEW_RESERVED | {arch, edge, innovation, pragmatic, requirements}`). A coder scout sidecar containing those slugs is stripped at Step 2 before `dispatch-panel.sh` can preserve them for review-mode dynamic archetypes, so Item 6 (duplicate/divergent normalization) stays broken on the real `/implement` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Update normalize_coder_scout_manifest to call scout filter-manifest with --mode review, and adjust step2-implement.md plus test-step2-dispatch fixtures so review-mode slugs are preserved while still filtering slugs reserved in review mode



