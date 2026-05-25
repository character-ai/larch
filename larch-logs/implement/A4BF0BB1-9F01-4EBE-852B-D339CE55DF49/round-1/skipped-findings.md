### FINDING_3: Export contract for title eligibility constants is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The contract and acceptance text imply four exported constants, but only `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` is exported. Either the three bash regex constants should be exported too, or the documentation and acceptance language should be narrowed to sourced-only visibility plus the exported jq fragment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



