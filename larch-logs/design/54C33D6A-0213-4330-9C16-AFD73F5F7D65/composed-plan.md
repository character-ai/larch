## Plan

## Approach

### UPDATED: skills/voter-calibration/scripts/voter-calibration.py
- Import `larch.core.proc` and `larch.git.gh`.
- Replace the final raw `gh issue view` argv with `gh.issue_view_field_read(proc, ...)`.
- Preserve the current JSON object validation and unavailable-boundary result.
- Delete the now-unused `_run_gh_json` helper.
- Keep issue listing, repository resolution, and `python/larch/` unchanged.

## Edge cases

- Preserve graceful handling for missing `gh`, nonzero results, empty output, malformed JSON, and non-object payloads.
- Preserve `closedAt_unavailable` when the issue payload lacks a usable timestamp.
- Do not invoke GitHub when repository resolution fails.

## Failure modes

- Avoid converting degraded boundary reporting into an uncaught exception.
- Pass the existing repository and field set unchanged.
- Use the shared read wrapper so transient failures receive its bounded retry policy.

## Testing strategy

- Run `make test-voter-calibration`.
- Confirm its fake GitHub cases still cover the requested fields, repository argument, missing executable, command failure, and missing `closedAt`.
- Run scoped pre-commit checks for `skills/voter-calibration/scripts/voter-calibration.py`.

Confidence: high

## Acceptance

- Run `make test-voter-calibration`.
- Confirm its fake GitHub cases still cover the requested fields, repository argument, missing executable, command failure, and missing `closedAt`.
- Run scoped pre-commit checks for `skills/voter-calibration/scripts/voter-calibration.py`.

Confidence: high

review_status: complete
rounds_completed: 1
difficulty: TRIVIAL
diff_added: 10
diff_deleted: 26
mechanical_churn: false
diff_lines: 36
