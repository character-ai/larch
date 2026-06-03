### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: CI rebase no longer drops legacy bump/changelog commits before rebase
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: In-flight pre–Phase 1 branches that still carry bump commits may hit hotter conflicts after upgrade because `run_rebase_rebump` no longer drops legacy bump/changelog commits before rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Optional legacy drop-bump in `run_rebase_rebump` or operator guidance to drop bump commits before resume.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Legacy postbump checkpoint reader without Phase 1 writer increases review cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Postbump checkpoint writer was removed; reader and `force-push-gate` resume branch remain for legacy files only, inviting mistaken “we still checkpoint on conflict” assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate legacy resume into one documented helper or remove after compatibility window.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `run_bump_phase` / stall tokens still use “bump” naming after ship-only behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Phase and function names still say “bump” while behavior is ship/postbump-only; operators and logs read “version bump” though no bump runs; stall token still says `bump-branch-guard`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename phase/function in a follow-up or align stall tokens and breadcrumbs with ship terminology.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `python/rebase.py` `RebaseResult.new_version` always `None`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Public dataclass field `new_version` is always `None` after `rebase_and_rebump`; callers may assume it is populated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the field in a later Python cutover or document it as permanently unused in Phase 1+.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: SKILL prose implies Step 8b rebase is skipped while postbump still rebases
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: SKILL claims Step 8b is skipped, but internal postbump rebase remains; operators may misread stalls as “no rebase step” and skip manual rebase work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword to clarify internal postbump rebase remains.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Missing `scripts/test-ship-pr-rebase.md` harness contract sibling
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `scripts/test-ship-pr-rebase.md` sibling contract doc, unlike other `test-*` harnesses — minor doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add short `test-ship-pr-rebase.md` describing cases A-E


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Plan concurrency acceptance lacks automated regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance for concurrency has no automated regression test; per-PR bump hot-spots could reappear without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Keep manual acceptance in PR test plan or add a future integration harness


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Postbump Step 8b conflicts stall without conflict-resolution handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_step8b_rebase` / postbump 8b rebase lacks `--keep-on-conflict` and the conflict-resolution handoff that CI-fix rebase still gets via `ship_pr_pre_push`. A branch behind `main` with overlapping non-bump files can stall at `STALL_STEP=8b` while the same conflict during CI would auto-resolve (exit 4). Accepted for Phase 1 per SKILL, but operator recovery is weaker than the CI path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Wire postbump conflict handoff in a follow-up, or emit explicit manual-recovery breadcrumbs in `run_step8b_rebase` output.
  - From cursor-specialist-correctness-output.txt: Accepted for Phase 1 per SKILL.md:85; follow-up wire keep-on-conflict for postbump or amplify operator docs.
  - From cursor-specialist-edge-cases-output.txt: Document loudly in stall recovery or add keep-on-conflict plus `ship_pr_pre_push` handoff for postbump.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `test-ship-pr-rebase.sh` is grep-only with weak behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new harness is mostly structural greps plus one negative resume guard; it does not exercise a happy-path `run_rebase_rebump` flow. A refactor could break defer-push CI-fix rebase or phase14 resume without failing `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add sandbox tests with stubbed `rebase-push` and `git-force-push` for defer-push success and flag-gated resume success


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

