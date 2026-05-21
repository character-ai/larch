The caller asked for **only** the structured finding list (no `CreatePlan`, no file reads — aggregating the supplied inputs).

### FINDING_1: Last-N merged PR selection may omit recent merges
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `gh pr list --limit` plus post-sort does not guarantee “last N by `mergedAt`”; default ordering can return an arbitrary five merged PRs so a more recently merged PR can be omitted while the script implies true last-N semantics.
- **Suggested revision**: Use paginated GitHub API (merged to default branch), sort by `merged_at`, take last N; or an explicitly merge-sorted `gh` query—do not rely on default list order alone.

### FINDING_2: Manual Pacific timestamp fallback is not faithful LA time (date/hour/DST)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Hybrid UTC calendar date with offset-shifted hour is not true `America/Los_Angeles`; DST/header claims can contradict behavior; near UTC midnight the labeled Pacific calendar date can be wrong (e.g. Zulu late evening still “next calendar day” in LA).
- **Suggested revision**: Drop the manual hybrid; use `TZ=America/Los_Angeles` end-to-end for the Pacific path, or document and implement a fully honest UTC fallback without labeling it as Pacific.

### FINDING_3: Pacific script can emit `Z` timestamps while SKILL forbids Z-only `audit_timestamp`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: When `TZ` tooling fails, the script may emit UTC `Z` timestamps while SKILL frontmatter rules disallow Z-only `audit_timestamp`, producing operator-facing contradiction.
- **Suggested revision**: Reconcile contract: either allow Z on documented fallback, or hard-fail preflight until a compliant Pacific ISO is available; align [`audit-pacific-timestamp.sh`](.claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh) and [`SKILL.md`](.claude/skills/audit-runs/SKILL.md).

### FINDING_4: `since` ISO detector is case-sensitive on `since` / `Z` forms
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Dispatch regex for since-ISO may reject otherwise-valid inputs due to case (e.g. `Since` vs `since`, or `Z` casing), misrouting forms as unrecognized.
- **Suggested revision**: Normalize case (or broaden patterns) before regex dispatch.

### FINDING_5: Multi-line TSV captured in a shell variable risks broken per-PR scanning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Unquoted expansion can merge rows/lines and break line-oriented scanning of run maps.
- **Suggested revision**: Prefer file-based maps or mandate safe iteration (quoted fields, process substitution, explicit record delimiter), and document consumption rules in [`SKILL.md`](.claude/skills/audit-runs/SKILL.md).

### FINDING_6: Tests mirror production logic instead of exercising real script dispatch paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Harness duplicates regex/dispatch logic so production scripts can regress while tests still pass (notably verbal-form / resolve paths).
- **Suggested revision**: Run the real scripts under stubbed `gh`/`PATH` fixtures for forms and errors, or share a single canonical implementation invoked by both tests and runtime.

### FINDING_7: Codex “generalist waste” timing uses only first match / `head -1`, hiding multi-step >120s totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Multiple matching timing steps can each be sub-threshold while their sum exceeds the threshold; taking the first match only can under-report waste.
- **Suggested revision**: Aggregate consistently (e.g. sum or max across matches—pick the semantically correct aggregate) before threshold comparison.

### FINDING_8: Preflight GitHub identity check: asymmetric URL normalization and misleading diagnostics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Remote URL normalization vs `gh` URL parsing can disagree (e.g. `.git` suffix / API-ish shapes), causing false mismatches or confusing `REASON` text (including mismatched “expected” labeling relative to what was compared).
- **Suggested revision**: Normalize both sides with one function; print both parsed identities and the normalized comparisons used in the decision.

### FINDING_9: Missing run-dir error `scan` id wording may disagree across script, markdown, and plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Downstream consumers keying on specific error object ids may miss events if `scan` identifiers differ between implementation and docs.
- **Suggested revision**: Align `scan` / error ids across [`audit-scan-run.sh`](.claude/skills/audit-runs/scripts/audit-scan-run.sh), [`audit-scan-run.md`](.claude/skills/audit-runs/scripts/audit-scan-run.md), and operator plans.

### FINDING_10: Unvalidated `NEW_ISSUE` interpolated into double-quoted `gh --body`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Non-numeric or shell-metacharacter-bearing values can alter parsing (quotes/command substitution) before `gh`, changing close/comment behavior.
- **Suggested revision**: Validate issue numbers as `^[0-9]+$`; build body with `printf` and pass `gh --body-file`.

### FINDING_11: KV stdout format allows embedded newlines / fake `KEY=` lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Downstream `sed`/`grep`/line parsers can mis-bind `PR_LIST`/`ERROR` to continuation lines, mis-scoping audits or hiding errors.
- **Suggested revision**: Emit machine-safe payloads (JSON/base64), or strictly sanitize (strip newlines, restrict `=` in values) and document a strict parsing contract.

### FINDING_12: TSV `rel_path` joined into `RUN_DIR` without `..` / absolute containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malicious or mistaken `../../../` style paths can cause reads outside the intended run directory tree.
- **Suggested revision**: Reject `..` and absolutes; optionally require resolved paths stay under `RUN_DIR`.

### FINDING_13: Preflight failure output may print raw git/gh URLs (credential leakage / hostname exposure)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Identity parse failures can echo clone URLs containing userinfo or sensitive hostnames to operator-visible output.
- **Suggested revision**: Redact userinfo by default; print normalized owner/repo unless verbose/debug explicitly enables full URLs.

### FINDING_14: Unknown `scans.tsv` rows can silently produce no scan NDJSON (false “all green”)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-registry-cross-sync-output.txt
- **Concern**: `case "$scan_name"` without a default arm drops unknown scan names without a loud registry-drift signal.
- **Suggested revision**: Add `*)` handling: emit explicit error NDJSON and fail non-zero (or another operator-obvious signal), so TSV and driver cannot silently diverge.

### FINDING_15: `changelog-rebase-conflicts` NDJSON `result` stays `pass` when `count>0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-registry-cross-sync-output.txt
- **Concern**: Consumers keying on `result` can disagree with non-zero `count` and with counter aggregation that sums counts regardless of `result`.
- **Suggested revision**: Flip `result` to `fail` when `count>0`, or document that only `count` is authoritative and update all consumers accordingly.

### FINDING_16: Missing `review-findings-full.jsonl` can make category deltas look like true zeros
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Absent category stats can be interpreted as “clean” rather than “data missing,” understating cumulative blank/clean counters for PRs without jsonl.
- **Suggested revision**: Emit explicit skip/partial-data markers in category stats and teach [`audit-compute-counters.sh`](.claude/skills/audit-runs/scripts/audit-compute-counters.sh) to interpret them.

### FINDING_17: `ISSUE_LIST_FAILED` KV emitted on stderr vs documented stdout contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Orchestrators capturing stdout-only can miss structured failure KVs.
- **Suggested revision**: Emit contract KVs on stdout consistently (or update the contract doc everywhere it’s referenced).

### FINDING_18: [OUT_OF_SCOPE] `read -a` / PR list parsing “Bash 3.2 breakage” vs documented Bash 3.2 validity
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Concern**: One reviewer claims `read -a` breaks macOS Bash 3.2 for comma PR lists in [`audit-map-runs.sh`](.claude/skills/audit-runs/scripts/audit-map-runs.sh); portability reviewer marks this out-of-scope and asserts `IFS=',' read -r -a` is valid Bash 3.2 array splitting under `#!/usr/bin/env bash`.
- **Suggested revision**: Reconcile with repo portability policy and a real macOS `/bin/bash` 3.2 check; either dismiss with evidence or replace tokenization only if a concrete incompatibility is confirmed.

### FINDING_19: `cache-freshness` hard-depends on `sort -V` (can abort on older BSD/macOS `sort`)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Under `set -euo pipefail`, unsupported `-V` can non-zero exit and abort the entire scan driver early.
- **Suggested revision**: Remove hard dependency (tuple compare in `awk`/`jq`, or feature-detect `sort -V` with portable fallback).

### FINDING_20: Non-`local` scratch assignments in `scan_codex_round1_adherence` / `scan_coder_tool`
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Loop temporaries leak into global namespace, unlike other helpers—brittle under refactors and `set -u` evolution.
- **Suggested revision**: Mark loop scratch vars as `local` (or otherwise scope them) for consistency and isolation.

### FINDING_21: [OUT_OF_SCOPE] Lexicographic `started_at` compare is a Bash-feature concern only if timestamps aren’t strict ISO-shaped
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: `[[ "$st" > "$best_started" ]]` is lexicographic; acceptable if inputs share stable ISO-8601 shapes; mixed/partial timestamps would be correctness, not Bash-version portability.
- **Suggested revision**: No Bash-level change required unless timestamp shape guarantees are weakened; if shapes vary, fix upstream normalization instead of string-compare semantics.

### FINDING_22: [OUT_OF_SCOPE] `audit-title.md` vs `audit-title.sh` non-contiguous list formatting mismatch
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Markdown describes size-dependent formatting for non-contiguous PR lists while the shell emits one comma form for all non-contiguous cases—documentation/behavior drift outside the Bash-portability checklist.
- **Suggested revision**: Update docs to match implementation (or change implementation to match docs) so title contracts are single-sourced.

### FINDING_23: `cumulative_counters` example in SKILL is out of sync with compute script + markdown schema
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Example documents keys the script does not emit/parse while omitting keys the script reads/writes—breaks the “populate frontmatter from script output” chain.
- **Suggested revision**: Make the example exhaustive relative to emitted/parsed KVs, or remove stale keys until implemented end-to-end.

### FINDING_24: SKILL claims adding a scan is “TSV row only, no SKILL edit” but wiring is multi-artifact
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Contradicts required updates in scan driver, optional counter aggregation, coordinated markdown, and tests.
- **Suggested revision**: Replace with an explicit checklist of all artifacts that must change when adding a scan.

### FINDING_25: [OUT_OF_SCOPE] Human “Scans” table diverges from `scans.tsv` (with partial pre-existing scope note)
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Narrative table omits machine-registered scans (notably `changelog-rebase-conflicts`); at least some older omissions (e.g. `rej-category-blank`) may predate the changelog addition but still contribute to registry/narrative drift.
- **Suggested revision**: Add a row per `scans.tsv` entry or delete the partial table and point readers to `scans.tsv` / [`audit-scan-run.md`](.claude/skills/audit-runs/scripts/audit-scan-run.md); separate “new drift” vs “pre-existing gap” in release notes if useful.

### FINDING_26: No harness coverage for `changelog-rebase-conflicts` NDJSON / `CHANGELOG_*` counter path
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Docs call for coordinated tests, but the harness appears not to reference the new scan/counter wiring—registry can drift undetected.
- **Suggested revision**: Add hermetic fixtures asserting NDJSON shapes and counter summation with synthetic `scan-results` + prior frontmatter samples.
