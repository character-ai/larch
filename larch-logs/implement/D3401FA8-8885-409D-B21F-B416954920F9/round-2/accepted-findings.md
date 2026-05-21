### FINDING_1: Last-N merged PR selection may omit recent merges
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `gh pr list --limit` plus post-sort does not guarantee “last N by `mergedAt`”; default ordering can return an arbitrary five merged PRs so a more recently merged PR can be omitted while the script implies true last-N semantics.
- **Suggested revision**: Use paginated GitHub API (merged to default branch), sort by `merged_at`, take last N; or an explicitly merge-sorted `gh` query—do not rely on default list order alone.


### FINDING_14: Unknown `scans.tsv` rows can silently produce no scan NDJSON (false “all green”)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-registry-cross-sync-output.txt
- **Concern**: `case "$scan_name"` without a default arm drops unknown scan names without a loud registry-drift signal.
- **Suggested revision**: Add `*)` handling: emit explicit error NDJSON and fail non-zero (or another operator-obvious signal), so TSV and driver cannot silently diverge.


### FINDING_16: Missing `review-findings-full.jsonl` can make category deltas look like true zeros
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Absent category stats can be interpreted as “clean” rather than “data missing,” understating cumulative blank/clean counters for PRs without jsonl.
- **Suggested revision**: Emit explicit skip/partial-data markers in category stats and teach [`audit-compute-counters.sh`](.claude/skills/audit-runs/scripts/audit-compute-counters.sh) to interpret them.


### FINDING_17: `ISSUE_LIST_FAILED` KV emitted on stderr vs documented stdout contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Orchestrators capturing stdout-only can miss structured failure KVs.
- **Suggested revision**: Emit contract KVs on stdout consistently (or update the contract doc everywhere it’s referenced).


### FINDING_23: `cumulative_counters` example in SKILL is out of sync with compute script + markdown schema
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Example documents keys the script does not emit/parse while omitting keys the script reads/writes—breaks the “populate frontmatter from script output” chain.
- **Suggested revision**: Make the example exhaustive relative to emitted/parsed KVs, or remove stale keys until implemented end-to-end.


### FINDING_24: SKILL claims adding a scan is “TSV row only, no SKILL edit” but wiring is multi-artifact
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Contradicts required updates in scan driver, optional counter aggregation, coordinated markdown, and tests.
- **Suggested revision**: Replace with an explicit checklist of all artifacts that must change when adding a scan.


### FINDING_26: No harness coverage for `changelog-rebase-conflicts` NDJSON / `CHANGELOG_*` counter path
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Docs call for coordinated tests, but the harness appears not to reference the new scan/counter wiring—registry can drift undetected.
- **Suggested revision**: Add hermetic fixtures asserting NDJSON shapes and counter summation with synthetic `scan-results` + prior frontmatter samples.

### FINDING_3: Pacific script can emit `Z` timestamps while SKILL forbids Z-only `audit_timestamp`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: When `TZ` tooling fails, the script may emit UTC `Z` timestamps while SKILL frontmatter rules disallow Z-only `audit_timestamp`, producing operator-facing contradiction.
- **Suggested revision**: Reconcile contract: either allow Z on documented fallback, or hard-fail preflight until a compliant Pacific ISO is available; align [`audit-pacific-timestamp.sh`](.claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh) and [`SKILL.md`](.claude/skills/audit-runs/SKILL.md).


### FINDING_6: Tests mirror production logic instead of exercising real script dispatch paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Harness duplicates regex/dispatch logic so production scripts can regress while tests still pass (notably verbal-form / resolve paths).
- **Suggested revision**: Run the real scripts under stubbed `gh`/`PATH` fixtures for forms and errors, or share a single canonical implementation invoked by both tests and runtime.


### FINDING_7: Codex “generalist waste” timing uses only first match / `head -1`, hiding multi-step >120s totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Multiple matching timing steps can each be sub-threshold while their sum exceeds the threshold; taking the first match only can under-report waste.
- **Suggested revision**: Aggregate consistently (e.g. sum or max across matches—pick the semantically correct aggregate) before threshold comparison.


