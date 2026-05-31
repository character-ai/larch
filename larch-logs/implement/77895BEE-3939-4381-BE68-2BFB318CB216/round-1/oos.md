### OOS_1: [OUT_OF_SCOPE] Consumer docs/external-reviewers.md still unconditional prompt
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Top-level `docs/external-reviewers.md` (~line 10) still says interactive runs always prompt when either tool is down. Operators reading consumer docs see old policy; not in branch diff. Runtime follows updated `skills/shared` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update docs/external-reviewers.md in a follow-up (not required by this plan’s file list).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Implement Continue label vs waterfall degradation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:455` Continue label says “reduced panel” though implement uses waterfall degradation. Pre-existing label/plan choice; not regressed by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider relabeling in a separate UX pass if confusing.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] relevant-checks does not map gate prose edits to harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` does not map SKILL/`external-reviewers` edits to `test-degraded-tools-gate`. Prose-only `BOTH_DOWN` regression may not run the gate harness on local pre-commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Map shared gate docs/skills to test-degraded-tools-gate or rely on full make lint in CI.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Case 1 optional BOTH_DOWN=false on healthy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: Case 1 (`DEGRADED=false`) does not assert `BOTH_DOWN=false` though the script emits it before early exit; low risk given Cases 2–4; not part of this branch’s plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional assert_contains BOTH_DOWN=false in Case 1.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] --skill accepts unvalidated SKILL_LABEL
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--skill` accepts unvalidated `SKILL_LABEL` in explanation text (display-only interpolation at lines 53, 129). Pre-existing; not changed by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate --skill against allowlist {design,implement,review,research} if hardening desired (separate change).


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] Per-skill interactive detection and Abort handling differences
- **Reviewer(s)**: dyn-cross-skill-consistency-output.txt
- **Severity**: nit
- **Concern**: Per-skill differences in interactive detection (`[[ -t 0 ]]` for `/research`, “non-subagent” for `/review`, plain “interactive” for `/design` and `/implement`) and Abort handling (`cleanup-tmpdir.sh` vs `STALL_TRACKING` + Step 18 for `/implement`) predate this branch and appear intentional; not regressions from `BOTH_DOWN` work.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Four SKILL callers largely aligned; minor implement AskUserQuestion wording
- **Reviewer(s)**: dyn-cross-skill-consistency-output.txt
- **Severity**: nit
- **Concern**: The four SKILL.md callers align on fail-safe prose, per-skill Continue labels match `external-reviewers.md:40`, and Cases 13–14 cover explanation last-line divergence. Minor formatting only: `/implement` uses `fire AskUserQuestion` (**Continue…**) without “with”, unlike the other three skills.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_8: [OUT_OF_SCOPE] No automated test of skill-side BOTH_DOWN parsing
- **Reviewer(s)**: dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: No automated test that skill orchestrators parse `BOTH_DOWN` and branch on `[[ "$BOTH_DOWN" == "false" ]]`; coverage is prose-only in shared doc and four SKILL gate bullets (acceptable per plan, not exercised by `test-degraded-tools-gate.sh`).


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_9: [OUT_OF_SCOPE] degraded-tools-gate.sh header comment drift (runtime OK)
- **Reviewer(s)**: dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: File header still says orchestrator always asks on `DEGRADED=true`; behavior is now split by `BOTH_DOWN` in callers — comment drift, not a runtime defect (overlaps in-scope FINDING_2 for files touched in-branch).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

