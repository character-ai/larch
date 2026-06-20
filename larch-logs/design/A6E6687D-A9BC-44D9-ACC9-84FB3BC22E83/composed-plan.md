## Plan

## Approach

- Keep this **lightweight**.
- Measure only **voter agreement vs panel verdict**.
- Do **not** use realized outcomes, issue fate, reverts, token allocation, or live voter rewards.
- Keep `findings-classification.tsv` **header constants and column schemas unchanged** for new writes.
- Reuse existing per-voter `vN_*` cells.
- Parse **committed** design and code-review TSVs across supported historical shapes (22-column design with `body_severity`, 21-column design without `body_severity`, 21-column code-review, legacy 18-column compact code-review).
- **Single agreement math path**: live `voting-tally.md` scoreboards and `/voter-calibration` TSV ingestion must call the same row builders and `compute_voter_agreement` aggregate; do not reimplement eligibility or agree/disagree rules separately in tally modules.

## Agreement definition

- Count only rows with:
  - `voting_result` of `accepted` or `rejected`.
  - At least **two parseable YES/NO voter cells**.
- Exclude rows with:
  - `voting_result=neutral`.
  - zero-voter main-agent paths.
  - single-voter fallback paths.
- A voter agrees when:
  - `accepted` and voter vote is `YES`.
  - `rejected` and voter vote is `NO`.
- Treat empty, missing, or `JUDGE_ERROR` voter cells as **missing**, not disagreement.
- Track `missing` separately so parse-rate failures do not look like outlier voting.
- Compute `agreement_rate` as `agree / (agree + disagree)` when the denominator is positive; missing votes are **not** in the rate denominator.
- **Chronic outlier rule** (single deterministic default, shared by shared math, live tally scoreboards, analyzer, docs, and tests):
  - `outlier = true` iff `eligible >= min_votes` **and** `agreement_rate < outlier_threshold`.
  - Default `min_votes = 20` (`--min-votes` on the analyzer).
  - Default `outlier_threshold = 0.50` (`--outlier-threshold` on the analyzer; not exposed on `/voter-calibration` SKILL argv unless docs list it).
  - Low-sample voters (`eligible < min_votes`) are never flagged outliers.

## Files to modify/create

### UPDATED: python/voting.py

Add shared voter-calibration helpers with **one row+aggregate path** for both committed TSV ingestion and live tally:

- `voter_agreement_row_from_panel(*, voting_result: str, voter_votes: list[tuple[str, str]]) -> dict | None`
  - Input: panel `voting_result` plus ordered `(voter_label, vote)` pairs where `vote` is `YES`, `NO`, empty, or `JUDGE_ERROR`.
  - Return one eligibility row dict when the row qualifies (accepted/rejected with at least two parseable YES/NO cells); otherwise `None`.
  - Encode agree/disagree/missing per voter using the shared agreement definition above.
- `voter_agreement_rows_from_tsv(text, *, panel_kind)` for committed TSV ingestion.
  - **Header-driven schema detection** (never width-only):
    - design: require `finding_reviewers` in header; treat as **22-column** when `body_severity` is present, **21-column** when absent (do not mis-map `v3_tool` as `body_severity` or drop the last voter).
    - code-review: require `reviewer_slots` in header; use **21-column** `csv.DictReader` path when `v1_severity`..`v3_severity` are present (mirror `fluff-analysis.py` `parse_impl_tsv` header logic); fall back to **18-column** positional compact parsing when named rating columns are absent.
  - Map each parsed data row to `(voting_result, voter_votes)` and delegate to `voter_agreement_row_from_panel`.
- `compute_voter_agreement(rows, *, min_votes=20, outlier_threshold=0.50)` returning stable records:
  - `voter`
  - `panel`
  - `eligible`
  - `agree`
  - `disagree`
  - `missing`
  - `agreement_rate`
  - `outlier`
- `render_voter_scoreboard(records)` for markdown tables.
- Use canonical fallback voter names:
  - design: `vN_tool` if present, else `v1=Claude`, `v2=Codex`, `v3=Cursor`.
  - three-slot code review: `v1=cursor-validity`, `v2=cursor-plan-fidelity`, `v3=cursor-pragmatism`.
  - compact fallback: positional `v1`, `v2`, `v3` unless caller supplies better labels.
- Add `## Voter Agreement Scoreboard` to `_ALLOWED_CODE_REVIEW_HEADERS` so `review_and_fix` / `voting.write-tally` code-review body validation accepts the new tally section.
- Do **not** modify `accept_finding`, `classify_result`, reviewer scoring, `FINDINGS_CLASSIFICATION_HEADER`, or `CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER`.

### UPDATED: python/plan_review_tally.py

Append a live **Voter Agreement Scoreboard** section to `voting-tally.md` after the reviewer scoreboard.

- Inside `_render`, for each `item_id` in `sorted_ids`:
  - Reuse existing `_tally_votes_for_id(item_id)` for `voting_result`.
  - Build per-finding `(voter_label, vote)` pairs from the same `slot_file[pos]` / `slot_tool[pos]` / `vote_for_id` data already used when writing classification rows (skip dead slots; map `JUDGE_ERROR` to missing).
  - Call `voter_agreement_row_from_panel` per finding; collect non-`None` rows.
- Pass collected rows to `compute_voter_agreement` and append `render_voter_scoreboard(...)` output.
- Do **not** duplicate eligibility or agree/disagree logic inline in `_render`.
- Skip the section or render an explicit `undefined` row when the panel has fewer than two parseable voter cells across all findings.
- Preserve existing `VOTING_TALLY_FILE` and `TALLY_PLAN_REVIEW_STATUS` output.
- Do not create or alter TSV columns.

### UPDATED: python/review_tally.py

Append a live **Voter Agreement Scoreboard** section to code-review `voting-tally.md`.

- Wire both paths through the same `voter_agreement_row_from_panel` → `compute_voter_agreement` → `render_voter_scoreboard` chain:
  - three-slot Cursor voters (`args.voter_tools` labels with `args.voter_files` votes).
  - legacy compact `--voter-files` fallback (positional labels unless better tool names are available).
- Build per-finding row dicts from the same vote reads used for classification TSV rows in the main tally loop.
- For `effective == 0`, render no agreement denominator and do not crash.
- Preserve reviewer scoreboard, `scout-archetype-yield.tsv`, tally env, and emitted KV contracts.

### NEW: skills/voter-calibration/SKILL.md

Add a public sibling skill with required YAML frontmatter modeled on `skills/fluff-analysis/SKILL.md`:

```yaml
---
name: voter-calibration
description: "Use when analyzing voter agreement and chronic outlier voters from committed larch run logs; diagnostic only — does not affect spawning, thresholds, tokens, or reviewer points."
allowed-tools: Bash, Read
```

- Usage: `/voter-calibration [--log-root DIR] [--min-votes N] [--outlier-threshold R] [--out FILE]`.
- Describe it as a committed-run analyzer for voter agreement and chronic outliers.
- State that it measures agreement only.
- State that it does not use realized outcomes or affect spawning, thresholds, tokens, or reviewer points.
- Document defaults: `--log-root` resolves to `<git toplevel>/larch-logs`; `--min-votes 20`; `--outlier-threshold 0.50`.
- Invoke the script directly:
  - `python3 "${CLAUDE_PLUGIN_ROOT}/skills/voter-calibration/scripts/voter-calibration.py" [flags]`.
- Note that direct `python3 .../voter-calibration.py` and `make test-voter-calibration` runs do not require `CLAUDE_PLUGIN_ROOT`; the script bootstraps `python/` imports from its own path (see script contract).

### NEW: skills/voter-calibration/scripts/voter-calibration.py

Add a stdlib-only analyzer.

- **Plugin-root bootstrap** (run before any `python/` import; required for direct script and harness execution when `CLAUDE_PLUGIN_ROOT` is unset):
  - Resolve plugin root as `Path(os.environ["CLAUDE_PLUGIN_ROOT"]) when CLAUDE_PLUGIN_ROOT is set and non-empty, else Path(__file__).resolve().parents[3]` (`skills/voter-calibration/scripts/` → plugin root).
  - Insert `str(plugin_root / "python")` at the front of `sys.path` once.
  - Import shared math from `voting` only after bootstrap (e.g. `from voting import voter_agreement_rows_from_tsv, compute_voter_agreement, ...`).
  - Do **not** rely on cwd-only `sys.path` insertion or implicit checkout layout.
- Discover:
  - `larch-logs/design/*/plan-review/round-*/findings-classification.tsv`.
  - `larch-logs/implement/*/round-*/findings-classification.tsv`.
  - `larch-logs/review/*/review-findings-classification-round-*.tsv` when present.
- Default `--log-root` to `<git toplevel>/larch-logs` using the same resolution pattern as `skills/fluff-analysis/scripts/fluff-analysis.py` (`git rev-parse --show-toplevel` when available, else `cwd/larch-logs`).
- Exit non-zero with a clear diagnostic only when the **resolved** log-root directory is absent.
- Parse TSVs via `voter_agreement_rows_from_tsv` (header-driven schema detection; no separate parser logic).
- Aggregate by:
  - skill/panel.
  - voter identity.
  - optionally global voter identity.
- Apply the shared outlier rule (`eligible >= min_votes` and `agreement_rate < outlier_threshold`).
- Render markdown:
  - `# Voter Calibration Report`
  - corpus counts.
  - agreement table.
  - chronic outlier table (using the explicit threshold).
  - missing-vote table.
  - notes on excluded neutral and single/zero-voter panels.
- If `--out` is provided, write the report there and keep stdout concise.

### NEW: skills/voter-calibration/scripts/voter-calibration.md

Document the analyzer contract.

- Inputs and glob patterns.
- **Plugin-root bootstrap contract**:
  - `CLAUDE_PLUGIN_ROOT` when set and non-empty; else `Path(__file__).resolve().parents[3]`.
  - `sys.path` receives `<plugin_root>/python` before importing `voting`.
  - SKILL invocation may set `CLAUDE_PLUGIN_ROOT`; direct `python3 voter-calibration.py` and `make test-voter-calibration` must succeed without it.
- TSV schema compatibility with **header-driven** detection:
  - 22-column design (`body_severity` present).
  - 21-column design (`finding_reviewers`, `vN_tool`, **no** `body_severity`).
  - 21-column code-review (`reviewer_slots`, named `vN_*` rating columns).
  - 18-column compact code-review (positional, no `vN_tool`).
- Agreement definition and `agreement_rate` denominator (`agree + disagree`; missing excluded).
- Shared row builder contract: `voter_agreement_row_from_panel` is the single per-finding semantics source; TSV ingestion and live tally both delegate to it.
- Outlier rule: `eligible >= min_votes` and `agreement_rate < outlier_threshold` (defaults 20 and 0.50).
- Output headings.
- Exit codes (`0` success; `2` resolved log-root missing).

### NEW: skills/voter-calibration/scripts/test-voter-calibration.sh

Add a synthetic offline harness.

- Build a temp `larch-logs` fixture.
- Include:
  - design 22-column TSV with Claude/Codex/Cursor.
  - design **21-column** TSV with `finding_reviewers` and `vN_tool` but **no** `body_severity` (assert header-driven parser maps `v3_tool` correctly and does not treat last column as `body_severity`).
  - code-review 21-column TSV with cursor voter tools.
  - legacy compact 18-column TSV.
  - neutral rows excluded from denominators.
  - single-voter fallback excluded.
  - chronic outlier case above `--min-votes` with `agreement_rate < 0.50`.
- Assert report heading, voter rows, exclusion notes, outlier flag, and default log-root behavior when run from a git worktree with the fixture path omitted.
- Assert missing resolved log-root exits `2`.
- **Bootstrap assertion**: run `python3 "$ANALYZER" --log-root "$FIX/larch-logs"` with `CLAUDE_PLUGIN_ROOT` unset in a clean subshell; assert exit `0` and that the report contains expected voter rows (proves `voting` import succeeds via `parents[3]` fallback, not cwd-only path hacks).

### NEW: skills/voter-calibration/scripts/test-voter-calibration.md

Document the harness contract and how to run it.

- Include the `CLAUDE_PLUGIN_ROOT`-unset bootstrap assertion and its purpose.

### UPDATED: python/test_voting.py

Add unit tests for shared math.

- `voter_agreement_row_from_panel`:
  - Accepted panel: YES agrees, NO disagrees.
  - Rejected panel: NO agrees, YES disagrees.
  - Neutral row returns `None`.
  - Single-voter row returns `None`.
  - Empty and `JUDGE_ERROR` cells counted as missing, not disagreement.
- `voter_agreement_rows_from_tsv`:
  - 22-column design parsing.
  - **21-column design without `body_severity`** (header-driven; verify `v3_tool` and voter votes are not shifted).
  - 21-column code-review and 18-column compact parsing.
- `compute_voter_agreement`:
  - Outlier flag: not set below `min_votes`; set when `eligible >= min_votes` and `agreement_rate < 0.50`; not set at exactly `0.50`.
- Cross-path parity: TSV-ingested rows and panel-built rows for the same fixture produce identical `compute_voter_agreement` output.

### UPDATED: python/test_plan_review_tally.py or python/test_plan_review.py

Extend plan-review tally tests.

- Assert `voting-tally.md` contains `## Voter Agreement Scoreboard`.
- Assert a mixed accepted/rejected run reports expected agreement for Claude/Codex/Cursor.
- Assert zero-voter path does not crash and does not produce fake agreement.
- Assert live tally agreement rows match `compute_voter_agreement(voter_agreement_rows_from_tsv(...))` on the emitted `findings-classification.tsv` for the same fixture.

### UPDATED: python/test_review_tally.py

Extend code-review tally tests.

- Assert three-slot code-review `voting-tally.md` contains voter agreement rows for `cursor-validity`, `cursor-plan-fidelity`, and `cursor-pragmatism`.
- Assert legacy compact fallback either labels slots positionally or excludes undefined single-voter agreement.
- Assert existing reviewer scoreboard rows remain unchanged.
- Assert `python/cli.py voting write-tally --phase code-review` accepts a body containing `## Voter Agreement Scoreboard` without unrecognized-section failure.
- Assert live tally agreement matches TSV-ingested agreement on the emitted classification file for the same run.

### UPDATED: Makefile

Add `test-voter-calibration`.

- Run the new shell harness through `python3 python/cli.py timing harness-mark`.
- Add it to one harness shard.
- Keep `make py-lint` scoped to `python/`; skill-local script coverage comes from the harness.

### UPDATED: README.md

Add `/voter-calibration` to the public skills table.

- Keep the description short.
- Link to `docs/skills.md#voter-calibration`.

### UPDATED: docs/skills.md

Add `/voter-calibration`.

- List arguments (`--log-root`, `--min-votes`, `--outlier-threshold`, `--out`).
- Link to `skills/voter-calibration/SKILL.md`.
- Explain committed-run aggregation and outlier flags (`eligible >= min_votes` and `agreement_rate < 0.50` by default).
- State the non-goals.

### UPDATED: docs/voting-process.md

Document that voting now emits a voter agreement scoreboard.

- Clarify it is diagnostic only.
- Clarify thresholds and verdicts are unchanged.
- Note neutral and single/zero-voter panels are excluded from agreement denominators.
- Document the outlier rule and that missing votes are excluded from `agreement_rate`.
- Note live tally and `/voter-calibration` share the same `voter_agreement_row_from_panel` / `compute_voter_agreement` math.

### UPDATED: docs/point-competition.md

Add a short voter-calibration note.

- Reviewer points remain unchanged.
- Voter agreement is measured separately.
- Voter calibration does not yet affect token allocation or spawning.

### UPDATED: docs/run-logs.md

Document the new `voting-tally.md` voter scoreboard section.

- Do not add a new committed artifact unless implementation chooses a separate file.
- Clarify that committed classification TSV schemas remain backward compatible for new writes.
- Mention older **21-column design** TSVs (no `body_severity`) and **18-column** compact code-review TSVs are still readable by the analyzer via header-driven detection.

### UPDATED: docs/linting.md

Add the new `make test-voter-calibration` target to the harness table.

## Edge cases

- **Neutral verdicts**: exclude from agreement denominators.
- **Accepted 2-1 split**: dissenting NO voter disagrees.
- **Rejected unanimous NO**: all NO voters agree.
- **Single-voter fallback**: undefined, excluded.
- **0-voter main-agent path**: undefined, excluded.
- **Dead slots**: count missing cells separately; missing excluded from `agreement_rate`.
- **Legacy 21-column design TSVs**: detect via absent `body_severity` header token; parse with `body_severity` optional; never infer schema from row width alone.
- **Legacy 18-column TSVs**: detect via absent named `vN_severity` header tokens; parse positionally.
- **Malformed TSV rows**: skip with a warning counter in the analyzer, not a crash.
- **No qualifying rows**: render `n/a` rates and explain why.
- **Low sample voters**: never flagged outlier when `eligible < min_votes`.
- **Live vs committed parity**: same per-finding inputs must yield identical agreement rows whether built from slot votes or re-read from committed TSV.
- **Direct script / harness runs without `CLAUDE_PLUGIN_ROOT`**: bootstrap via `Path(__file__).resolve().parents[3]`; do not depend on cwd or an ambient checkout `python/` on `PYTHONPATH`.

## Failure modes

- Analyzer resolved log-root absent: exit non-zero with a diagnostic.
- Analyzer sees unknown schema (unrecognized header tokens): skip file, count it under malformed/skipped files.
- Width-only schema guess mis-mapping `v3_tool` as `body_severity`: prevented by header-driven detection and 21-column fixture coverage.
- Live tally path has no qualifying rows: keep tally success and render undefined agreement.
- Divergent live vs TSV agreement math: prevented by shared `voter_agreement_row_from_panel` + `compute_voter_agreement` path and parity tests.
- Outlier threshold too aggressive: use `--min-votes` and default `0.50`; do not label low-sample voters.
- Code-review tally flush with new scoreboard section: prevented by updating `_ALLOWED_CODE_REVIEW_HEADERS`.
- Missing skill frontmatter breaking plugin discovery: prevented by standard `name` / `description` / `allowed-tools` YAML block.
- **`voting` import failure on direct runs**: prevented by explicit plugin-root bootstrap (`CLAUDE_PLUGIN_ROOT` or `parents[3]`) plus harness assertion with `CLAUDE_PLUGIN_ROOT` unset; cwd-only `sys.path` insertion must not be used.

## Testing strategy

- Run targeted Python tests:
  - `python3 -m pytest python/test_voting.py python/test_plan_review.py python/test_review_tally.py -q`
- Run skill harness:
  - `make test-voter-calibration` (includes `CLAUDE_PLUGIN_ROOT`-unset bootstrap assertion)
- Run relevant existing harnesses:
  - `make test-tally-plan-review`
  - `make test-tally-code-votes`
- Final required checks:
  - `make lint`
  - `make py-lint`
  - `make py-test`

## Acceptance

- `python/voting.py` adds `voter_agreement_row_from_panel`, `voter_agreement_rows_from_tsv`, `compute_voter_agreement`, and `render_voter_scoreboard`. `accept_finding`, `classify_result`, reviewer scoring, `FINDINGS_CLASSIFICATION_HEADER`, and `CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER` are unchanged.
- Agreement math matches the definition: only `accepted`/`rejected` rows with >=2 parseable YES/NO cells are eligible; `accepted`+YES and `rejected`+NO agree; empty/`JUDGE_ERROR` count as missing; `agreement_rate = agree / (agree + disagree)` with missing excluded; `outlier = (eligible >= min_votes and agreement_rate < outlier_threshold)`, defaults 20 and 0.50, never flagged below `min_votes`.
- Header-driven schema detection parses 22-col design, 21-col design (no `body_severity`), 21-col code-review, and 18-col compact code-review without shifting voter columns; width-only inference is not used.
- `python/plan_review_tally.py` and `python/review_tally.py` append a `## Voter Agreement Scoreboard` section to `voting-tally.md`, built through the shared row+aggregate path (no duplicated eligibility logic). Existing tally outputs, the reviewer scoreboard, `scout-archetype-yield.tsv`, tally env, and emitted KV contracts are unchanged. Zero/single-voter panels render undefined and do not crash.
- `## Voter Agreement Scoreboard` is added to `_ALLOWED_CODE_REVIEW_HEADERS` so code-review tally body validation accepts the new section.
- New `skills/voter-calibration/` skill ships: `SKILL.md` (with `name`/`description`/`allowed-tools` frontmatter), `scripts/voter-calibration.py`, `scripts/voter-calibration.md`, `scripts/test-voter-calibration.sh`, `scripts/test-voter-calibration.md`. The analyzer aggregates voter agreement and flags chronic outliers across committed `larch-logs/{design,implement,review}` classification TSVs.
- The analyzer imports shared math via plugin-root bootstrap (`CLAUDE_PLUGIN_ROOT` when set, else `Path(__file__).resolve().parents[3]`); `python3 .../voter-calibration.py` and `make test-voter-calibration` succeed with `CLAUDE_PLUGIN_ROOT` unset. A missing resolved log-root exits non-zero with a diagnostic.
- Tests: `python/test_voting.py` covers the shared math and all schema shapes plus cross-path parity; `python/test_plan_review.py` (or `test_plan_review_tally.py`) and `python/test_review_tally.py` assert the live scoreboard section, expected agreement rows, zero-voter safety, body-validation acceptance, and live-vs-committed parity.
- `make test-voter-calibration` is added and wired into one harness shard; `docs/linting.md` lists it.
- Docs updated: `README.md` skills table, `docs/skills.md`, `docs/voting-process.md`, `docs/point-competition.md`, `docs/run-logs.md`.
- `make lint`, `make py-lint`, and `make py-test` pass.
- Out of scope and not present: realized-outcome / issue-fate / revert calibration; changes to vote thresholds, dedup, reviewer scoring, token allocation, or spawning; changes to `/fluff-analysis`; new committed run-log artifacts beyond the `voting-tally.md` section.

review_status: complete
rounds_completed: 4
diff_lines: 1075
