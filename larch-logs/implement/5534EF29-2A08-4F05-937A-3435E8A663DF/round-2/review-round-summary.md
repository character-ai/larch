# Review Round 2

- Mode: `diff`
- 16 accepted, 2 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: correctness: skills/implement/SKILL.md:459-464;scripts/implement-bootstrap.sh:592-605
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Dirty-tree recovery only re-runs the checkpoint but bootstrap returns before branch capture and plan logging. Operator restores a clean tree after STATUS=dirty; checkpoint passes but BRANCH_NAME stays empty and plan-goals/tally/summary never run; Step 2 or post-dispatch branch assertion fails. Document and implement resume of plan-materialize steps after dirty-tree (re-bootstrap tail or explicit helper blocks) plus a harness case.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:411-441
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Best-effort plan-log / tally / summary failures are untested. Changing a best-effort helper to fatal would pass harness but break live runs mid-Step-0. Add configurable stub exit codes and assert append-tool-failure plus continued flow.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.md:19-37
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness contract table omits several implemented Phase 3 cases. Reviewers and future editors miss GP-repo-unavail-plan, B13, B14, and related guards when assessing coverage. Sync test-implement-bootstrap.md case table with the shell harness.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:816-858
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] B5-plan-green does not assert workflow-path HARD or ledger marks. timing-ledger workflow-path HARD binding could regress without test failure. Assert timing-ledger mark and workflow-path HARD in invoke-log on green path.
- **Suggested revision**: Address the concern above.


### FINDING_13: security: skills/implement/SKILL.md:369-380
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] copy-plan exit-2 handler cats copy-plan.stderr.log without redaction while gh-issue-view stderr uses redact-secrets.sh A failed cp can print filesystem paths or tool errors into the operator transcript; asymmetric with hardened gh path in the same block Pipe copy-plan.stderr.log through redact-secrets.sh (and redact-tmpdir-paths.sh); on redactor failure print a generic message like gh-issue-view
- **Suggested revision**: Address the concern above.


### FINDING_14: security: scripts/implement-bootstrap.sh:647
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] goal_text redaction uses fail-open fallback to raw issue title If redact-secrets or redact-tmpdir-paths exits non-zero, attacker-controlled issue titles with tokens could reach plan-goals-test and committed larch-logs Fail closed with a placeholder goal string and append-tool-failure warning instead of goal_text=$goal_text_raw
- **Suggested revision**: Address the concern above.


### FINDING_15: architecture: skills/implement/SKILL.md:459-464 scripts/implement-bootstrap.sh:600-604
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dirty-tree recovery only re-runs check-mid-run-dirty-tree.sh but phase_plan_materialize returns before branch capture and plan logging. Operator cleans tree after IMPLEMENT_BAIL_REASON=dirty-tree; recovery passes re-check but BRANCH_NAME stays empty and plan-goals-test / plan-review-tally never run; Step 2 waterfall or dispatch fails branch guards. After clean re-check re-invoke implement-bootstrap.sh --up-to-phase plan or add a resume tail entrypoint; document in recovery gate and harness it.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/implement/SKILL.md:459-464
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Dirty-tree recovery only re-runs the checkpoint probe but bootstrap already returned before branch capture and plan batches. After operator cleans the tree and checkpoint is clean orchestrator continues with empty BRANCH_NAME and missing plan-goals-test/plan-review-tally/larch:plan summary. Add a post-dirty resume path in bootstrap or a documented re-invocation that runs phase_plan_materialize tail steps; add harness coverage for recovery continuation.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/implement/SKILL.md:463-464,679
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Recovery clears RECOVERY_REQUIRED but not IMPLEMENT_BAIL_REASON=dirty-tree while the waterfall blocks on that bail reason. Operator completes dirty-tree recovery but implementer waterfall guard still sees IMPLEMENT_BAIL_REASON=dirty-tree and refuses to proceed. Document and require unsetting IMPLEMENT_BAIL_REASON after a clean re-check before entering the waterfall.
- **Suggested revision**: Address the concern above.


### FINDING_19: architecture: skills/implement/scripts/test-implement-bootstrap.md:59-87
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness contract table omits B13 B14 B7 probe-failure and GP-repo-unavail-plan cases present in the shell harness. Contributors reading only the md file miss documented coverage for branch-create-fail and repo-unavailable plan skip. Add the missing case rows to the contract table.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/SKILL.md:463-464;skills/implement/SKILL.md:679
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Recovery gate never clears IMPLEMENT_BAIL_REASON=dirty-tree before continuing. After successful re-check orchestrator still has IMPLEMENT_BAIL_REASON=dirty-tree from KV parse and L679 blocks the implementer waterfall indefinitely. Add explicit unset of IMPLEMENT_BAIL_REASON after clean checkpoint and RECOVERY_REQUIRED=false.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/implement/scripts/test-implement-bootstrap.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness contract md missing new B13/B14/GP-repo-unavail-plan rows. Contributors relying on the md table miss coverage that exists only in the shell harness. Add the new case rows to test-implement-bootstrap.md.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/SKILL.md:459-464
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree recovery re-probes checkpoint only; collapsed bootstrap returns before branch create/capture and plan logging, and full bootstrap re-entry allocates a new SESSION_TMPDIR. After IMPLEMENT_BAIL_REASON=dirty-tree and a clean re-probe, orchestrator continues with empty BRANCH_NAME, missing plan batches, and step2-implement.sh main-branch-prohibited on main/master. Add a documented resume tail (bootstrap flag or helper) for post-checkpoint plan materialization; do not rely on a second full bootstrap without tmpdir continuity.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:463-464
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Recovery gate never clears IMPLEMENT_BAIL_REASON=dirty-tree while the implementer waterfall blocks on that bail. Even after RECOVERY_REQUIRED=false, exported IMPLEMENT_BAIL_REASON=dirty-tree prevents the Step 2 waterfall per L679. After clean re-probe, unset IMPLEMENT_BAIL_REASON and re-export before continuing; pair with the plan-materialization resume tail.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/implement/SKILL.md:459-464
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Dirty-tree recovery re-runs only the checkpoint, not remaining plan-materialization steps absorbed into bootstrap. After IMPLEMENT_BAIL_REASON=dirty-tree, operator cleans tree and passes re-check; orchestrator continues to Step 2 with empty BRANCH_NAME, no feature branch, and missing plan-goals-test / plan-review-tally / larch:plan upsert. Re-run implement-bootstrap --up-to-phase plan after clean re-check, or add bootstrap resume for post-checkpoint steps; add harness simulating dirty→clean→full materialization.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:1227-1265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness coverage for Phase 3 plan-materialization breadcrumbs. Breadcrumb regressions (missing lines, unconditional larch:plan posted) ship without offline detection. Add Edge-breadcrumb-count-plan-green and summary-fail cases with LARCH_QUIET_BREADCRUMBS=1 on --up-to-phase plan.
- **Suggested revision**: Address the concern above.


