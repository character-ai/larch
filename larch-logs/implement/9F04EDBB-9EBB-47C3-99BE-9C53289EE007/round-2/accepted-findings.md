### FINDING_1: code-quality: skills/implement/SKILL.md:1154-1158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 prose still claims launcher maps SIMPLE/HARD to public `--panel hard` and `review_panel=hard` Orchestrator prompt-side round-cap / banner math can diverge from real argv; contradicts NEVER #4 and run-step5-review.sh Rewrite to describe internal `--panel hard` only inside review-and-fix → review-core; launcher only forwards non-panel argv
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/implement/SKILL.md:243-263
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Exit 3 used for clarify-state ambiguous without posting clarify; exit-code table and /fix-issue text say exit 3 implies clarify posted Operator or wrapper assumes clarify thread exists after exit 3; ambiguous case exits 3 with no new request; /fix-issue message misleads Use distinct exit code for ambiguous vs audit-refused or update all prose (implement table fix-issue agnix-fix) to describe both sub-cases
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/fix-issue/SKILL.md:227-237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Missing <!-- larch:plan-missing --> marker and no harness pin per plan M Harder to detect plan-missing class in automation; plan-specified CI guard absent Add marker to mandated comment body and assert in test-fix-issue-bail-detection or step-order harness
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/fix-issue/SKILL.md:92-95
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale prose references /implement --issue for child adoption Orchestrator may pass removed flag and fail after locking Rewrite to positional issue tail only
- **Suggested revision**: Address the concern above.


### FINDING_13: code-quality: skills/implement/SKILL.md:1152-1160
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale Step 5 prose claims --panel hard on launcher path Maintainers mis-model argv and drift gate math Rewrite to internal review-core --panel hard only; align with NEVER bullet 4
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/fix-issue/SKILL.md:16128-16151
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] /fix-issue still documents --hard in argument-hint and flag prose despite operator scope to drop --hard once /implement is issue-only Operators and wrappers may keep passing a flag the project declared removed; docs disagree with the stated #2485 CLI contract Remove --hard from public /fix-issue argv/hint; keep COMPLEXITY triage internal-only without a --hard user flag; align harness/docs in the same PR
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/fix-issue/SKILL.md:108-246
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Plan probe runs after Step 0 lock Issue without plan still acquires IN PROGRESS lock before probe; diverges from probe-before-lock acceptance and increases avoidable locked-state churn Restructure so plan-block-read (or equivalent) runs before find-lock on PR path once intent is known
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: skills/fix-issue/SKILL.md:68-246
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-required plan probe before lock not implemented; Step 0 still locks first Missing-plan / malformed-plan issues still get IN PROGRESS and title churn before the probe; violates #2485 plan ordering and acceptance Restructure PR path: run plan-block-read (read-only) before find-lock; update step-order harness pins
- **Suggested revision**: Address the concern above.


### FINDING_22: architecture: skills/fix-issue/SKILL.md:227-246
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Plan probe remains after lock/setup/triage instead of before lock per agreed #2485 ordering Issue without plan still acquires IN PROGRESS and lifecycle title before probe; violates probe-before-mutate contract and increases stuck-title/comment recovery cost Move plan-block-read probe before find-lock-issue; update prose + test-fix-issue-step-order to enforce ordering vs Step 0 lock
- **Suggested revision**: Address the concern above.


### FINDING_24: code-quality: skills/fix-issue/SKILL.md:94
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stale prose still cites /implement --issue forwarding Umbrella path orchestrators may emit removed --issue argv and fail /fix-issue after lock Reword to positional issue tail; sweep remaining --issue references for /implement
- **Suggested revision**: Address the concern above.


### FINDING_26: code-quality: skills/implement/scripts/hook-stop-fail-close.sh:1-3
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Header still mentions post-/design halt though gate removed Misleading operator/debug narrative Update header to post-review + post-bump-version only
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/fix-issue/SKILL.md:16202-16264
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan probe is documented after Step 0 lock and Step 4 classify, not before find-lock-issue.sh as FINDING_6 required. Issues without a plan still acquire IN PROGRESS at Step 0; bail path relies on title restore and a new comment instead of skipping lock entirely, leaving a different failure/recovery surface than the plan. Move plan-block-read (and missing-plan comment) before find-lock-issue; renumber steps/registry; update anti-pattern #1 accordingly.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/fix-issue/SKILL.md:94
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Umbrella prose references removed `/implement --issue` argv Operators following umbrella docs invoke illegal flags or confuse positional contract Replace with positional issue tail wording
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/implement/SKILL.md:52-62 952 1111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER ladder skips #10 while Step 2 cites NEVER #10 Cross-references point at a non-existent ladder entry; undermines normative NEVER navigation Restore explicit NEVER #10 bullet or retarget all NEVER #10 citations to the correct surviving number
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: CHANGELOG.md:8-24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate `### Changed` headers under 35.0.0 Release notes harder to scan; mixes unrelated themes Merge/relabel sections or split entries across appropriate versions
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/scripts/hook-stop-fail-close.sh:1-5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header still mentions post-/design halt though gate removed Source readers mis-model hook responsibilities Update header to mention only remaining gates (review / bump)
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/fix-issue/SKILL.md:68-246
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan probe runs after find-lock; contradicts plan order plan-before-lock Lock plus [IN_PROGRESS] title applied before discovering missing/malformed plan; title restore can fail leaving misleading lifecycle state Move plan-block-read probe and plan-missing comment path before find-lock-issue.sh; update step-order harness accordingly
- **Suggested revision**: Address the concern above.


