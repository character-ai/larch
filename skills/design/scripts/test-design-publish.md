# test-design-publish.sh

Offline harness for [`design-publish.sh`](design-publish.md). Stub `PATH` shims exercise argv, preconditions, plan-write failure, happy path, plan → upsert → rename → publish → marker ordering, exactly one `[DESIGNED]` rename call on the happy path, `SESSION_ID` empty, `PUBLISH_OK=false` after mutating, idempotent, and failed `[DESIGNED]` renames, unexpected publish, rename-failure warning detail, unknown rename-result handling, and render env binding.

Wired via `make test-design-publish` (see `Makefile`).

## Recent contract coverage

- Covers non-zero publish exits that also print `PUBLISH_OK=true` and empty-`SESSION_ID` `publish-skipped` rendering with rename/reentry marker skipped.
- Covers re-entry when `.design-publish-result.env` already has `PUBLISH_OK=true`:
  the wrapper still invokes `design-log-publish.sh` and preserves the earlier
  success metadata when the later publish attempt fails.
- Covers missing or empty `composed-plan.md`: exits `4` with validator-defect KVs and no publish-side effects. Stub logs are reset with the standard prelude before assertions.
- Covers `--skip-validate` with missing or empty `composed-plan.md`: exits `4` with the same validator-defect KVs, proving the precondition check runs before skip-validation logic.
- The `--skip-validate` missing-composed-plan regression uses isolated tmpdir `D_SKIP_MISSING` and fresh stub logs, not the skip-validate happy-path tmpdir.
