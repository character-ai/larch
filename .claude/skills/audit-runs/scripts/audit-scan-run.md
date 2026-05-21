# .claude/skills/audit-runs/scripts/audit-scan-run.sh — contract

Runs all scans from `scans.tsv` against one run-log directory. Emits NDJSON (one compact JSON object per scan per line) to stdout.

## Output

One NDJSON line per scan, plus summary objects:

```json
{"scan":"exon-misclassification","pr":2476,"result":"pass","count":0}
{"scan":"oos-category-mangle","pr":2476,"result":"fail","count":12,"detail":"12 plan-review-phase rows with prose category"}
{"scan":"required-file-presence","pr":2476,"result":"fail","missing":["oos-issues.ndjson"]}
{"scan":"cache-freshness","pr":2476,"result":"informational","run_version":"29.8.54","current_version":"29.8.61","detail":"run plugin version behind current"}
{"scan":"changelog-rebase-conflicts","pr":2476,"result":"fail","count":2}
{"scan":"category-stats","pr":2476,"partial_data":false,"canonical":38,"blank":1,"mangled":12,"oos_blank":0,"rej_blank":1}
{"scan":"cross-cutting","pr":2476,"ended_at_null":true,"pr_number_null":true,"manifest_pr_number_mismatch_with_audited_pr":false,"self_deploying_gap":false}
```

Missing `--run-dir` (not a directory): emits a `run-dir-missing` NDJSON line (`incomplete: true`, `result:"error"`, `detail` explains the path) to stdout and exits non-zero — **do not treat stdout as a complete scan set** for aggregation.

Missing `scans.tsv` path: emits a `scans-registry` NDJSON line (`result:"error"`, `detail` explains the path problem) to stdout and exits non-zero.

Invalid `--pr` (non-decimal): emits an `audit-scan-run-args` NDJSON line (`result:"error"`) to stdout and exits non-zero.

## Scans implemented

All scans in `scans.tsv`: `required-file-presence`, `exon-misclassification`, `oos-category-mangle`, `rej-category-blank`, `ns-retry-sidecars`, `codex-round1-adherence`, `codex-generalist-waste`, `execution-issues-categories`, `cache-freshness`, `changelog-rebase-conflicts`, `coder-tool`, `trailing-content-no-issues-found`. Plus synthetic `category-stats` and `cross-cutting` objects.

A `name` in `scans.tsv` with no matching `case` arm emits an `{"scan":"<name>","result":"error",...}` NDJSON line and exits non-zero (registry drift vs this script).

`category-stats` always emits. When `review-findings-full.jsonl` is missing, `partial_data` is `true` and numeric fields are zero placeholders (not “measured clean”).

`cross-cutting` summarizes manifest integrity: `ended_at_null` / `pr_number_null` flag empty `manifest.json` fields; **`manifest_pr_number_mismatch_with_audited_pr`** is `true` when `manifest.json`’s `pr_number` is present and differs from the audited `--pr` (run-log vs audited PR skew). **`self_deploying_gap`** duplicates that boolean for backward compatibility (same meaning as `manifest_pr_number_mismatch_with_audited_pr`; prefer the explicit name in new consumers).

## Edit-in-sync

When adding a scan to `scans.tsv`, add the corresponding `case` branch in this script and tests in `test-audit-runs.sh`.
