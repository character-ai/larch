### OOS_1: [OUT_OF_SCOPE] Duplicate-code CI push-to-main trigger removed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/duplicate-code.yaml:13-20` — duplicate-code CI no longer runs on `push` to `main` (commit `842205e01`). Unrelated to #5095; not introduced or amplified by the consecutive-bash diff.
- **Suggested revisions (informational for voters; coder decides)**:


