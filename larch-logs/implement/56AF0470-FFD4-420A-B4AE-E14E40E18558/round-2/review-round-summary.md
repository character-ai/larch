# Review Round 2

- Mode: `diff`
- 9 accepted, 12 rejected (12 exonerated)

## Accepted Findings

### FINDING_13: risk-integration: skills/implement/SKILL.md:464-468
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Dirty-tree recovery re-bootstrap is prose-only; structure lint guards the primary Step 0 bash block but not recovery re-entry with --resume-plan-tail. After IMPLEMENT_BAIL_REASON=dirty-tree the orchestrator may re-run bootstrap without --resume-plan-tail, duplicating snapshot/gh/persist or never completing branch/plan batches on the existing IMPLEMENT_TMPDIR. Add a fenced recovery bash block mirroring _ib_* args plus --resume-plan-tail; extend test-implement-structure.sh to require --resume-plan-tail in SKILL.md.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/SKILL.md:405-431
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No static test asserts _ib_kv_scan case arms for BRANCH_NAME BRANCH_ACTION PLAN_FILE. Dropping those case arms still passes test-implement-bootstrap while Step 2 and post-dispatch branch checks see empty BRANCH_NAME. Add grep or awk guards in test-implement-structure.sh for the three case arms in the Step 0 KV scan.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:602-608
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing harness for forked-target plan without --upstream-repo. Forked runs with unset UPSTREAM_REPO fail generically at gh-issue-view without a regression test locking exit 2 and helper short-circuit order. Add B-plan-forked-missing-upstream: expect STEP_FAILED=gh-issue-view exit 2 and no persist/create-branch in invoke log.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/implement-bootstrap.sh:270-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --resume-plan-tail silently allocates a new tmpdir when IMPLEMENT_TMPDIR is unset or session-env.sh is missing. Orchestrator re-runs bootstrap with --resume-plan-tail but without exporting IMPLEMENT_TMPDIR; script exits 0 with PLAN_FILE under a new empty tmpdir while plan.txt and feature-description.txt remain in the first-pass tmpdir. die_usage or exit 2 when RESUME_PLAN_TAIL=true and reuse preconditions fail; add harness asserting failure without IMPLEMENT_TMPDIR in env.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/implement-bootstrap.sh:172-176,587-589
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] snapshot-untracked.sh runs only inside phase_plan_materialize, which is skipped when REPO_UNAVAILABLE=true. On main, snapshot ran before the plan-materialization skip; repo-unavailable local runs no longer get untracked-baseline.z, so later phantom probes may treat pre-existing untracked files differently if the run progresses past Step 0 without plan files. Run snapshot after tracking (or at end of phase_infra) even when plan materialization is skipped; update GP-repo-unavail-plan to expect snapshot but not gh/persist.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Dirty-tree recovery prose omits exporting IMPLEMENT_TMPDIR before --resume-plan-tail bootstrap re-run. phase_infra cannot reuse session-env.sh; resume allocates a new tmpdir and plan/feature files from the dirty-tree pass are lost, so recovery appears to succeed in KV terms but Step 2 lacks materialized artifacts. Add explicit export IMPLEMENT_TMPDIR (and optional Bash snippet) to the recovery gate before the --resume-plan-tail call; align with implement-bootstrap.md caller contract.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/SKILL.md:637
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SKILL bootstrap table does not document that repo_unavailable skips all of Phase 3. Operators reading only SKILL.md may expect plan.txt or snapshot behavior that implement-bootstrap.md and tests intentionally omit. Add a table note that plan materialization (including snapshot) is skipped and PLAN_FILE remains empty.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree recovery lists bootstrap argv flags but omits required export of IMPLEMENT_TMPDIR documented in implement-bootstrap.md. First pass writes plan/feature files under session tmpdir A; recovery runs --resume-plan-tail without IMPLEMENT_TMPDIR in env; phase_infra allocates tmpdir B and resume skips copy/gh; tail uses empty feature file or waterfall blocks on missing artifacts. Add export IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" to step 468 and a fenced recovery bash block; mirror in implement-bootstrap.md cross-link.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/SKILL.md:464-468,684
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Recovery prose unsets IMPLEMENT_BAIL_REASON and re-runs bootstrap but does not require re-parsing resume bootstrap stdout like Step 2 redispatch does. Orchestrator keeps stale IMPLEMENT_BAIL_REASON=dirty-tree from first KV parse; L684 blocks implementer waterfall after successful resume that emitted BRANCH_NAME. Add fenced recovery bash that re-invokes bootstrap with --resume-plan-tail and re-runs the full _ib_kv_scan/export block on new stdout before continuing Step 0.
- **Suggested revision**: Address the concern above.


