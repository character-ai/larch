## Decision 1: Era boundary source
- **Question**: How is the pre/post incentive boundary resolved, given the default rule needs a GitHub-only date and today's tool is fully offline?
- **Resolution**: `--era-since-date YYYY-MM-DD` is the primary, deterministic cutoff. Default mode best-effort auto-detects the incentive-shipped date via `gh` (reusing the `_ground_truth_calibration_incentive_shipped` closed-with-PR rule, then reading the close/merge date). When `gh` is unavailable or the incentive has not shipped, fall back to a clear "boundary unavailable; pass --era-since-date" message rather than erroring. The tool stays usable with zero network access via the explicit flag.
- **Source**: user

## Decision 2: Segmentation default (backward compatibility)
- **Question**: With no era flag, does the tool keep today's single report or switch to segmented output?
- **Resolution**: Opt-in. No `--era` flag reproduces today's single unsegmented report byte-for-byte. Segmentation is purely additive: `--era all` renders pre vs post side-by-side; `--era pre|post` filters to one era. Existing callers and all current `test-voter-calibration.sh` assertions stay unaffected.
- **Source**: user

## Decision 3: Runs with missing `started_at`
- **Question**: How are runs whose `manifest.json` lacks a parseable `started_at` placed into an era?
- **Resolution**: They cannot be placed, so exclude them from both pre and post corpora and report the excluded count in the report. This mirrors the existing `excluded_missing_started_at_runs` precedent in `analyze_issues._ground_truth_verdict_run_qualifies`.
- **Source**: codebase

## Decision 4: Boundary precedence when both signals exist
- **Question**: If `--era-since-date` is passed and `gh` also resolves a shipped date, which wins?
- **Resolution**: The explicit `--era-since-date` always wins. `gh` auto-detection runs only when `--era-since-date` is absent.
- **Source**: user

## Decision 5: Scope surfaces
- **Question**: Which files are in-scope?
- **Resolution**: `skills/voter-calibration/scripts/voter-calibration.py` (and contract `voter-calibration.md`), `skills/voter-calibration/SKILL.md`, and `skills/voter-calibration/scripts/test-voter-calibration.sh`. Era tagging happens at file-discovery time because the per-finding rows from `voting.voter_agreement_rows_from_tsv` carry no path or date. A thin shared helper may live in `python/voting.py`, or the script may reuse `analyze_issues._ground_truth_run_started_at_strict` and `_ground_truth_run_dir`. Keep the change surgical and reuse existing severity/agreement math.
- **Source**: feature description / codebase
