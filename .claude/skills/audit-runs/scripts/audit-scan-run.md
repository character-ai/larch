# .claude/skills/audit-runs/scripts/audit-scan-run.sh — contract

Runs all scans from `scans.tsv` against one run-log directory. Emits NDJSON (one compact JSON object per scan per line) to stdout.

## Output

One NDJSON line per scan, plus summary objects:

```json
{"scan":"exon-misclassification","pr":2476,"result":"pass","count":0}
{"scan":"oos-category-mangle","pr":2476,"result":"fail","count":12,"detail":"12 plan-review-phase rows with prose category"}
{"scan":"required-file-presence","pr":2476,"result":"fail","missing":["oos-issues.ndjson"]}
{"scan":"cache-freshness","pr":2476,"result":"fail","run_version":"29.8.54","current_version":"29.8.61","detail":"run plugin version behind current"}
{"scan":"changelog-rebase-conflicts","pr":2476,"result":"fail","count":2}
{"scan":"category-stats","pr":2476,"partial_data":false,"canonical":38,"blank":1,"mangled":12,"oos_blank":0,"rej_blank":1}
{"scan":"cross-cutting","pr":2476,"ended_at_null":true,"pr_number_null":true,"self_deploying_gap":false}
```

Missing `--run-dir` / missing `scans.tsv` path: emits a `required-file-presence` NDJSON line (`result:"error"`, `detail` explains the path problem) to stdout and exits non-zero (caller must not scan).

## Scans implemented

All scans in `scans.tsv`: `required-file-presence`, `exon-misclassification`, `oos-category-mangle`, `rej-category-blank`, `ns-retry-sidecars`, `codex-round1-adherence`, `codex-generalist-waste`, `execution-issues-categories`, `cache-freshness`, `changelog-rebase-conflicts`, `coder-tool`, `trailing-content-no-issues-found`. Plus synthetic `category-stats` and `cross-cutting` objects.

A `name` in `scans.tsv` with no matching `case` arm emits an `{"scan":"<name>","result":"error",...}` NDJSON line and exits non-zero (registry drift vs this script).

`category-stats` always emits. When `review-findings-full.jsonl` is missing, `partial_data` is `true` and numeric fields are zero placeholders (not “measured clean”).

Unrecognized CLI flags or arguments: prints a stderr diagnostic and exits non-zero (no NDJSON contract on that path).

## Edit-in-sync

When adding a scan to `scans.tsv`, add the corresponding `case` branch in this script and tests in `test-audit-runs.sh`.
