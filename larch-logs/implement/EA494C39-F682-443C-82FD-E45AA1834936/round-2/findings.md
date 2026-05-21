### FINDING_1: code-quality: scripts/persist-implement-run-flags.md:7-9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Interface example still shows required --quick-mode while shell treats it optional and defaults false. Readers follow the .md contract and keep passing --quick-mode unnecessarily or think omission is invalid when the writer accepts omission. Update the fenced Interface block to show [--quick-mode] optional consistent with persist-implement-run-flags.sh header comments.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/compose-review-findings.sh;scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Substantive compose JSONL strict-scan and fixture changes bundled with unify-implement review-flow PR. Unrelated regressions or review churn block or distract from the Step 5 unification review. Split compose-review-findings changes into a separate PR or explicitly tie to the same tracked requirement.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/run-step5-review.sh:6504-6506
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stderr cap notice only for HARD round 1 though SIMPLE uses same base cap. Operators infer SIMPLE vs HARD differ at the launcher when only HARD prints the note. Emit the same notice for both paths or remove the asymmetric branch.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:7793-7795
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] a6 bans any substring ' --quick' in entire Step 5a awk window. Future legitimate prose like '/design --quick' inside Step 5a trips assert_not_contains even without forwarding /implement --quick. Scope the negative check to the implement invocation line or args template instead of whole block.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: git log merge-base..HEAD
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Branch mixes issue-anchored-plan doc bump larch-logs flush and unify-implement commits. Reviewers cannot treat diff as single-purpose without reading commit boundaries. Narrow PR scope or document stacked commits in PR body.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: .claude-plugin/plugin.json:11
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plugin description claims POST_PLAN SIMPLE/HARD gates /design depth alongside post-plan routing Operator expects SIMPLE post-plan label to imply lighter /design; SKILL forwards --design-classification HARD on the Skill /design path when externals exist Reword description to match skills/implement/SKILL.md: POST_PLAN_WORKFLOW_PATH for downstream routing; /design classification behavior documented separately
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:7793-7794
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] (a6) bans any ' --quick' substring in the whole Step 5a awk window Future prose inside ### 5a containing ' removed --quick' etc. fails CI despite no argv regression Anchor the negative check to the /implement invocation line or a stricter argv-local pattern
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/run-step5-review.sh:6504-6506
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] stderr cap notice only for HARD round 1 SIMPLE vs HARD now share cap/panel; operators only see the notice on one branch Print for both WORKFLOW_PATH values on round 1 or remove as redundant
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/compose-review-findings.sh:6255-6271
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Strict category extraction for plan-review accepted JSONL Downstream dashboards keyed on old human title in category mis-classify after upgrade Update consumers or document migration per compose-review-findings.md compatibility note
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/persist-implement-run-flags.md:6320-6323
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Interface example still shows required --quick-mode while script defaults when omitted Readers copy-paste an outdated required-arg shape Bracket [--quick-mode …] in the Interface block to match persist-implement-run-flags.sh
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: larch-logs/implement/** (diff bulk)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Large run-log fixture churn bundled with feature diff Obscures functional review for humans Treat as intentional per run-log policy; no action required for this review
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:300-345
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Default dynamic-archetypes cap raised to 6 is not asserted by the offline harness Regression reverting implement-tmpdir default to 4 could pass CI while contradicting SKILL and runtime contract Add a stub-capture case with no session-env cap and empty process env asserting DYNAMIC_ARCHETYPES=6 is passed to review-core
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/persist-implement-run-flags.md:7-10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Interface doc still shows required --quick-mode line though the script default makes it optional Operators copying usage from the .md may pass redundant flags or misunderstand optionality Update fenced usage to optional [--quick-mode] and document --no-issues alongside --workflow-path
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-implement-structure.sh:6778-6782
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Removed grep guard on Larch-log batches / quick-skip prose Larch-log batch guidance could drift without failing structure harness Add a new stable substring assertion for the unified Step 5 / batches contract
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .claude/settings.json:55-71 and .claude-plugin/plugin.json:57-71
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Strict permission allowlists no longer include deleted imaq/imq skills Strict-permission workspaces referencing removed skills break after plugin upgrade Document migration: remove /imaq / /imq invocations and refresh allowlists per release notes
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/run-step5-review.sh:6504-6506
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] HARD round-1 stderr breadcrumb has no harness assertion Message could be dropped accidentally with no CI signal Optionally assert stderr substring in test-run-step5-review HARD case
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/persist-implement-run-flags.md:8-9
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Interface block shows required --quick-mode but script makes it optional with default false Operators or maintainers follow stale signature and omit optional handling or add redundant flags Update fenced Interface to [ --quick-mode ] optional or note default false
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:132-133
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] assert_not_contains ' --quick' scans whole Step5a-5b awk window Future doc line like /design --quick inside window trips CI without forwarding bug Scope check to invocation template line or stricter token than bare space--quick
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/compress-skill/SKILL.md:10-65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] /compress-skill now delegates to /implement --merge --auto instead of the /imaq chain that used /implement --quick, pulling in full /design plus unified hard Step 5. Unattended or low-budget compress jobs that previously relied on the quick-implement envelope can time out, exhaust tokens, or fail in environments lacking SendMessage when /design subagent dispatch activates. Document the heavier pipeline in CHANGELOG and the skill (and steer operators to an explicit narrow path such as --design-only / --inline when that is the supported product intent).
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: CHANGELOG.md:12-14
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] 29.8.64 release notes omit delegator argv changes beyond Step 5. Operators upgrading from the changelog alone may not realize /alias scaffold, /create-skill, /compress-skill, and removed /imaq / /imq also moved off /implement --quick semantics. Add bullets naming those entry points and stating that former quick-implement shortcuts are removed except for /design --quick.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/persist-implement-run-flags.md:8-9
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Interface fenced usage still lists --quick-mode as a mandatory-looking flag while the shell treats it as optional with a false default. External scripts or humans mirroring only the .md may always pass --quick-mode or assume it controls behavior. Update the fenced block to bracket --quick-mode as optional and align wording with persist-implement-run-flags.sh.
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/run-step5-review.sh:167
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Informational stderr about the unified base round cap prints only for HARD workflow round 1, not for SIMPLE. Asymmetric logs make it harder to correlate SIMPLE vs HARD runs when debugging cap inflation from degraded rounds. Emit the breadcrumb for both SIMPLE and HARD (or whenever ROUND_NUM==1 regardless of path).
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] (a6) rejects any occurrence of space-prefixed --quick in the whole Step 5a awk window. Future legitimate prose that quotes a forbidden /implement --quick argv could false-fail CI. Scope the assertion to the args template line or a tighter pattern such as args:.*--quick instead of a global substring ban.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/fix-issue/SKILL.md:7628-7633
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] --inline/--hard prose claims /design only runs with --hard Operators following /fix-issue flags may wrongly believe default /implement skips /design unless --hard, conflicting with implement Step 1 default /design when externals exist Reword bullets to match implement Step 1: default /design path, both-externals exception, and that --hard pins HARD post-plan + pairs --inline forwarding
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/implement/SKILL.md:8366-8401
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5 unified banner text ordered after opening Bash before first run-step5-review Orchestrator following SKILL top-to-bottom may run token marks then run-step5-review before emitting the banner that prose says must print before first launcher call Move unified print immediately above first run-step5-review invocation or merge into preamble Bash
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: scripts/compose-review-findings.sh + scripts/test-compose-review-findings.sh (diff hunks ~6073-6750)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan fidelity: compose-review-findings category logic + fixtures changed without appearing in implementation plan file list PR reviewers cannot trace those behavioral changes to the stated unify-review-flow requirements Split unrelated JSONL/category work to its own PR or amend planning docs to explicitly own it
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:7709-7794
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan said remove a6 --quick invocation assertion; harness still has a6 with different semantics Traceability mismatch vs written plan Renumber/rename assertion and sync plan text with the stricter assert_not_contains rule
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/persist-implement-run-flags.sh:6341-6395
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Optional --quick-mode + QUICK_MODE key retained despite plan to remove quick control surface Legacy surface remains documented Remove flag/key in follow-up or document intentional retention in plan
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture: merge-base..HEAD commit list
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Branch bundles docs/issue-anchored-plan + version bump + larch-logs flush beyond narrow review-flow plan Wider PR than plan implies Prefer stacked PRs or single-scoped branch next time
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] architecture: skills/shared/subskill-invocation.md:8964-8972
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Pattern B example simplified while fix-issue Step 5a remains verbose Minor doc consistency risk Keep Pattern B example synchronized with fix-issue Step 5a canonical text
- **Suggested revision**: Address the concern above.

