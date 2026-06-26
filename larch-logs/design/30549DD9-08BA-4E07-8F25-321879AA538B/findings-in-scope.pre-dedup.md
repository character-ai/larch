### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-60
- **Concern**: [SCOPE-REDUCTION] Plan adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: Binding Mechanism authorizes only those two branch-only bodies (~28–39 every-run line savings). The third file plus lines 174–201 and 241–246 harness pins drive `diff_added: 198` / `diff_lines: 260`, expanding SKILL/matrix lazy-load surface without a completeness gate on the stated two-split scope.
- **Proposed resolution**: Drop the OOS-router split from this change. Keep `## OOS checkpoint router` inline in `ship-pr-exit-matrix.md` with only the mandatory-read pointer if needed; limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:51-53
- **Concern**: Plan omits updating the Step 18a.5 ownership forward after moving eligible filing prose to `step18a5-filing.md`.. Scenario: After the split, stall-recovery still directs readers to `step18-cleanup.md` § Step 18a.5 for the full escalation-success procedure, but that parent file becomes gate-only. Eligible-path implementers can skip Tier A/B filing steps.
- **Proposed resolution**: Add `### UPDATED: skills/implement/references/stall-recovery.md` to forward gate/skip predicates to `step18-cleanup.md` and eligible filing to `step18a5-filing.md`; update `scripts/test-implement-structure.sh` line 512 forward pin accordingly.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/step18-cleanup.md:5
- **Concern**: Plan does not revise the parent `**Contract**` header after moving escalation-success reporting into `step18a5-filing.md`.. Scenario: Line 5 still claims `step18-cleanup.md` owns escalation-success reporting while the plan makes it gate-only (lines 82–95). Load-contract drift misroutes maintainers and reviewers to the wrong authority surface.
- **Proposed resolution**: Revise the parent Contract to gate/skip/eligibility only; move reporting ownership to `step18a5-filing.md` Contract. Add a structure `forbid(step18-cleanup.md, 'escalation-success reporting', ...)` or equivalent if the phrase must not remain in the parent header.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:149-172
- **Concern**: Step 18a.5 harness section lists moved needles and parent `forbid` pins but omits explicit child-file `require` needles, unlike the OOS-router block at plan line 201.. Scenario: An implementer can retire parent fragments and pass parent forbids while `step18a5-filing.md` lacks key tokens (`compose-report --report-kind escalation-success`, Tier A `/larch:issue --input-file`, atomic env-write sentence). Structure lint may pass without verifying the child owns the moved body.
- **Proposed resolution**: Mirror the OOS-router pattern: add explicit `require(step18a5-filing.md, ...)` for every moved eligible-body needle listed at lines 151–169.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:27-31,102-117
- **Concern**: CI-fix forbid set is file-wide but the retained Exit 3 reason table uses the same tokens. Scenario: The planned forbids for `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, and `local-unfixable` will also match the still-inline Exit 3 reason routing table at lines 29-31. A correct split would false-fail lint, or the routing table would have to be removed even though the plan says to keep it inline.
- **Proposed resolution**: Scope the CI-fix forbids to the autonomous sub-procedure block only, or add a section-bounded check instead of file-wide substring forbids.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:56,74,90-100
- **Concern**: OOS-router forbid set is file-wide but it matches required every-run seeder and invariant text. Scenario: The planned forbids for `OOS_PENDING=false` and `steps_ran.step9a1=true` also hit the retained seed-initial-state contract at line 56 and the bail-time invariant at line 74. A correct implementation would false-fail the harness unless those every-run sections were removed, which the plan explicitly says not to do.
- **Proposed resolution**: Limit the OOS-router forbids to the router subsection, or anchor them on the `## OOS checkpoint router` block and not the file as a whole.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-61
- **Concern**: [SCOPE-REDUCTION] Plan still adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: The issue Mechanism authorizes only those two branch-only bodies (~28–39 line savings). The plan’s own `diff_added: 198` / `diff_lines: 260` is dominated by this third file plus a large OOS-router harness block (lines 174–201), expanding every-run SKILL/matrix edits without a completeness gate. Prior scope-reduction rejections on the same expansion still apply; the plan doubled down with more pins rather than dropping the split.
- **Proposed resolution**: Drop `ship-pr-oos-checkpoint-router.md` from scope. Keep the `## OOS checkpoint router` body inline in `ship-pr-exit-matrix.md` (or only a pointer without a third header loop). Limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md` per the binding Mechanism.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:149-172
- **Concern**: Step 18a.5 split adds parent `forbid(step18-cleanup.md, …)` needles but no matching child `require` loop in `step18a5-filing.md`.. Scenario: OOS router split explicitly adds child `require` needles (plan line 201); Step 18a.5 does not. An implementer can retire the heading, satisfy parent forbids, and ship an empty or header-only `step18a5-filing.md` while eligible filing prose remains missing from the lazy-load path.
- **Proposed resolution**: Mirror the OOS pattern: add a `forbid`/`require` pair so every moved eligible-body needle in the Step 18a.5 section is `require`d in `step18a5-filing.md` (not only forbidden in `step18-cleanup.md`).



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:228-229
- **Concern**: CI-fix parent `forbid` uses one-space numbered markers (` 1.` … ` 12.`) but the live subprocedure uses two-space list items (` 1.` … ` 12.` in `ship-pr-exit-matrix.md:106-117`).. Scenario: Partial moves can leave the full numbered 1–12 body inline while the heading and one-space tokens are stripped; structure lint and the retargeted first-fixer harness (which checks two-space steps) can disagree, letting duplicate CI-fix authority survive in the every-run matrix.
- **Proposed resolution**: Align parent `forbid` needles with the two-space ` {n}.` literals (or forbid both one- and two-space forms) so numbered steps cannot remain inline after the split.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:151-172
- **Concern**: Round-4 Step 18a.5 parent `forbid` expansion is still incomplete versus the eligible-path prose at `step18-cleanup.md:42-44`.. Scenario: Unlisted fragments such as `Tier A files through`, `after full-output secret redaction and exact-signature dedup`, and `after composing \`stall-recovery-chat-print.md\`` can stay inline after a partial move; structure lint passes while every-run `step18-cleanup.md` still owns filing authority.
- **Proposed resolution**: Add the remaining distinctive eligible-path sentences/phrases to the parent `forbid` list and to child `require` needles in `step18a5-filing.md`.



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:180-200
- **Concern**: Round-4 OOS-router parent `forbid` expansion is still incomplete versus `ship-pr-exit-matrix.md:90-100`.. Scenario: Phrases such as `with fallback counts only when ndjson is absent`, `leaves \`OOS_PENDING\` unchanged`, and `The checkpoint wrapper preserves non-empty child-written` are not forbidden; implementers can retire the heading and pinned tokens while substantive router sentences remain inline on every ship load.
- **Proposed resolution**: Extend parent `forbid` and child `require` lists to cover these remaining router sentences, not only success-bookkeeping fragments.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] OOS-router parent forbids still miss body text. Scenario: The planned `ship-pr-exit-matrix.md` split forbids the obvious router tokens, but it does not catch the remaining router prose such as `fallback counts only when ndjson is absent` or the stderr-preservation sentence. A partial edit can still leave the OOS checkpoint body inline in `ship-pr-exit-matrix.md:90-100`, so the every-run load and duplicate authority do not actually disappear.
- **Proposed resolution**: Extend the parent `forbid` set to cover the remaining router-only sentences, or move the whole section under a single child-reference guard so no router prose can survive inline.



### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] CI-fix parent forbids still leave repair steps inline. Scenario: The CI-fix split forbids routing tokens, but it still leaves uncovered body prose such as the minimal-repair, git-add, commit, and run-log-refresh steps in `ship-pr-exit-matrix.md:102-117`. That lets a partial move keep autonomous repair instructions inline, so the lazy-load split can pass while the every-run path still carries most of the CI-fix body.
- **Proposed resolution**: Broaden the parent `forbid` list to cover the remaining CI-fix body sentences, or gate the whole section with a single child-reference move check so no repair steps remain inline.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:151-172
- **Concern**: Step 18a.5 parent forbid needles overlap every-run stall gate and skip-predicate prose in step18-cleanup.md. Scenario: The harness forbid() helper uses substring `needle in text`. Planned forbids include ship-pr-state.sh, finalize-state.sh, session-env.sh, and record-failure marker, but those strings also appear in the every-run stall gate (line 13) and escalation-evidence skip list (line 38). A correct split that keeps gate text inline fails structure lint, or implementers delete required gate/skip prose to satisfy forbid.
- **Proposed resolution**: Scope parent forbids to the removed eligible-path paragraph only (for example forbid the full If eligible, Main Claude reads opener and filing-only sentences), or implement section-scoped forbid checks. Do not globally forbid ship-pr-state.sh / finalize-state.sh / session-env.sh / record-failure marker in step18-cleanup.md.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:207-219
- **Concern**: CI-fix parent forbid needles overlap every-run Exit 3 routing and handoff env in ship-pr-exit-matrix.md. Scenario: Planned forbid tokens first-fixer-non-health, ship-pr-internal-lint-fix, ci-local-unfixable, local-unfixable, and ledger_ready=true also appear in Exit 3 reason routing (line 30) and the handoff env paragraph (line 34), which the plan requires to stay inline. Substring forbids force either lint failure on a correct matrix or removal of required every-run routing text.
- **Proposed resolution**: Limit CI-fix parent forbids to the retired ## autonomous main-agent CI-fix sub-procedure section and stripped ci-fix branch-bullet repair prose. Drop Exit 3 routing tokens and ledger_ready=true from the global ship-pr-exit-matrix.md forbid list; keep those requires in the stay-inline loop.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:180-200
- **Concern**: OOS router parent forbid needles overlap every-run seeder, bail-time, and reship prose in ship-pr-exit-matrix.md. Scenario: Planned OOS forbids include OOS_PENDING=false, steps_ran.step9a1=true, NEXT_ACTION=reship, and best-effort stamps steps_ran.step9a1=false, but the same substrings live in the initial seeder contract (line 56), bail-time steps_ran invariant (lines 74-76), and the reship branch bullet (line 45). Global substring forbids conflict with keep every-run routing text inline.
- **Proposed resolution**: Restrict OOS parent forbids to the removed ## OOS checkpoint router body (heading forbid plus router-only distinctive sentences). Remove OOS_PENDING=false, steps_ran.step9a1=true/false, and NEXT_ACTION=reship from file-wide forbid; retain them in stay-inline requires where they belong outside the router section.



### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:241
- **Concern**: skills/implement/SKILL.md oos-pipeline require_near pin cannot enforce post-pipeline router placement. Scenario: Plan prose requires ship-pr-oos-checkpoint-router.md after the OOS pipeline and before the checkpoint fence, but require_near(SKILL.md, **`oos-pipeline`**, ship-pr-oos-checkpoint-router.md) uses a ±900-char window centered on the branch bullet. step-8-oos-checkpoint.sh sits roughly 1000+ chars later (intervening branch bullets plus OOS checkpoint fence header), outside that window. Lint either fails on correct placement or forces the router read adjacent to the oos-pipeline bullet before pipeline execution.
- **Proposed resolution**: Anchor oos-pipeline ordering on **`OOS checkpoint fence.**` or oos-pipeline.md with require_near before step-8-oos-checkpoint.sh (and optionally after oos-pipeline.md), not on the distant **`oos-pipeline`** skeleton bullet alone.



### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:808-815; scripts/test-implement-structure.sh:240-245
- **Concern**: ci-fix read pin can still be satisfied by the earlier oos-pipeline mandatory-read marker. Scenario: The planned ci-fix ordering checks search a 900-char window around the ci-fix bullet, but that window still contains the oos-pipeline `MANDATORY — READ ENTIRE FILE` line. If the new `ship-pr-ci-fix.md` read is missing or moved, the harness can false-pass and leave the old every-run CI-fix body inline.
- **Proposed resolution**: Use a ci-fix-local sentinel or a slice bounded to the ci-fix bullet itself, so only a marker adjacent to the new pointer can satisfy the check.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:149-172
- **Concern**: Step 18a.5 harness lacks explicit child-side require needles in step18a5-filing.md (unlike OOS router line 201). Scenario: An implementer can retire parent eligible-body phrases and satisfy parent forbid checks while step18a5-filing.md contains only headers; make test-implement-structure passes with an empty filing reference and eligible paths lose procedure authority
- **Proposed resolution**: Add matching require(step18a5-filing.md, ...) needles for every moved eligible-body token, mirroring the OOS-router child require block



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/step18-cleanup.md:42-44
- **Concern**: Step 18a.5 parent forbid list still omits distinctive eligible-path fragments (incomplete round-4 FINDING_1/4 fix). Scenario: Partial move can delete pinned needles yet leave Tier A files through and after full-output secret redaction and exact-signature dedup inline in step18-cleanup.md; every-run load keeps filing-body authority
- **Proposed resolution**: Extend forbid(step18-cleanup.md, ...) to cover Tier A files through, after full-output secret redaction and exact-signature dedup, and other surviving sentence fragments from lines 42-44



### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:46
- **Concern**: Plan omits forbid for legacy generic OOS router phrase in the oos-pipeline branch bullet (CI-fix legacy authority got explicit forbid; OOS did not). Scenario: Partial split can keep then run the OOS checkpoint router alongside the new ship-pr-oos-checkpoint-router.md mandatory read; every-run matrix retains duplicate router authority
- **Proposed resolution**: Add forbid(ship-pr-exit-matrix.md, 'run the OOS checkpoint router', ...) and require the branch bullet to name ship-pr-oos-checkpoint-router.md only



### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:909
- **Concern**: Plan omits structure forbid for legacy Step 18a.5 full-procedure pointer in SKILL.md (CI-fix legacy pointer gets explicit forbid at plan lines 232-234). Scenario: Partial implementation can keep Follow step18-cleanup.md for the escalation-success report procedure next to the new step18a5-filing.md read; eligible runs load gate-only cleanup and skip the conditional filing reference
- **Proposed resolution**: Add forbid(SKILL.md, 'Follow `step18-cleanup.md` for the escalation-success report procedure', ...) alongside the planned gate-only + step18a5-filing.md pointer



