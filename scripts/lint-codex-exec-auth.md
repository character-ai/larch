# lint-codex-exec-auth.sh

Static guard for unwired `codex exec` call sites.

## Allowlist (basename)

`launch-review.sh`, `launch-codex-ci.sh`, `launch-codex-implement.sh`, `check-reviewers.sh`, `review-and-fix.sh`, `launch-codex-exec.sh`

## Pragma

`# lint-codex-exec-auth: ok <reason>` per line.

## Harness

`scripts/test-lint-codex-exec-auth.sh`
