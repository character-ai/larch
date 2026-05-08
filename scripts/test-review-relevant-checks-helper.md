# test-review-relevant-checks-helper.sh

Purpose: structural regression-test that `/review` Step 3e uses `scripts/run-relevant-checks-captured.sh` instead of invoking the `/relevant-checks` Skill on the green path.

The harness asserts exactly one helper call with `--site review-step3e --tmpdir "$REVIEW_TMPDIR"`, nearby continuation prose that advances to Step 3f on `RELEVANT_CHECKS_OK=true`, and failure-only log reading through `REDACTED_LOG_FILE` rather than raw `LOG_FILE`. It also rejects legacy `/relevant-checks` Skill invocation prose.

Primary callers: `make test-review-relevant-checks-helper` and `make test-harnesses`.

Edit in sync: update this harness with `skills/review/SKILL.md` and `scripts/run-relevant-checks-captured.md` when changing the Step 3e validation command, site label, or continuation wording.
