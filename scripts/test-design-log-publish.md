# test-design-log-publish.sh

Regression harness for `scripts/design-log-publish.sh`. See
`scripts/design-log-publish.md` for the primary contract.

Coverage includes dry-run preflight, invalid args, trim/redact fail-closed
paths, PR create/list/view/merge recovery behavior, render-cache recursive
staging, suffix deny-list exclusions, and the strict `plan-review/` allowlist
for `round-<N>/findings-classification.tsv` (including unexpected-path and
symlink rejection).

Run via:

```bash
bash scripts/test-design-log-publish.sh
```

Or `make test-design-log-publish`.
