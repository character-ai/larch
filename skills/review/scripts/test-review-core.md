# test-review-core.sh Contract

Regression harness skeleton for `skills/review/scripts/review-core.sh`.

The harness stubs the one-round helper scripts through `REVIEW_CORE_*_SH` environment-variable seams, so it does not launch real reviewers. It covers:

- zero-findings exit
- aggregate-success zero-findings exit, including the voter-skip artifact path
- aggregate-success with missing `MERGED_COUNT` staying on the voter path instead of degrading to zero-findings
- all-findings-rejected convergence exit
- diff-mode `fix-required` signal
- both-down `PANEL_MODE` preservation
- description mode producing `ok` rather than a fix loop
- summary artifact and parent tmpdir copies when `SESSION_ENV_PATH` is set
- dirty-tree recovery summaries for clean, dirty, and unknown sidecars
- a set-but-empty `LARCH_DYNAMIC_ARCHETYPES_MAX` is ignored for the pre-parse default (cap `0`), so the round completes instead of failing validation

Run with `bash skills/review/scripts/test-review-core.sh` or `make test-review-core`.
