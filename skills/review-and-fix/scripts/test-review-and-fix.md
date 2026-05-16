# test-review-and-fix.sh Contract

Regression harness for `skills/review-and-fix/scripts/review-and-fix.sh`.

It verifies standalone accepted-findings mode no-op behavior and Codex coder dispatch.

It also verifies `/implement` orchestrator mode selected by `--implement-tmpdir`: Codex success, Cursor fallback success, Claude-subagent fallback success, all-coder failure, post-dispatch submodule revert failure, no-finding exit `0`, wholesale-rejection exit `2`, summary JSON schema `2`, new coder/submodule fields, and OOS accumulation.

Run with `bash skills/review-and-fix/scripts/test-review-and-fix.sh` or `make test-review-and-fix`.
