### FINDING_2: Redundant create-pr retry branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/create-pr.sh:203-213` has identical then/else branches assigning `pr_json=$_WTR_OUT`, obscuring the intended wrapper contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: lib-net docs not updated with signature changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-net.md` was not updated after `is_transient_net_signature` changed, so contributors relying on the documented signature list may miss the new DNS/reset signatures and hosted-name exclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_4: Merge-pr S4 does not guard skipped text fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-merge-pr.sh` does not explicitly prove that text-format `gh pr checks` is skipped after JSON checks exhaust transient retries. A regression could re-enable the text fallback and still pass parts of the current harness, potentially allowing misleading check output to affect merge readiness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


