### OOS_1: [OUT_OF_SCOPE] `closes_issue_main` repo slug validation gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `closes_issue_main` still forwards an explicit or resolved repo slug to `gh.extract_closes_issue_from_current_pr` without `_validate_repo_arg`; out of scope because the path is unchanged by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] missing regression tests for CLI contract fixes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers noted no regression tests lock the `checks_main` invalid-repo rejection and `create_branch_main` failure-path KV suppression contracts; this could allow future refactors to reintroduce either issue without CI coverage. Some sources marked this out of scope because tests were not part of the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] bash `gh-pr-checks.sh` repo-validation / exit-code parity gap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Python `pr checks` path now validates malformed `--repo` and exits 2, while `scripts/gh-pr-checks.sh` still passes the value to `gh` and exits with `gh`’s code; out of scope because the bash path is unchanged and the plan intentionally aligned Python PR verbs with each other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] `create_branch_main` stderr diagnostic parity gap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `create_branch_main` still does not emit bash-style stderr diagnostics on failure paths; out of scope because this is a pre-existing parity gap not introduced or worsened by this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


