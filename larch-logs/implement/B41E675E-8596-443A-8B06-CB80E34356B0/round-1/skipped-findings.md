### FINDING_3: Breadcrumb assertions no longer fail when breadcrumbs disappear
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Review-and-fix breadcrumb tests were weakened after the FD 3 harness change, so expected user-visible breadcrumbs can disappear on compose-fail, all-fail, and dispatch paths without failing the relevant lint shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.



