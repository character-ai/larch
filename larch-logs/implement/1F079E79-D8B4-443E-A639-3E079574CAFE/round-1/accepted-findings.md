### FINDING_10: correctness: scripts/render-run-summary.sh:131-134
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cost line omits spec’s ~ prefix Consumers/tests expecting TOTAL ~$X.XX from the issue spec see a mismatch Update cost_bullet formatting and assert in test-render-run-summary.sh
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/fix-issue/SKILL.md:359-365
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 6c writes OUTCOME from ${OUTCOME:-pr-open} without any in-skill definition of when the host sets OUTCOME after /implement. If OUTCOME is never assigned merged state defaults to pr-open even when the PR merged in-session misreporting the terminal summary and any downstream readers of final-report-state.sh. Bind OUTCOME to explicit parsed signals or scripted helpers derived from implement outputs or state files instead of an unset shell variable.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/fix-issue/SKILL.md:359-367
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OUTCOME defaults to pr-open when the shell variable is unset. A merged PR run can be labeled pr-open in the printed summary with no fix-issue upsert correction. Remove the default or derive outcome from /implement machine output.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/fix-issue/scripts/write-final-report.sh:95-177
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] bailed PR-path outcomes still run GitHub upsert after --print-stdout Step 5a bail sets bailed-implement-failed or bailed-adopted-issue-closed; script posts fix-issue final-summary marker on the tracking issue despite plan terminal-only bail and /implement owning that surface Add bailed-* to skip_upsert (or equivalent branch) so only terminal output runs; align SKILL if needed
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/fix-issue/scripts/write-final-report.sh:95-178
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] skip_upsert omits bailed-implement-failed and bailed-adopted-issue-closed Step 5a bail paths still upsert fix-issue:final-summary despite plan terminal-only (no GitHub post) requirement Extend skip_upsert (or branch) for both bailed outcomes and add harness coverage proving tracking-issue-summary.sh is not called
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/implement/SKILL.md:1853-1863
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 17 still instructs skipping ahead when DESIGN_ONLY_DONE=true before write-final-report.sh Design-only runs never invoke write-final-report; terminal summary + larch:final-summary upsert diverge from FINDING_4 single-call contract Remove the pre-guard so write-final-report.sh --print-stdout always runs before the token summary
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/implement/references/summary-comment-template.md:5412-5415
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc claims run-summary sentinel is first line of body; renderer starts with ## header and places sentinel before optional notes. Operators or parsers mis-locate the sentinel and couple wrong consumers. Fix wording to match render-run-summary.sh output order.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/implement/scripts/test-write-final-report.sh:1-86 skills/fix-issue/scripts/test-write-final-report.sh:1-37 scripts/test-render-run-summary.sh:1-49
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Test harnesses cover only a small slice of planned cases Missing mandated outcome matrices stream contracts N/A sweeps and fix-issue upsert assertions from implementation_plan Step 7 Implement the Step 7 checklist across the three harness files
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/implement/scripts/write-final-report.sh:86-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] BAIL_NEEDS_USER_INPUT is read but ignored in outcome logic. User-input bail paths look like generic bailed outcomes in the standardized block. Incorporate BAIL_USER into outcome or notes.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: agent-lint.toml near skills/fix-issue/scripts/test-*.sh excludes
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New fix-issue test harness is Makefile wired but not added to the same agent-lint exclude pattern as sibling fix-issue test scripts. agent-lint G004 may flag the harness as dead or misreferenced breaking lint on an otherwise green change. Add exclude entries and comments mirroring other skills/fix-issue/scripts/test-* harnesses plus sibling md.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: docs/linting.md:874-920
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New make targets not listed in harness inventory table. Contributors rely on docs/linting.md to discover harnesses; new tests are discoverable only via Makefile grep. Add rows for test-render-run-summary and test-fix-issue-write-final-report.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/test-implement-structure.sh:4219-4231
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Only Step 17 prose guard added; no Step 18 structural mirror for duplicated reminders and print-stdout. Step 18 could reintroduce branched reminder prose without CI catching it. Add Step 18 awk window similar to Step 17 per plan.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/test-render-run-summary.sh:4496-4543
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Shared renderer harness is a single golden path; missing N/A semantics and envelope assertions promised in plan. Renderer regressions for all-N/A costs or stdout/stderr mixing slip past lint. Add focused cases for all rates unset partial N/A and stderr STATUS OUTPUT_FILE pins.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/fix-issue/scripts/test-write-final-report.sh:1-37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fix-issue harness omits upsert/KV assertions and hides stderr Regression removing skip rules leaves CI green while behavior violates FINDING_3 Extend harness to assert stub tracking-issue-summary.sh not invoked and stderr STATUS/REASON for skip paths
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/fix-issue/scripts/test-write-final-report.sh:14-20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness redirects stderr to dev null hiding render or upsert diagnostics. Tests pass even when the helper emits STATUS failed on stderr only masking integration bugs. Preserve stderr in a tempfile and assert expected envelope lines for at least one scenario.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/fix-issue/scripts/test-write-final-report.sh:4985-5021
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fix-issue harness is two shallow substring checks; no upsert marker skip matrix or multi-outcome coverage. Wrong upsert marker skipped post for pr outcomes or broken no-tmpdir paths would not fail CI. Extend stub tracking-issue-summary.sh to record marker and argv add table tests for all eight outcomes and skip rules.
- **Suggested revision**: Address the concern above.


### FINDING_29: risk-integration: skills/fix-issue/scripts/write-final-report.sh:157-174
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] No digits-only validation of ISSUE before tracking-issue-summary upsert unlike implement write-final-report. Corrupted ISSUE_NUMBER yields avoidable gh failures or inconsistent handling vs the implement skill’s fail-fast contract. Mirror implement’s case guard for ISSUE before building args and calling tracking-issue-summary.sh.
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: skills/implement/SKILL.md:1853-1867
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stale Step 17 prose says design-only runs should continue straight to the token summary while the script block mandates write-final-report first; the fenced call lacks || true so upsert mkdir failures exit non-zero despite prose saying log and continue. Orchestrator may skip the rich summary on design-only or halt Step 17 before the token summary when write-final-report fails. Rewrite/remove the misleading line; wrap Step 17 write-final-report like Step 18 with || true and explicit failure logging.
- **Suggested revision**: Address the concern above.


### FINDING_31: risk-integration: skills/implement/scripts/test-write-final-report.sh:5428-5520
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Implement test harness falls far short of plan-required coverage (8 outcomes print-stdout N/A notes stalled MERGE_RESULT matrix). Regression in write-final-report outcome logic quiet routing or note migration ships undetected despite make lint green on shallow cases. Add fixture-driven cases per plan Step 7 for implement write-final-report.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/SKILL.md:1853-1862
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale Step 17 line says DESIGN_ONLY_DONE runs should continue to the token summary before the mandatory write-final-report call, contradicting unconditional summary and the plan’s removal of DESIGN_ONLY_ONLY pre-guards. An orchestrator that treats SKILL steps literally may skip write-final-report on design-only runs and never print or upsert the standardized block before Step 17’s token summary. Delete or rewrite the sentence so it cannot be read as bypassing write-final-report.sh; align prose with unconditional invocation.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: skills/implement/references/summary-comment-template.md:14-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc states the run-summary sentinel is the first line of the body but render-run-summary emits it as the last line after bullets. Operators editing comments may search for the wrong anchor or misunderstand ordering when debugging upserts. Fix documentation to say trailing sentinel or final line not first line.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: skills/implement/scripts/test-write-final-report.sh; skills/fix-issue/scripts/test-write-final-report.sh; scripts/test-render-run-summary.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Regression harnesses are far thinner than the implementation_plan matrix for outcomes print-stdout parity N/A fields cost branches and fix-issue upsert behavior. Regressions in outcome mapping marker tails or print-stdout contracts can ship without CI catching them undermining the whole standardization goal. Expand tests per the agreed plan or revise the plan to the smaller enforced surface.
- **Suggested revision**: Address the concern above.


