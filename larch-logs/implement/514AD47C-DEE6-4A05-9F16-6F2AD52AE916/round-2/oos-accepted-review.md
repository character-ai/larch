### OOS_2: [OUT_OF_SCOPE] Anti-halt prose may misroute clear-stall success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Anti-halt prose at `skills/implement/SKILL.md:908` may imply clear-stall success should go to Step 18b instead of re-entering the pipeline. Pre-existing; orchestrator misread could tear down before recovery completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Clarify that clear-stall success re-enters Steps 2–15; only terminal failure proceeds to 18a.5/18b.


### OOS_3: [OUT_OF_SCOPE] Self-review lint terminal stall lacks ship-pr-state seeding prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Self-review lint terminal stall at `skills/implement/SKILL.md:592` skips to Step 18 without ship-pr-state seeding prose. Pre-existing; may leave Step 18a with thinner durable bail evidence than the stall branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse stall-branch seeding contract for self-review terminal stalls if classification gaps appear in production.


### OOS_4: [OUT_OF_SCOPE] Branch mixes unrelated changes with #5011 stall-ordering work
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Branch mixes unrelated #4994/#4965 changes with #5011 stall-ordering work. CI failures or regressions from voting/research_eval edits may be misattributed to the stall fix during review or bisect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Split or isolate #5011 from unrelated commits before merge when practical.


