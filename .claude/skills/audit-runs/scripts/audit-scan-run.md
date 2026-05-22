# .claude/skills/audit-runs/scripts/audit-scan-run.sh — contract

Runs all scans from `scans.tsv` against one run-log directory. Emits NDJSON (one compact JSON object per scan per line) to stdout.

## Output

One NDJSON line per scan, plus summary objects:

```json
{"scan":"exon-misclassification","pr":2476,"result":"pass","count":0}
{"scan":"oos-category-mangle","pr":2476,"result":"fail","count":12,"detail":"12 plan-review accepted rows with prose category (not canonical)"}
{"scan":"required-file-presence","pr":2476,"result":"fail","missing":["run-statistics.md"]}
{"scan":"cache-freshness","pr":2476,"result":"informational","run_version":"29.8.54","current_version":"29.8.61","detail":"run plugin version behind current"}
{"scan":"changelog-rebase-conflicts","pr":2476,"result":"fail","count":2}
{"scan":"category-stats","pr":2476,"partial_data":false,"canonical":38,"blank":1,"mangled":12,"oos_blank":0,"rej_blank":1}
{"scan":"cross-cutting","pr":2476,"ended_at_null":true,"pr_number_null":true,"manifest_pr_number_mismatch_with_audited_pr":false,"self_deploying_gap":false}
{"scan":"cross-cutting","pr":2476,"ended_at_null":false,"pr_number_null":false,"manifest_pr_number_mismatch_with_audited_pr":false,"self_deploying_gap":false}
{"scan":"cross-cutting","pr":2476,"ended_at_null":false,"pr_number_null":false,"manifest_pr_number_mismatch_with_audited_pr":true,"self_deploying_gap":true}
```

The first `cross-cutting` line illustrates **legacy `manifest.json` (schema_version &lt; 2)** semantics: `ended_at_null` / `pr_number_null` mean the corresponding fields are **empty or JSON null** (treated as “missing” for dashboards). The second line illustrates a typical **flushed v2** manifest (`schema_version >= 2`) that **omits** `ended_at` and `pr_number`: `jq` `has("field")` is false, so both `*_null` flags are **`false`** even though the run is incomplete in a human sense — **do not** read v2 `false` as “field populated”; read it as “key absent or not null-shaped.” The third line is the same audited `--pr` but a manifest that records a **different** non-null `pr_number` (here vs the run under audit): `manifest_pr_number_mismatch_with_audited_pr` (and `self_deploying_gap`) flip to **`true`** when `pr_number` **exists**, is non-null / non-empty, and **differs** from the audited `--pr` argument.

Missing `--run-dir` (not a directory): emits a `run-dir-missing` NDJSON line (`incomplete: true`, `result:"error"`, `detail` explains the path) to stdout and exits non-zero — **do not treat stdout as a complete scan set** for aggregation.

Missing `scans.tsv` path: emits a `scans-registry` NDJSON line (`result:"error"`, `detail` explains the path problem) to stdout and exits non-zero.

Invalid `--pr` (non-decimal): emits an `audit-scan-run-args` NDJSON line (`result:"error"`) to stdout and exits non-zero.

## Scans implemented

All scans in `scans.tsv`: `required-file-presence`, `exon-misclassification`, `oos-category-mangle`, `rej-category-blank`, `ns-retry-sidecars`, `codex-round1-adherence`, `codex-generalist-waste`, `execution-issues-categories`, `cache-freshness`, `changelog-rebase-conflicts`, `coder-tool`, `trailing-content-no-issues-found`, `oos-silent-drop`. Plus synthetic `category-stats` and `cross-cutting` objects.

`required-file-presence` reads `docs/run-logs-required-files.tsv`-shaped rows: when the `condition` column is neither empty nor `always`, a missing file is ignored (informational) if `manifest.json` contains `"steps_ran": { "<condition>": false }` for that step key — committed runs that skipped Step 9a.1 may omit those batches without failing the scan. For `step9a1` specifically, direct TSV rows use that rule alone (default: enforce listed files unless `steps_ran.step9a1` is `false`). When `step9a1` is evaluated as part of the `step8` condition chain, the scan still uses the `run-statistics.md` / `oos-issues.ndjson` presence heuristic so `step8` does not widen from an empty run directory. The gate uses `jq -ne` (equivalently `jq -n -e`) so the boolean drives process exit status while stdin stays unused (TTY-safe in harnesses).

A `name` in `scans.tsv` with no matching `case` arm emits an `{"scan":"<name>","result":"error",...}` NDJSON line and exits non-zero (registry drift vs this script).

**`ns-retry-sidecars` reasons field**: the `ns-retry-sidecars` scan now includes a `reasons` object alongside `count` in its NDJSON output (e.g., `{“scan”:”ns-retry-sidecars”,”pr”:N,”result”:”fail”,”count”:3,”reasons”:{“NO_ISSUES_FOUND_TOO_THIN”:2,”UNKNOWN”:1}}`). Reasons are parsed from `NS_RETRY_REASON=` in each `*-ns-retry*.txt.meta` sidecar. Sidecars that lack a `NS_RETRY_REASON=` line (e.g., produced before this change landed) contribute an `UNKNOWN` count. The pass-result variant always emits `”reasons”:{}`. When `count` is positive but the histogram step cannot be built (e.g., `jq` failure), the line rolls up to `reasons:{“UNKNOWN”:<count>}` and may include `reasons_detail` explaining the fallback.

**`oos-silent-drop`**: compares non-security `### OOS_*` blocks counted from `oos-accepted-main-agent.md` / `oos-accepted-design.md` / `oos-accepted-review.md` (same awk as `oos-disposition-gate.sh`) against disposition evidence: union of GitHub issue URLs in `oos-issues.ndjson` and `oos-issues-created.md`, `Inline-triage rule` lines counted only from run-local `codex-commit-message.txt` or `session-transcript.jsonl` when either exists (otherwise inline triage is `0` — no ambient-repo `git log` fallback), and deduped `OOS_<n>` markers from rejected-OOS sections in `oos-issues.ndjson` (any NDJSON line that is not a JSON object or fails `jq` parsing yields `result:"error"` for this scan). NDJSON fields on pass/fail lines include `non_security_oos_blocks`, `issue_urls`, `inline_triage_hits`, and `rejected_oos_markers`; failure adds `detail`. `result:"skip"` when there are zero non-security OOS blocks in those accepted files.

`category-stats` always emits. When `review-findings-full.jsonl` is missing, `partial_data` is `true` and numeric fields are zero placeholders (not “measured clean”). When the file is present but the shared mangled-category jq program (`audit-scan-run-mangled-rows.jq`) cannot run successfully — including when `oos-category-mangle` already emitted `result:”error”` for a jq/parse failure on that JSONL — `partial_data` is `true`, `mangled` is a zero placeholder (not “measured clean”), and a `detail` string may be present; `canonical` / `oos_blank` / `rej_blank` may still reflect jq over the raw JSONL. When `oos-category-mangle` jq succeeds, `category-stats` reuses that single jq pass for `mangled` (no duplicate `jq -f` on the same file). The `mangled` count otherwise uses the same `plan-review` / `accepted` / non-canonical-category filter as the `oos-category-mangle` scan (not “any phase” prose categories).

**`oos-silent-drop`** (retroactive disposition heuristic over canonical `oos-accepted-{main-agent,design,review}.md`): counts non-security `### OOS_*` blocks (same awk contract as `scripts/oos-disposition-gate.sh`), then requires evidence that each block terminated with a filed GitHub issue URL (union of `oos-issues.ndjson` + `oos-issues-created.md`), sufficient `Inline-triage rule` breadcrumbs (prefers `session-transcript.jsonl` / `codex-commit-message.txt` under the run dir when present; otherwise falls back to a git log walk), or explicit rejected-OOS markers derived from `oos-issues.ndjson`. NDJSON fields (when not `skip`): `non_security_oos_blocks`, `issue_urls`, `inline_triage_hits`, `rejected_oos_markers`; `fail` lines may add `detail` (JSON string).

`cross-cutting` summarizes manifest integrity with **version-aware** rules (mirrors `audit-scan-run.sh` `jq`):

- **`schema_version` &lt; 2 (or non-numeric / absent — treated as v1-style):** `ended_at_null` is `true` when `ended_at` is empty after string coercion; `pr_number_null` is `true` when `pr_number` is JSON null or stringifies to empty. These flags match the older NDJSON “missing field” mental model.
- **`schema_version >= 2`:** `ended_at_null` is `true` only when the **`ended_at` key exists** and is JSON null or empty string (omitted key ⇒ `false`). Likewise `pr_number_null` is `true` only when the **`pr_number` key exists** and is JSON null (omitted key ⇒ `false`). Typical flushed v2 manifests omit both keys, yielding **`false`** / **`false`** for the two `*_null` booleans — **not** the same signal as v1 empties.
- **`manifest_pr_number_mismatch_with_audited_pr`:** `true` when `pr_number` is present, non-empty / non-null, and **not equal** to the audited `--pr` (use this to detect skew even when `pr_number_null` is `false` because the field is populated). **`self_deploying_gap`** duplicates that boolean for backward compatibility (prefer the explicit name in new consumers).

## Edit-in-sync

When adding a scan to `scans.tsv`, add the corresponding `case` branch in this script and tests in `test-audit-runs.sh`.
