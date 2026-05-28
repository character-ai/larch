### FINDING_1: Finalize Plan Review conflicts with multi-round auto-apply
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Finalize Plan Review still says Step 3 never applies findings and must not revise `plan.txt`, while the multi-round loop and approval-gates guidance document in-loop auto-apply behavior. Operators following only Finalize may skip or duplicate `revise-plan-with-waterfall` behavior or mishandle Gate B after convergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Invalid loop env-var docs omit Step 3b branch behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Loop env-var docs state invalid argv values exit 2, but omit the plan edge-case that Step 3 short-circuits to Step 3b through `panel-failed` handling without Gate B. Operators reading only `flags.md` or `configuration-and-permissions.md` may not know where `/design` lands after argv failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

