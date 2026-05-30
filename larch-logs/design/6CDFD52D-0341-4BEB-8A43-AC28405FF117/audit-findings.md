# lib-quiet `sanitize_diagnostic_line` passthrough audit (broad sweep, 2026-05-29, main 924345fba)

Swept all `larch_err` / `larch_errf` relays across `scripts/`, `skills/`, `hooks/`
(1329 `larch_err` + 71 `larch_errf` call sites). ~40 `<<'USAGE'` / `<<'EOF'`
heredoc relays are STATIC help text → low-risk, excluded. `sanitize_diagnostic_line`
already adopted by `ci-failed-jobs.sh`; defined at `lib-quiet.sh:86`.

## HIGH-RISK — external-content relays (route through sanitize_diagnostic_line)
- `scripts/ship-pr.sh:894-901` — `append_tool_failure_local` fallback relay of
  `$output_file` (captured tool / CI / vendor failure log). Already pipes
  `redact-secrets.sh`; add per-line `sanitize_diagnostic_line`. **[Item C]**
- `skills/review/scripts/collect-findings.sh:217-220` — relay of `$collector_log`
  (captured external reviewer / collector output). Already redact-secrets; add sanitize.
- `skills/review/scripts/collect-findings.sh:241-243` — relay of `$wait_log`
  (wait-for-reviewers stderr inside the external-reviewer path). Add sanitize.

## MEDIUM — internal-script stderr in reviewer/CI paths (route for defense-in-depth)
- `scripts/collect-agent-results.sh:311` — relay of `$WAIT_STDERR`
  (`wait-for-reviewers.sh` stderr). Internal script, adjacent to external-reviewer pipeline.
- `skills/review/scripts/review-core.sh:531-534` — relay of `$aggregate_stderr`
  (`aggregate-findings.sh` stderr). Internal; processes external findings.

## LOW-RISK — documented in lib-quiet.md, not routed
- `scripts/eval-research.sh:596` — `git show` stderr (dev/eval harness, not runtime surface).
- `skills/research/scripts/validate-citations.sh:692` — `__VC_DRY_RUN` test seam only.
- `scripts/generate-topology-docs.sh:135` — awk stderr over the committed internal `TOPOLOGY_TSV`.
- ~40 `print_usage` heredoc relays across scripts/ + skills/ — static text.

## Note
Each `.sh` edit requires its sibling `.md` update (script-md-siblings rule) and any
harness extension (`test-ship-pr.sh`, `test-collect-findings.sh`, `test-collect-agent-results.sh`).
The HIGH set is mandatory; MEDIUM included per the operator's "broad sweep" choice; LOW documented only.
