### FINDING_2: parse_rate_retry_main still requires dropped VPR_ARGS flags
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan drops `--launch-mode` and `--retry-prefix-kind` from VPR_ARGS, but `parse_rate_retry_main` still requires them. After `scripts/dispatch-code-voters.sh` removes retry-only VPR_ARGS, classify-only calls exit with argparse error before printing NOT_SUBSTANTIVE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make launch-mode retry-prefix-kind and prompt-file optional no-ops in parse_rate_retry_main; keep accepting legacy argv; add pytest that dispatch-shaped argv without those flags exits 0 with bare NOT_SUBSTANTIVE


