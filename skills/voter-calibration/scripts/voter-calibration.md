# voter-calibration.py contract

`skills/voter-calibration/scripts/voter-calibration.py` is the analyzer behind the `/voter-calibration` skill. It is stdlib-only Python and runs directly.

## Inputs

The analyzer scans these committed log patterns under `--log-root`:

- `larch-logs/design/*/plan-review/round-*/findings-classification.tsv`
- `larch-logs/implement/*/round-*/findings-classification.tsv`
- `larch-logs/review/*/review-findings-classification-round-*.tsv`

Default `--log-root` resolves to `<git toplevel>/larch-logs` when `git rev-parse --show-toplevel` succeeds. It falls back to `cwd/larch-logs` otherwise.

## Plugin-root bootstrap contract

- Use `CLAUDE_PLUGIN_ROOT` when it is set and non-empty.
- Otherwise use `Path(__file__).resolve().parents[3]`.
- Insert `<plugin_root>/python` into `sys.path` before importing `voting`.
- SKILL invocation may set `CLAUDE_PLUGIN_ROOT`.
- Direct `python3 voter-calibration.py` and `make test-voter-calibration` must succeed without it.

## Era segmentation

`--era {all,pre,post}` opts into diagnostic pre/post incentive segmentation. `--era-since-date YYYY-MM-DD` sets an explicit UTC-midnight cutoff and wins over auto-detection. `--era-since-date` is only valid with `--era`. A malformed date exits `2` with an `--era-since-date` message.

When `--era` is present without an explicit date, auto-detection runs only after plugin-source repo resolution succeeds. Repo resolution uses `git -C <plugin_root> config --get remote.origin.url` from `CLAUDE_PLUGIN_ROOT` or the bootstrapped plugin root. The local slug helper applies the same three remote-URL transforms as `_detect_repo()`'s remote branch: strip `git@host:`, strip `https://host/`, and strip trailing `.git`. It does not call `_detect_repo()`. It does not run unscoped `gh repo view`. Auto `gh issue view` always passes `--repo owner/repo`.

Auto boundary uses one `gh issue view` fetch for incentive #5461 with `--json number,state,stateReason,labels,body,closedAt,closedByPullRequestsReferences`. The payload feeds `_ground_truth_calibration_incentive_shipped(issues=[payload], repo=None)` so no second `gh` fetch can occur. The payload number is normalized with `{**payload, "number": ...}` so canonical #5461 wins. After the shipped gate, missing or unparseable `closedAt` makes the boundary unavailable. There is no PR `mergedAt`, `updated_at`, or manifest timestamp fallback.

Missing `gh` and missing `git` are soft failures. `FileNotFoundError` from either subprocess renders boundary-unavailable guidance and exits `0`, not a traceback. Boundary-unavailable reports tell the operator to pass `--era-since-date`. `--out FILE` writes the guidance report and prints `REPORT_FILE=...`.

Era bucketing uses `_ground_truth_run_dir(path, panel_kind=...)` and `_ground_truth_run_started_at_strict(run_dir)`. Runs with missing or invalid `manifest.json` `started_at` are excluded from both eras and counted once per unique run. Runs before the boundary are pre-incentive. Runs exactly at the boundary are post-incentive.

Pinned era output headings:

- `## Pre-incentive era`
- `## Post-incentive era`
- `## Agreement Table` in every emitted era slice
- `## Voter Severity Scoreboard` in every emitted era slice

Segmentation is diagnostic only.

## TSV compatibility

Parsing delegates to `voting.voter_agreement_rows_from_tsv` and uses header-driven schema detection:

- 22-column design TSVs with `body_severity`.
- 21-column design TSVs with `finding_reviewers`, `vN_tool`, and no `body_severity`.
- 21-column code-review TSVs with `reviewer_slots` and named `vN_*` rating columns.
- 18-column compact code-review TSVs with positional `v1`, `v2`, `v3` voters and no `vN_tool`.

## Agreement and severity definition

`voting.voter_agreement_row_from_panel` is the single per-finding semantics source. TSV ingestion and live tally both delegate to it.

Eligible rows have an `accepted` or `rejected` verdict and at least two parseable `YES`/`NO` voter cells. `accepted` plus `YES` agrees. `rejected` plus `NO` agrees. Empty, missing, and `JUDGE_ERROR` cells count as missing.

`agreement_rate` is `agree / (agree + disagree)`. Missing votes are excluded.

The outlier rule is `eligible >= min_votes` and `agreement_rate < outlier_threshold`. Defaults are `20` and `0.50`.

Severity calibration uses the same eligible rows. It counts only valid `YES` voter-cell severities in the High Rate and Calibration Score denominators. Missing or invalid YES severities are reported separately and do not enter those denominators. `uncertain` is valid non-high input. High Rate is `(blocker + major) / valid_yes_severity_count`. The default high-severity threshold is `0.90`, and `uncalibrated` is true when High Rate is above that threshold.

Calibration Score is a voter-side standing signal derived from threshold excess. At or below the threshold it is `1.000`. Above the threshold it declines linearly as `1 - ((high_rate - threshold) / (1 - threshold))`, clamped to `[0.0, 1.0]`. Thresholds `>= 1.0` score as non-penalized so the linear branch never divides by zero.

The report is diagnostic only. It does not affect reviewer/proposer points, spawning, thresholds, token allocation, or live panel verdicts.

## Output and exit codes

Output headings:

- `# Voter Calibration Report`
- `## Corpus`
- `## Agreement Table`
- `## Voter Severity Scoreboard`
- `## Global Voter Agreement`
- `## Voter Severity Scoreboard`
- `## Chronic Outliers ...`
- `## Missing Vote Table`
- `## Notes`
- Era mode also emits `## Era Boundary`, `## Pre-incentive era`, and/or `## Post-incentive era`.

Exit `0` on success. Exit `2` when the resolved log-root directory is missing.
