# lint-codex-exec-auth.sh

Static guard for unwired `codex exec` call sites.

## Allowlist

Only these canonical paths are exempt from raw-dispatch scanning:
`scripts/launch-review.sh`, `scripts/launch-codex-ci.sh`,
`scripts/launch-codex-implement.sh`, `scripts/check-reviewers.sh`,
`scripts/launch-codex-exec.sh`, and
`skills/review-and-fix/scripts/review-and-fix.sh`.

## Pragma

`# lint-codex-exec-auth: ok <reason>` per line.

## Harness

`scripts/test-lint-codex-exec-auth.sh`
