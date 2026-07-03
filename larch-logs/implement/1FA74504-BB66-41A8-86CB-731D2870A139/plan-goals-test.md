## Goal
Implement issue #5992: [IMPLEMENTING] difficulty-tiers: difficulty-calibration analyzer.

## Implementation Plan
## Plan

## Approach

Draft from direct repo inspection. `approach-synthesis.txt` is `NO_SKETCHES`.

Build a stdlib-only analyzer under `python/larch/calibration/`. Keep it diagnostic-only. It must read committed `larch-logs/` and write only when `--out` is provided.

Core model:

- Discover run dirs under `larch-logs/{implement,design,review}/` with symlink-safe, fail-soft enumeration (`_safe_child_run_dirs`-style). Do not reuse `run_log_corpus.run_dirs` directly: it requires numeric `issue_number` manifests and would silently omit standalone review runs.
- Treat `manifest.json` as optional best-effort metadata. Admit a run when `difficulty-rating.json` or a known classification source exists.
- Treat missing or malformed `difficulty-rating.json` as unratable. Count it, skip it from confusion matrices, and continue.
- Classification sources with per-skill precedence, mirroring `rejected_analysis` enumeration:
  - implement: `round-*/findings-classification.tsv`; when absent, run-root `review-findings-full.jsonl`.
  - review: `review-findings-classification-round-*.tsv`; when absent, `review-findings.ndjson`, then run-root `review-findings-full.jsonl`.
  - design: `plan-review/round-*/findings-classification.tsv` only (no JSONL fallback).
- Pin an explicit skill-to-panel_kind mapping and pass it into the reused classification helpers: design paths parse with `panel_kind="design"`; implement and review paths parse with `panel_kind="code-review"`.
- One in-scope accepted rule for every source: `voting_result=accepted` (TSV) or `outcome=accepted` (JSONL/NDJSON), not `classification_row_is_oos(...)` (the same inverted helper `issue/_ground_truth.py` uses; drop the `progress_report` alternative), and `finding_id` not starting with `OOS_`. JSONL fallback rows also filter to the skill-owned phase (`code-review` for implement and standalone review). Malformed or unsupported rows increment degraded counters; they are never counted as accepted.
- Finding identity: implement and review `FINDING_N` ids restart each round, so their counted identity is `(numeric round, finding_id)`; the same bare id in two rounds is two findings. Design plan-review ids are stable across continuation rounds, so design identity is bare `finding_id` deduped across rounds. When a stable cross-round identity exists (JSONL `id` / `finding_hash`), collapse on it. Never count the same identity twice; never sum raw per-round row counts.
- Round precedence: extract round numbers as integers from `round-N` directories and `...-round-N.tsv` filenames (the `_ground_truth_round_num` pattern in `python/larch/issue/_ground_truth.py`), sort numerically, and when one identity has conflicting rows, the highest numeric round wins (round 10 beats round 2).
- Run-level accepted count: the size of the deduped identity set that passes the in-scope accepted rule.
- Join `larch-logs/rejected-analysis-verdicts.tsv` by `source_skill`, `run_id`, `round_num`, and `finding_id` when present. Dedupe sidecar rows on `finding_hash` (last row wins) and count duplicates in a `duplicate_sidecar_rows` degraded counter. False-negative burden totals count only `verdict=confirmed` rows; stale or already-fixed verdicts render as separate non-burden annotations. The join annotates under-rating rows; it never changes the fixed realized-difficulty formula.
- Load token and timing reports when present:
  - implement: `token-report.json`, `timing-report.json`
  - design: `token-report-final.json`, `timing-report-final.json`
  - review: best-effort same root names if present
- Degrade on gc-slimmed dirs. Missing classification sources, token reports, timing reports, or rejected sidecar rows produce `n/a` cells and corpus counters, not crashes.

Realized tier formula:

- Evaluate committed escalation evidence first: `HARD` when `difficulty-rating.json.escalations` is non-empty, even when no classification artifact survives GC.
- Otherwise `HARD` if the run tripped the substantiality gate per committed evidence or accepted at least 3 in-scope findings (the deduped identity count above); `TRIVIAL` if it accepted 0; else `MODERATE`.
- Only non-escalated runs without any parseable classification source have `unknown` accepted count and realized tier: increment a degraded counter, exclude the run from confusion-matrix denominators, and still emit its rating row.
- Severity never feeds the realized tier.
- Substantiality evidence is committed-only: the same `escalations` array, which the live gates own. Do not reconstruct the gate from severity labels, `CODER_INPUT_COUNT` / `FIX_COUNT`, review-and-fix env values, or structural-LOC snapshots: those are stdout-only or GC-sensitive, not committed contracts.
- When no committed substantiality evidence exists, mark the proxy `unknown` and let the accepted-count thresholds decide the tier.

Reports on stdout markdown:

1. Corpus summary and degraded-input counters.
2. Predicted/applied versus realized confusion matrix per skill. Matrix denominators include only runs with both a rating and a known realized tier.
3. Confusion matrix per rater, using `rater`, `rater_tool`, and `rater_model`.
4. Under-rating misses: `tier_rank(realized) > tier_rank(applied_tier)` using `larch.calibration.difficulty` tier ranks, over ratable runs only. Rows show `predicted_tier`, `panel_skipped`, relative run-log links, and issue numbers when available.
5. Per-tier token/cost and latency table. Use token totals always; use USD only when an existing pricing helper can price the report safely, else render `n/a`.
6. Audit-run deltas with a deterministic peer-matching contract: audited runs have `audit_evaluated=true` or `audit_upgrade=true`. Peers share the same skill, the same pre-audit tier, and the same calendar month, with audit fields false or absent. The pre-audit tier derives from committed fields only: the most severe of `design_tier`, `implement_tier`, and `predicted_tier`, raised by `floors_applied`; never the post-audit `applied_tier` of an audited run. Month bucketing (here and in drift tables) pins to `manifest.started_at` UTC; runs missing either the pre-audit tier or the timestamp are excluded from pairing and render `n/a`. Render `n/a` when no peer matches; never synthesize peers.
7. Escalation statistics.
8. Tier-distribution drift by month (same pinned timestamp) and by rater model.

## Files to modify/create

### NEW: python/larch/calibration/difficulty_calibration.py

Add the analyzer module.

Implementation notes:

- Use frozen dataclasses for run records, outcome counts, cost/timing summaries, and aggregate rows.
- Keep file reads symlink-safe and fail-soft, matching nearby report analyzers.
- Reuse existing helpers where practical:
  - symlink-safe child-dir enumeration mirroring `larch.report.run_log_corpus` internals (`_safe_child_run_dirs`); manifest loads stay best-effort.
  - `larch.review.voting.classification_row_panel_inputs` / `classification_row_is_oos` for classification parsing, with the pinned panel_kind mapping.
  - numeric round parsing per the `_ground_truth_round_num` pattern; JSONL enumeration parity with `rejected_analysis._implement_jsonl_records`.
  - `larch.calibration.difficulty` tier constants and rank helpers.
  - `larch.report.report_tokens_models.safe_int` for numeric coercion.
- Do not shell out to `gh`. Links must come from committed data or relative run-log paths.
- Add `analyze_main(argv) -> int`.
- Flags:
  - `--log-root DIR`, default `<git toplevel>/larch-logs`, falling back to `cwd/larch-logs`.
  - `--out FILE`, write report to file and print `REPORT_FILE=<path>`.
- Missing `--log-root` should exit `2` with a clear stderr diagnostic.
- Keep all mutations behind `--out`; no run-log writes.

### UPDATED: python/larch/cli.py

Register:

- `("difficulty-calibration", "analyze") -> ("larch.calibration.difficulty_calibration", "analyze_main")`

### NEW: python/tests/calibration/test_difficulty_calibration.py

Add synthetic offline pytest coverage.

Cover:

- Confusion matrix rows for all three skills.
- Realized tier formula:
  - 0 accepted -> `TRIVIAL`
  - 1 to 2 accepted -> `MODERATE`
  - 3 accepted -> `HARD`
  - non-empty `escalations` -> `HARD`
- An escalated gc-slimmed run with no classification source is `HARD`, not `unknown`.
- Design identity: the same design `finding_id` accepted in two rounds counts once; a design finding accepted in round 1 and rejected in round 2 is excluded (highest numeric round wins; round 10 beats round 2, not lexicographic order).
- Implement identity: `FINDING_1` accepted in round 1 and `FINDING_1` accepted in round 2 count as two distinct findings.
- A design-TSV header fixture pins `panel_kind="design"`; implement and review fixtures pin `panel_kind="code-review"`.
- Severity does not alter realized tier: accepted high-severity rows without committed gate evidence leave the substantiality proxy `unknown` and the tier follows the accepted count.
- Missing `difficulty-rating.json` is counted as unratable and does not crash.
- A gc-slimmed implement dir with only keep-set files recovers the accepted set from `review-findings-full.jsonl` (`outcome=accepted`, skill-owned phase) and yields a non-unknown realized tier eligible for the matrices.
- A review run with TSVs absent recovers from `review-findings.ndjson`.
- A non-escalated run with no parseable classification source sets realized tier `unknown`, is excluded from matrix denominators, and increments the degraded counter; token reports, timing reports, and sidecar rows degrade to counters or `n/a`.
- An audited/unaudited matched pair with explicit month boundaries renders a delta row; an audited run with no matching peer (or no recoverable pre-audit tier or timestamp) renders `n/a`.
- An applied `MODERATE` / realized `HARD` run appears in the under-rating miss table.
- Duplicate sidecar `finding_hash` rows dedupe (last wins) and increment `duplicate_sidecar_rows`; only `verdict=confirmed` rows count toward false-negative burden.
- `--out` writes the report and prints only `REPORT_FILE=...`.
- Missing log root exits `2`.

### UPDATED: Makefile

Add a focused target, for example:

- `test-difficulty-calibration:`
  - `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py`

Do not add a Bash harness unless the implementation adds skill-local scripts.

### NEW: skills/difficulty-calibration/SKILL.md

Add a thin public skill.

Required content:

- Frontmatter with `name: difficulty-calibration`, a diagnostic description, `allowed-tools: Bash, Read`, and a useful argument hint.
- Readability-style preamble.
- Usage:
  - `/difficulty-calibration [--log-root DIR] [--out FILE]`
- Run:
  - `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" difficulty-calibration analyze [flags]`
- State that the analyzer reads committed logs only.
- State that it changes no thresholds, panels, reviewer points, or live routing.
- Tell the main agent not to re-tally or reformat the report.

### UPDATED: scripts/lint-readability-preamble.tsv

Add the new skill row so the preamble lint keeps passing:

- `skills/difficulty-calibration/SKILL.md` with variant `orchestrator-inline` and `expected_count` 1.
- Bump the `__metadata__` expected_count total to match the new row count.

### UPDATED: README.md

Add `/difficulty-calibration` to the support analysis tools list.

Add a public skill table row near `/voter-calibration`:

- Arguments: `[--log-root DIR] [--out FILE]`
- One concise description of predicted-vs-realized difficulty calibration from committed logs.

### UPDATED: docs/skills.md

Add `/difficulty-calibration` to the public skills list.

Add a section near `/voter-calibration` that documents:

- Arguments.
- Source path.
- Read-only diagnostic posture.
- Joined artifacts and the per-skill classification precedence.
- Fixed realized-difficulty formula, including escalation-evidence-first ordering, the deduped identity count, and committed-only substantiality evidence.
- The pinned `manifest.started_at` UTC month-bucket rule for audit pairing and drift tables.
- Reports emitted.
- Degraded-input behavior.

### UPDATED: docs/run-logs.md

Update analyzer documentation in the consumer/audit area.

Mention:

- `/difficulty-calibration` reads `difficulty-rating.json`, classification TSVs (with `review-findings-full.jsonl` / `review-findings.ndjson` fallback), token/timing reports, and `rejected-analysis-verdicts.tsv`.
- It tolerates gc-slimmed dirs and missing pre-initiative artifacts; non-escalated runs without a parseable classification source report realized tier `unknown`.
- It is read-only and produces no run-log batches.

### UPDATED: docs/linting.md

Add the new focused test row:

- `make test-difficulty-calibration`
- State that it exercises the offline synthetic fixture and CLI report shape.

### UPDATED: docs/configuration-and-permissions.md

Update strict-permissions skill snippets to include both forms:

- `Skill(difficulty-calibration)`
- `Skill(larch:difficulty-calibration)`

Keep ASCII sort order.

## Edge cases

- Pre-initiative runs may lack `difficulty-rating.json`; count them as unratable.
- A run can have `predicted_tier`, `applied_tier`, and `panel_tier` that differ. Use `applied_tier` for the primary confusion matrix and include predicted/panel fields in row details.
- A run can be `panel_skipped=self-review`. Include it, but mark skipped-panel status in the under-rating table.
- Review logs may have no token/timing reports. Render cost and latency as `n/a`.
- Classification TSV schemas vary. Use existing voting helpers and skip unsupported rows with counters.
- `rejected-analysis-verdicts.tsv` can be absent, empty, or partial. Do not fail the main report.
- Run dirs may be symlinks or malformed. Skip unsafe dirs.

## Failure modes

- Substantiality cannot be fully reconstructed after GC. Mark the proxy unknown instead of guessing.
- Token pricing can drift or be unavailable. Always show token totals; show USD only when safely computed.
- Rater model strings can be empty. Group empty values under `unknown`.
- Relative links may not render outside the repo. Still prefer committed relative run-log paths over network calls.

## Testing strategy

Run focused tests:

- `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py`

Run broader relevant Python checks if touched files require it:

- `make py-test`
- `make py-lint`

For docs-only follow-up edits, use relevant markdown or repo checks per `docs/linting.md`.

## Acceptance

- Produces all reports from committed logs alone; tolerates pre-initiative runs (absent batches) and gc-slimmed directories.
- Diagnostic only: changes no thresholds, panels, or points.
- Documented alongside the other run-log analyzers.

mechanical_churn: false
diff_lines: 950

## Test plan
(no test plan section in plan-file)
