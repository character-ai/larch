# test-review-relevant-checks-helper.sh

Purpose: structural regression-test that `/review` Step 3e uses `scripts/run-relevant-checks-captured.sh` on the green path (not a Skill-tool invocation of the consumer checks flow).

The harness asserts exactly one helper call with `--site review-step3e --tmpdir "$REVIEW_TMPDIR"`, continuation prose after the fenced helper that advances to Step 3f on `RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true`, and failure-only log reading through `REDACTED_LOG_FILE` rather than raw `LOG_FILE`. It also rejects legacy Skill-tool prose that would route relevant checks through the Skill tool instead of the helper.

Primary callers: `make test-review-relevant-checks-helper` and `make test-harnesses`.

Edit in sync: update this harness with `skills/review/SKILL.md` and `scripts/run-relevant-checks-captured.md` when changing the Step 3e validation command, site label, or continuation wording.
