### FINDING_3: Step 18a.5 harness lacks child-side `require` needles
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 18a.5 split plan adds parent `forbid(step18-cleanup.md, …)` needles but no matching `require(step18a5-filing.md, …)` loop, unlike the OOS-router block. An implementer can retire parent fragments and pass parent forbids while `step18a5-filing.md` lacks key moved-body tokens (`compose-report --report-kind escalation-success`, Tier A `/larch:issue --input-file`, atomic env-write sentence). Structure lint may pass with an empty or header-only child file and eligible paths lose procedure authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the OOS-router pattern: add explicit `require(step18a5-filing.md, ...)` for every moved eligible-body needle listed at lines 151–169.
  - From Cursor-Innovation: Mirror the OOS pattern: add a `forbid`/`require` pair so every moved eligible-body needle in the Step 18a.5 section is `require`d in `step18a5-filing.md` (not only forbidden in `step18-cleanup.md`).
  - From Cursor-Requirements: Add matching require(step18a5-filing.md, ...) needles for every moved eligible-body token, mirroring the OOS-router child require block


### FINDING_4: CI-fix parent `forbid` needles collide with every-run Exit 3 routing
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Planned file-wide CI-fix forbids for `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, `local-unfixable`, and `ledger_ready=true` also match the retained Exit 3 reason routing table (lines 29–31) and handoff env paragraph (line 34), which the plan requires to stay inline. Substring `forbid()` checks force either lint failure on a correct matrix or removal of required every-run routing text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Scope the CI-fix forbids to the autonomous sub-procedure block only, or add a section-bounded check instead of file-wide substring forbids.
  - From Cursor-Pragmatic: Limit CI-fix parent forbids to the retired ## autonomous main-agent CI-fix sub-procedure section and stripped ci-fix branch-bullet repair prose. Drop Exit 3 routing tokens and ledger_ready=true from the global ship-pr-exit-matrix.md forbid list; keep those requires in the stay-inline loop.


### FINDING_5: OOS-router parent `forbid` needles collide with every-run seeder and bail-time prose
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Planned file-wide OOS forbids for `OOS_PENDING=false`, `steps_ran.step9a1=true/false`, and `NEXT_ACTION=reship` also match the initial seeder contract (line 56), bail-time `steps_ran` invariant (lines 74–76), and the reship branch bullet (line 45). Global substring forbids conflict with the plan's requirement to keep every-run routing text inline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Limit the OOS-router forbids to the router subsection, or anchor them on the `## OOS checkpoint router` block and not the file as a whole.
  - From Cursor-Pragmatic: Restrict OOS parent forbids to the removed ## OOS checkpoint router body (heading forbid plus router-only distinctive sentences). Remove OOS_PENDING=false, steps_ran.step9a1=true/false, and NEXT_ACTION=reship from file-wide forbid; retain them in stay-inline requires where they belong outside the router section.


### FINDING_6: CI-fix parent `forbid` uses wrong numbered-list spacing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: CI-fix parent `forbid` uses one-space numbered markers (` 1.` … ` 12.`) but the live subprocedure uses two-space list items (`  1.` … `  12.` at lines 106–117). Partial moves can leave the full numbered 1–12 body inline while the heading and one-space tokens are stripped; structure lint and the retargeted first-fixer harness (which checks two-space steps) can disagree, letting duplicate CI-fix authority survive in the every-run matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align parent `forbid` needles with the two-space ` {n}.` literals (or forbid both one- and two-space forms) so numbered steps cannot remain inline after the split.


### FINDING_7: Step 18a.5 parent `forbid` list incomplete versus eligible-path prose
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Round-4 Step 18a.5 parent `forbid` expansion omits distinctive eligible-path fragments at `step18-cleanup.md:42–44` such as `Tier A files through`, `after full-output secret redaction and exact-signature dedup`, and `after composing \`stall-recovery-chat-print.md\``. Partial moves can delete pinned needles yet leave filing-body sentences inline; every-run `step18-cleanup.md` keeps filing authority while structure lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the remaining distinctive eligible-path sentences/phrases to the parent `forbid` list and to child `require` needles in `step18a5-filing.md`.
  - From Cursor-Requirements: Extend forbid(step18-cleanup.md, ...) to cover Tier A files through, after full-output secret redaction and exact-signature dedup, and other surviving sentence fragments from lines 42-44


### FINDING_8: OOS-router parent `forbid` list incomplete versus router body
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Round-4 OOS-router parent `forbid` expansion omits router sentences at `ship-pr-exit-matrix.md:90–100` such as `with fallback counts only when ndjson is absent`, `leaves \`OOS_PENDING\` unchanged`, and `The checkpoint wrapper preserves non-empty child-written`. Implementers can retire the heading and pinned tokens while substantive router sentences remain inline on every ship load.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend parent `forbid` and child `require` lists to cover these remaining router sentences, not only success-bookkeeping fragments.


### FINDING_9: Step 18a.5 parent `forbid` needles overlap every-run gate and skip predicates
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Planned Step 18a.5 parent forbids include `ship-pr-state.sh`, `finalize-state.sh`, `session-env.sh`, and `record-failure marker`, but those substrings also appear in the every-run stall gate (line 13) and escalation-evidence skip list (line 38). The harness `forbid()` helper uses substring `needle in text`. A correct split that keeps gate text inline fails structure lint, or implementers delete required gate/skip prose to satisfy forbid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Scope parent forbids to the removed eligible-path paragraph only (for example forbid the full If eligible, Main Claude reads opener and filing-only sentences), or implement section-scoped forbid checks. Do not globally forbid ship-pr-state.sh / finalize-state.sh / session-env.sh / record-failure marker in step18-cleanup.md.


### FINDING_10: `require_near` oos-pipeline pin cannot enforce post-pipeline router placement
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan prose requires `ship-pr-oos-checkpoint-router.md` after the OOS pipeline and before the checkpoint fence, but `require_near(SKILL.md, **`oos-pipeline`**, ship-pr-oos-checkpoint-router.md)` uses a ±900-char window centered on the branch bullet. `step-8-oos-checkpoint.sh` sits roughly 1000+ chars later (intervening branch bullets plus OOS checkpoint fence header), outside that window. Lint either fails on correct placement or forces the router read adjacent to the oos-pipeline bullet before pipeline execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Anchor oos-pipeline ordering on **`OOS checkpoint fence.**` or oos-pipeline.md with require_near before step-8-oos-checkpoint.sh (and optionally after oos-pipeline.md), not on the distant **`oos-pipeline`** skeleton bullet alone.


### FINDING_11: ci-fix read pin can false-pass via nearby oos-pipeline mandatory-read marker
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Planned ci-fix ordering checks search a 900-char window around the ci-fix bullet, but that window still contains the oos-pipeline `MANDATORY — READ ENTIRE FILE` line. If the new `ship-pr-ci-fix.md` read is missing or moved, the harness can false-pass and leave the old every-run CI-fix body inline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use a ci-fix-local sentinel or a slice bounded to the ci-fix bullet itself, so only a marker adjacent to the new pointer can satisfy the check.


### FINDING_12: Plan omits forbid for legacy generic OOS router phrase in branch bullet
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: CI-fix legacy authority gets an explicit forbid in the plan, but the OOS split does not forbid the legacy `run the OOS checkpoint router` phrase in the oos-pipeline branch bullet. Partial split can keep duplicate router authority inline in the every-run matrix alongside the new `ship-pr-oos-checkpoint-router.md` mandatory read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add forbid(ship-pr-exit-matrix.md, 'run the OOS checkpoint router', ...) and require the branch bullet to name ship-pr-oos-checkpoint-router.md only


### FINDING_13: Plan omits structure forbid for legacy Step 18a.5 full-procedure pointer in SKILL.md
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: CI-fix legacy pointer gets an explicit forbid at plan lines 232–234, but the plan omits a matching forbid for `Follow step18-cleanup.md for the escalation-success report procedure` at SKILL.md:909. Partial implementation can keep the old pointer next to the new `step18a5-filing.md` read; eligible runs load gate-only cleanup and skip the conditional filing reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add forbid(SKILL.md, 'Follow `step18-cleanup.md` for the escalation-success report procedure', ...) alongside the planned gate-only + step18a5-filing.md pointer


### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] OOS-router parent forbids still miss body text. Scenario: The planned `ship-pr-exit-matrix.md` split forbids the obvious router tokens, but it does not catch the remaining router prose such as `fallback counts only when ndjson is absent` or the stderr-preservation sentence. A partial edit can still leave the OOS checkpoint body inline in `ship-pr-exit-matrix.md:90-100`, so the every-run load and duplicate authority do not actually disappear.
- **Proposed resolution**: Extend the parent `forbid` set to cover the remaining router-only sentences, or move the whole section under a single child-reference guard so no router prose can survive inline.


### FINDING_17:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] CI-fix parent forbids still leave repair steps inline. Scenario: The CI-fix split forbids routing tokens, but it still leaves uncovered body prose such as the minimal-repair, git-add, commit, and run-log-refresh steps in `ship-pr-exit-matrix.md:102-117`. That lets a partial move keep autonomous repair instructions inline, so the lazy-load split can pass while the every-run path still carries most of the CI-fix body.
- **Proposed resolution**: Broaden the parent `forbid` list to cover the remaining CI-fix body sentences, or gate the whole section with a single child-reference move check so no repair steps remain inline.


