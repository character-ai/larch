## Goal
Implement issue #3645: [IMPLEMENTING] [BUG] claude_sub token-lane (#3637) review follow-ups: launcher + audit + tests\n\nFollow-up work items surfaced by the code review of the **Claude (subprocess) / `claude_sub` token-cost lane** work (issue #3637). The review panel accepted these as out-of-scope for that PR; they are combined here per the "combine related items into one issue" convention. Each item is independent — pick up individually..

## Implementation Plan
Follow-up work items surfaced by the code review of the **Claude (subprocess) / `claude_sub` token-cost lane** work (issue #3637). The review panel accepted these as out-of-scope for that PR; they are combined here per the "combine related items into one issue" convention. Each item is independent — pick up individually.

These do **not** affect the correctness of the `claude_sub` lane shipped in #3637 (the live cost report is fed by the direct `record-vendor claude_sub` ledger path, with a no-double-count regression test). They are hardening / audit-fidelity / additional-coverage follow-ups.

## Work items

1. **`scripts/launch-claude-ci.sh` exits 0 regardless of `LAUNCHER_EXIT` (pre-existing).** The CI launcher always exits `0`, so callers must parse the `LAUNCHER_EXIT=` line from stdout rather than relying on process exit status. Either align the process exit status with `LAUNCHER_EXIT`, or document the stdout-contract intent explicitly. Reviewer tagged this pre-existing.

2. **`scripts/append-token-record.sh` rewrites Claude CI token-records to `unknown` (pre-existing).** `launch-claude-ci.sh` writes `TOOL=claude` into `${OUTPUT}.token-record`, but `append-token-record.sh` (`case "$TOOL" in codex|cursor) ;; *) TOOL=unknown ;; esac`) only accepts `codex|cursor`, so the Claude CI sidecar is normalized to `unknown` in `token-report.ndjson`, weakening that NDJSON audit fallback. Add `claude` (and `claude_sub`) to the allowlist. Note: the live cost report is fed by the direct `record-vendor claude_sub` ledger path, **not** this sink (which currently has no consumer), so run totals are unaffected — this is audit-record fidelity only.

3. **`scripts/token-ledger.sh record-vendor` still permits a reserved `claude` vendor name (pre-existing).** `record-vendor` accepts arbitrary vendor names, including the literal `claude`, which would collide with the transcript-derived `claude` key in `token-report.sh`'s vendor-object merge and overwrite the main-agent totals. The #3637 design deliberately uses `claude_sub` to avoid this; add a guard that rejects (or warns on) a literal `claude` vendor write so the collision cannot be reintroduced by a future caller.

4. **Fourth-lane integration test coverage is incomplete (important).** Several end-to-end surfaces do not pin non-zero `claude_sub` behavior: `skills/implement/scripts/test-write-final-report.sh` (final-summary token sourcing + cost-line shape), `scripts/test-render-run-summary-callsites.sh` (claude_sub argv forwarding), `python/test_report_tokens_cost.py` (CLAUDE_SUB_COST KV parsing), and `python/test_report_tokens_scan.py` (claude_sub `_totals` / `_has_numeric_tokens` scan). Unit-level coverage exists (token-cost, token-report no-double-count, render-cost-line, python golden + cost pipeline); this is additional end-to-end hardening to lock the four-lane wiring.

5. **Per-bucket `claude_sub` cost-harness coverage is missing (important).** `scripts/test-token-cost-per-bucket.sh` pins per-bucket Claude/Codex/Cursor rate arithmetic and `LARCH_*_RATE_PER_M` env precedence but was not extended for `claude_sub`. Add per-bucket `--claude-sub-*` cases mirroring the Claude ones (priced at the Claude rate constants, resolved independently of `CLAUDE_BUCKET`) to pin the subprocess per-bucket arithmetic and env precedence.

6. **`scripts/launch-claude-ci.sh` CI-fixer prompt inlines the plan file without hardening (pre-existing).** The prompt embeds `$(cat "$PLAN_FILE")` directly, without symlink canonicalization or content redaction — a prompt-injection surface shared with the other CI launchers. Canonicalize/redact the plan content consistent with the untrusted-context handling used elsewhere (e.g. `launch-claude-subprocess.sh` context files).

## Excluded (false positive)

A 7th reviewer observation claimed `skills/report-tokens/SKILL.md` and `skills/shared/topology.tsv` still describe an "old three-lane" cost model. This was verified to be a false positive: `report-tokens/SKILL.md` documents the report-tokens skill (no cost-lane enumeration) and the `topology.tsv` Claude/Codex/Cursor rows are review/judge-panel counts, not cost lanes. There is nothing to update there, so it is intentionally not included.

## Test plan
(no test plan section in plan-file)
