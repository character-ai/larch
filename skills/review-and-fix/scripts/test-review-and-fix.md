# test-review-and-fix.sh Contract

Regression harness for `skills/review-and-fix/scripts/review-and-fix.sh`.

It verifies the no-findings status, accepted finding ID enumeration, `FIX_COUNT`, and per-finding structured fixer env files for the existing fixer-enumeration mode.

It also verifies `/implement` orchestrator mode selected by `--implement-tmpdir`: accepted-fix exit `3`, no-finding exit `0`, wholesale-rejection exit `2`, summary JSON creation, fixer env generation, and OOS accumulation.

Run with `bash skills/review-and-fix/scripts/test-review-and-fix.sh` or `make test-review-and-fix`.
