### OOS_1: [OUT_OF_SCOPE] correctness: skills/research/references/research-phase.md:194-206
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [latent] Pre-existing research sidecar snippet captures $? inside if ! command, so failures report exit 0. Token append-record or record-vendor-sidecar fails during research sidecar ingestion, but the operator warning says exit 0. Use the set +e, capture rc, set -e pattern added in validation-phase.md.
- **Suggested revision**: Address the concern above.


