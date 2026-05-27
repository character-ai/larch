### FINDING_1: [OUT_OF_SCOPE] Helper rc=2 fail-opens or is inconsistently specified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 0b proceeds on `lib-design-reentry-guard.sh` return code 2, so invalid input, an empty `HOME`, or a corrupted/badly bound PPID can bypass an existing marker. The prose, plan, and reference Bash contract also disagree on this behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Treat return 2 as refuse after ISSUE_NUMBER validation or add explicit re-validate before proceed.
  - From cursor-specialist-edge-cases-output.txt: Refuse or abort on return 2 when issue/ppid were bound from gh; only soft-fail for pre-binding errors.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan and reference bash with item 4, or remove item 4 to match plan-only miss/hit semantics.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


