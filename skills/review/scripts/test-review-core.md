# test-review-core.sh Contract

Regression harness skeleton for `skills/review/scripts/review-core.sh`.

The harness stubs the one-round helper scripts through `REVIEW_CORE_*_SH` environment-variable seams, so it does not launch real reviewers. It covers:

- zero-findings exit
- wholesale-rejection exit
- diff-mode `fix-required` signal
- both-down `PANEL_MODE` preservation
- description mode producing `ok` rather than a fix loop
- summary artifact and parent tmpdir copies when `SESSION_ENV_PATH` is set
- dirty-tree recovery summaries for clean, dirty, and unknown sidecars

Run with `bash skills/review/scripts/test-review-core.sh` or `make test-review-core`.
