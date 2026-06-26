## Goal
Implement issue #5545: [IMPLEMENTING] Add `/voter-calibration` pre/post incentive era segmentation.

## Implementation Plan
## Plan

### Approach

- Keep the current **no-flag path** unchanged.
  - Do not run `gh`.
  - Do not add corpus lines.
  - Preserve today's single report output byte-for-byte.

- Add opt-in CLI flags in `voter-calibration.py`:
  - `--era {all,pre,post}`
  - `--era-since-date YYYY-MM-DD`
  - Require `--era` to enable segmentation.
  - Let `--era-since-date` supply the cutoff only when `--era` is present.

- Resolve the era boundary only in era mode:
  - When `--era-since-date` is present, parse it as UTC midnight (`YYYY-MM-DDT00:00:00Z`) via a local helper that exits **`2`** on malformed input (do not let `_parse_ground_truth_since_date` `SystemExit(1)` leak through unchanged).
  - Otherwise resolve the **larch plugin source repo** once from `plugin_root` (`CLAUDE_PLUGIN_ROOT` when set, else existing `parents[3]` bootstrap), then issue **one** `gh issue view` fetch against that repo:
    - Resolve repo **only** via `git -C <plugin_root> config --get remote.origin.url`.
    - Normalize the URL to `owner/repo` with a **local** `_slug_owner_repo_from_remote_url(url)` helper that copies only the three slug regex lines from `_detect_repo()`'s remote-URL branch (`git@host:` strip, `https://host/` strip, `.git` strip).
    - **Do not call `_detect_repo()`** on the era path; that helper runs unscoped `gh repo view` first and would revive consumer-cwd wrong-repo resolution for #5461.
    - Validate `owner/repo` shape; on any parse failure return `repo_unresolved` and do **not** call `gh`.
    - In `_resolve_incentive_repo`, catch **`FileNotFoundError`** from the `git` subprocess (missing `git` binary) and return `None`/`repo_unresolved` — same degradation contract as `_run_gh_json` for missing `gh`; no traceback.
    - Do **not** use consumer-clone cwd remotes or unscoped `gh repo view` (ambient cwd would resolve the wrong repo when the operator runs from a consumer checkout).
    - If repo resolution fails, degrade to boundary unavailable (do not query the wrong repository).
    - Fetch `number`, `state`, `stateReason`, `labels`, `body`, `closedAt`, `closedByPullRequestsReferences` in that single call (`--repo <resolved>`). The `number` field is required so `_merged_issue_index` can key the payload via `issue_number(issue)` without `KeyError` and without falling back to `_incentive_issue_from_gh` (which omits `closedAt`/labels/body and would break the one-fetch contract).
    - Wrap the `gh issue view` subprocess in a helper that catches **`FileNotFoundError`** (missing `gh` executable) and converts it to the same unavailable-boundary result as non-zero exit or JSON failure; no traceback.
    - Before the shipped predicate, ensure the payload carries the canonical incentive issue number: if `number` is absent or wrong, normalize with `{**payload, "number": GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER}` so the canonical value **wins** over any stub/gh mismatch (never `{"number": ..., **payload}` where payload overwrites).
    - Pass the normalized payload into `_ground_truth_calibration_incentive_shipped(issues=[payload], repo=None)` so no hidden second `gh` fetch via `_incentive_issue_from_gh` can fire when indexing misses or stub number mismatches.
    - When shipped, set boundary from `parse_iso(closedAt)` only.
    - When `closedAt` is missing or unparseable after a shipped pass, treat as boundary unavailable (no fallback to PR `mergedAt`, `updated_at`, or manifest timestamps).
    - When not shipped, `gh` is missing, `git` is missing, `gh` fails, JSON is malformed, repo is unresolved, or boundary datetime is unavailable, render a clear markdown message telling the user to pass `--era-since-date`; exit `0`.
    - Honor `--out` on unavailable-boundary paths.

- Tag files at discovery time.
  - Use `_ground_truth_run_dir(path, panel_kind=...)`.
  - Use `_ground_truth_run_started_at_strict(run_dir)`.
  - Classify `started_at < boundary` as **pre**.
  - Classify `started_at >= boundary` as **post**.
  - Exclude runs with missing or invalid `started_at` from both corpora.
  - Report the excluded unique run count.

- Keep agreement and severity math unchanged.
  - Continue to parse TSV rows with `voter_agreement_rows_from_tsv`.
  - Continue to compute scoreboards with `compute_voter_agreement` and `compute_voter_severity_distribution`.

- Render era mode as segmented markdown with **both** agreement and severity readouts per corpus:
  - Pin exact era slice section headings (same literals in renderer, docs, and harness):
    - `--era all`: emit **`## Pre-incentive era`** then **`## Post-incentive era`** as top-level era delimiters; each era slice must include **`## Agreement Table`** and **`## Voter Severity Scoreboard`** (the pair the scope requires for side-by-side comparison of `High Rate` and `Calibration Score`).
    - `--era pre`: emit **`## Pre-incentive era`** only, with the same **`## Agreement Table`** + **`## Voter Severity Scoreboard`** pair.
    - `--era post`: emit **`## Post-incentive era`** only, with the same pair.
  - Prefer calling existing `_render` per slice and extracting or re-emitting the Agreement Table and Voter Severity Scoreboard sections (omit Global/Chronic Outliers/Missing for era slices unless already present in a thin wrapper); do not ship era mode with severity-only tables.
  - Include resolved repo slug (when auto-detect attempted), boundary source, boundary timestamp, and excluded missing-`started_at` runs.

## Files to modify/create

### UPDATED: `skills/voter-calibration/scripts/voter-calibration.py`

- Add argparse flags for era mode.
- Add `_parse_era_since_date(value) -> datetime`:
  - Accept only `YYYY-MM-DD`.
  - Return UTC midnight.
  - On invalid input, print a clear stderr message and exit **`2`**.
  - If reusing `_parse_ground_truth_since_date`, catch `SystemExit` and re-raise as exit **`2`** with an `--era-since-date`-specific message.
- Add `_slug_owner_repo_from_remote_url(url: str) -> str | None`:
  - Copy only the three remote-URL slug regex transforms from `_detect_repo()` lines 3404–3406 (`git@host:`, `https://host/`, trailing `.git`).
  - Validate `owner/repo` with `re.fullmatch(r"[^/]+/[^/]+", slug)`; return `None` on empty input or invalid shape.
  - **Do not call or import `_detect_repo()`** on the era auto-boundary path.
- Add `_resolve_incentive_repo(plugin_root: Path) -> str | None`:
  - Run `git -C <plugin_root> config --get remote.origin.url`.
  - Catch **`FileNotFoundError`** from missing `git` binary; return `None` (`repo_unresolved`) — same soft-fail as missing `gh`.
  - On subprocess non-zero or empty stdout, return `None`.
  - Normalize via `_slug_owner_repo_from_remote_url`; return `None` on malformed slug.
  - Do **not** call unscoped `gh repo view` or read remotes from consumer cwd.
- Add `_run_gh_json(args: list[str]) -> tuple[int, object | None]` (or equivalent):
  - Invoke `gh` via `subprocess`.
  - Catch **`FileNotFoundError`** and return a sentinel indicating `gh` unavailable (same degradation path as non-zero exit).
  - Catch JSON decode errors and return unavailable.
- Add `_resolve_era_boundary_auto(plugin_root: Path) -> BoundaryResult`:
  - Resolve repo via `_resolve_incentive_repo`.
  - When repo is missing (`repo_unresolved`, including missing `git`), return unavailable.
  - Issue one `gh issue view <GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER> --repo <repo> --json number,state,stateReason,labels,body,closedAt,closedByPullRequestsReferences` through `_run_gh_json`.
  - On `gh` missing (`FileNotFoundError`), non-zero exit, JSON decode failure, or empty payload: unavailable.
  - Normalize payload number: `{**payload, "number": GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER}` when `number` absent or wrong; production fetch must still request `number` in `--json` field list.
  - Run `_ground_truth_calibration_incentive_shipped(issues=[normalized_payload], repo=None)` — **never pass `repo=`** on the prefetched path to block `_incentive_issue_from_gh` fallback.
  - When not shipped: unavailable with shipped reason preserved for messaging.
  - When shipped: `boundary = parse_iso(normalized_payload["closedAt"])`.
  - When `boundary` is `None`: unavailable (`closedAt` missing or unparseable); do not infer from PR refs or `updated_at`.
  - Return structured result: `boundary`, `source` (`explicit-date` | `gh-issue-closedAt`), `repo`, `unavailable_reason`.
- Reuse existing helpers from `python/analyze_issues.py` where practical:
  - `_ground_truth_run_dir`
  - `_ground_truth_run_started_at_strict`
  - `_ground_truth_calibration_incentive_shipped` (with `repo=None` on prefetched path only)
  - `GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER`
  - `parse_iso`
- Add segmented corpus collection that groups discovered TSVs into pre and post buckets keyed by unique run dir.
- Keep the existing `_discover` and `_render` behavior intact for default mode.
- Add era-only rendering helpers that emit per-slice **`## Agreement Table`** and **`## Voter Severity Scoreboard`** under the pinned era headings **`## Pre-incentive era`** / **`## Post-incentive era`** (via full `_render` per slice or a thin extractor over `_render` / shared table builders).
- Preserve `--out FILE` behavior for both normal and era reports (including unavailable-boundary message reports).

### UPDATED: `skills/voter-calibration/scripts/voter-calibration.md`

- Document the new flags.
- Document boundary precedence:
  - explicit `--era-since-date` wins.
  - auto-detect runs only in era mode, only when no explicit date is passed, and only after plugin-source repo resolution succeeds.
- Document repo resolution:
  - sourced from `plugin_root` / `CLAUDE_PLUGIN_ROOT` via `git -C <plugin_root> config --get remote.origin.url` only.
  - slug normalization via local `_slug_owner_repo_from_remote_url` (same regex rules as `_detect_repo()` remote branch, but **no `_detect_repo()` call** and no unscoped `gh repo view`).
  - auto `gh issue view` queries always pass `--repo owner/repo`.
- Document single-fetch auto boundary:
  - one `gh issue view` supplies both shipped predicate and `closedAt` cutoff.
  - the `--json` field list must include `number` (alongside `state`, `stateReason`, `labels`, `body`, `closedAt`, `closedByPullRequestsReferences`).
  - call `_ground_truth_calibration_incentive_shipped(issues=[payload], repo=None)` so no second gh fetch occurs.
  - payload number normalization uses `{**payload, "number": ...}` so canonical #5461 wins.
  - missing or unparseable `closedAt` after shipped gate is boundary unavailable (no PR/`updated_at` fallback).
- Document missing-`gh` and missing-`git` handling: `FileNotFoundError` from either subprocess degrades to boundary-unavailable guidance (exit `0`), not traceback.
- Document malformed `--era-since-date` exit code **`2`**.
- Document missing `started_at` handling.
- Document pinned segmented output headings:
  - era delimiters: **`## Pre-incentive era`** and **`## Post-incentive era`** (exact literals; harness greps between these anchors).
  - per-era subsections: **`## Agreement Table`** and **`## Voter Severity Scoreboard`** for `--era all`, `--era pre`, and `--era post`.
- State that segmentation is diagnostic only.

### UPDATED: `skills/voter-calibration/SKILL.md`

- Extend usage with `--era` and `--era-since-date`.
- Add acceptance readout note covering **both workflows**:
  - **Default (post-ship):** run `--era all` when incentive #5461 is shipped; auto-boundary uses `closedAt` from one scoped `gh issue view`; compare pre vs post **`High Rate`** and **`Calibration Score`** in segmented **`## Pre-incentive era`** / **`## Post-incentive era`** sections, each containing **`## Agreement Table`** and **`## Voter Severity Scoreboard`**.
  - **Override / pre-ship:** run `--era all --era-since-date YYYY-MM-DD` when incentive is unshipped, auto-boundary degrades, or operator wants a manual cutoff.
- Keep the skill thin.
- Do not add main-agent retallying.

### UPDATED: `skills/voter-calibration/scripts/test-voter-calibration.sh`

- Keep all current no-flag assertions.
- Extend the harness Python fixture to write **`manifest.json`** at each synthetic run root (alongside existing TSV paths):
  - `design/run-pre-era/manifest.json` with ISO `started_at` **before** the test cutoff (e.g. `2026-06-25T12:00:00Z`) and a classification TSV containing a distinct voter name (e.g. `pre-era-voter`).
  - `design/run-post-era/manifest.json` with ISO `started_at` **at or after** the cutoff (e.g. `2026-06-26T00:00:00Z`) and a TSV containing `post-era-voter`.
  - one run (e.g. `design/run-missing-started-at/`) with **absent or invalid** `started_at` in `manifest.json` (omit file, empty file, or non-ISO value).
  - Write full TSV paths under each run dir (e.g. `design/<run>/plan-review/round-1/findings-classification.tsv`) so `_ground_truth_run_dir` resolves the same run root that owns `manifest.json`.
- Assert default output remains unchanged for existing expectations.
- Add explicit-boundary era tests:
  - `--era all --era-since-date 2026-06-26`
  - `--era pre --era-since-date 2026-06-26`
  - `--era post --era-since-date 2026-06-26`
- Assert missing `started_at` runs are excluded and counted.
- Assert malformed `--era-since-date` exits **`2`** with a clear message.
- Add bucketing partition assertions using pinned era heading literals:
  - For `--era all`: `awk` between **`## Pre-incentive era`** and **`## Post-incentive era`** (and after the post heading for the post slice) so `pre-era-voter` appears only under the pre section and `post-era-voter` appears only under the post section.
  - For `--era pre`: grep between report start and end that `pre-era-voter` is present and `post-era-voter` is absent under **`## Pre-incentive era`**.
  - For `--era post`: grep that `post-era-voter` is present and `pre-era-voter` is absent under **`## Post-incentive era`**.
- Assert each era report slice includes both **`## Agreement Table`** and **`## Voter Severity Scoreboard`** headings.
- Add a no-`gh` unavailable-boundary test that **shadows only `gh`** (wrapper script or PATH stub) while keeping real `git` on PATH so repo resolution runs and the missing-`gh` `FileNotFoundError` branch in `_run_gh_json` is actually exercised; assert exit `0`, boundary-unavailable guidance, and no traceback.
- Add a no-`git` unavailable-boundary test that **shadows only `git`** (wrapper script or PATH stub) while keeping a fake `gh` available on PATH, so `_resolve_incentive_repo`'s `FileNotFoundError` branch is exercised before any `gh issue view`; assert exit `0`, boundary-unavailable guidance, and no traceback (and that fake `gh` was not invoked for issue fetch when repo resolution fails first).
- Add a fake-`gh` success test that stubs:
  - repo resolution succeeding for `plugin_root` via `git -C` remote parse (no `gh repo view`).
  - one `gh issue view` returning shipped-shaped JSON with `number`, `closedAt`, and the other required fields.
  - assert the production `--json` field list includes `number` (not only a stub that happens to supply it).
  - assert boundary source and timestamp appear in output.
- Add fake-`gh` shipped-but-missing-`closedAt` test:
  - shipped predicate passes (include `number` in stub payload).
  - `closedAt` absent.
  - assert boundary-unavailable guidance and exit `0`.
- Add repo-unresolved test: set **`CLAUDE_PLUGIN_ROOT`** to a temp plugin tree **without** a usable `remote.origin.url` (or equivalent stub where `git -C` returns empty/malformed remote); assert boundary-unavailable **without invoking `gh`** (wrap/stub `gh` to fail if called).

### MAY_UPDATE: `skills/voter-calibration/scripts/test-voter-calibration.md`

- Update only if the harness gains new named coverage bullets.
- Mention era segmentation; pinned era delimiters **`## Pre-incentive era`** / **`## Post-incentive era`**; per-era Agreement Table + Voter Severity Scoreboard headings; pre/post partition `awk`/grep between pinned anchors; synthetic **`manifest.json`** `started_at` fixtures at run roots; missing `started_at`; plugin-root-only repo resolution via local slug helper (no `_detect_repo()` / no unscoped `gh repo view`); single-fetch boundary with `repo=None` shipped call and canonical number inject order; missing `closedAt` degradation; missing-`gh`/`git` `FileNotFoundError` handling (separate gh-only and git-only shadow tests); malformed-date exit `2`; `CLAUDE_PLUGIN_ROOT` temp-tree repo-unresolved isolation; and boundary fallback coverage.

## Edge cases

- **Boundary date with no time:** treat `YYYY-MM-DD` as `YYYY-MM-DDT00:00:00Z`.
- **Run exactly at boundary:** classify as post-incentive.
- **Multiple TSVs in one run:** count one excluded missing-`started_at` run once.
- **Unsupported TSV in era mode:** keep unsupported-file accounting for dated runs.
- **Missing `gh` executable:** catch `FileNotFoundError` in `_run_gh_json`; produce boundary-unavailable markdown guidance, not a traceback; exit `0`.
- **Missing `git` executable:** catch `FileNotFoundError` in `_resolve_incentive_repo`; return `repo_unresolved`; same unavailable-boundary path; exit `0`.
- **Unshipped incentive issue:** produce the boundary-unavailable path.
- **Shipped issue without parseable `closedAt`:** boundary unavailable; suggest `--era-since-date`; exit `0`.
- **Repo unresolved from plugin root:** boundary unavailable without querying incentive issue #5461 on a wrong repo.
- **`gh` payload missing/wrong `number`:** normalize with `{**payload, "number": GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER}` before shipped call; production fetch requests `number`.
- **Passing `repo=` with prefetched payload:** would enable `_incentive_issue_from_gh` fallback and break one-fetch contract; always use `repo=None` on prefetched path.
- **`--out` with unavailable boundary:** write the message report to the output file and print `REPORT_FILE=...`.
- **Harness without `manifest.json` at run root:** every run lacks strict `started_at`; all era runs excluded; partition greps fail; prevented by explicit fixture writes.

## Failure modes

- A malformed explicit date should fail via argparse-style exit **`2`** with a clear message (not exit `1` from reused since-date helper).
- A missing `gh` binary should degrade to boundary unavailable (not `FileNotFoundError` traceback).
- A missing `git` binary during repo resolution should degrade to boundary unavailable (not `FileNotFoundError` traceback).
- A malformed `gh` JSON response should degrade to boundary unavailable.
- A `gh` response that says the issue is closed without PR refs should degrade to boundary unavailable via the shipped predicate.
- A shipped-shaped payload without parseable `closedAt` should degrade to boundary unavailable; do not guess from PR refs or `updated_at`.
- Calling `_detect_repo()` on the era path would run unscoped `gh repo view` and fetch wrong #5461 from consumer cwd; prevented by local `_slug_owner_repo_from_remote_url` only.
- Passing `repo=` into `_ground_truth_calibration_incentive_shipped` with prefetched payload enables hidden second gh fetch via `_incentive_issue_from_gh`; prevented by `repo=None`.
- Wrong dict spread order `{"number": ..., **payload}` lets stub wrong numbers win and trigger fallback; prevented by `{**payload, "number": ...}`.
- Era rendering that omits `## Agreement Table` per slice would fail scope and harness greps.
- Implementer-chosen era section titles diverging from harness `awk`/grep delimiters would cause flaky partition tests; prevented by pinning **`## Pre-incentive era`** / **`## Post-incentive era`** in renderer, docs, and harness.
- Wrong run-dir bucketing (basename vs `_ground_truth_run_dir`) could merge or swap corpora; prevented by partition greps on distinct synthetic voter names with manifest-backed `started_at`.
- A run manifest with only `updated_at` should not qualify for era placement.
- Repo-unresolved test without `CLAUDE_PLUGIN_ROOT` isolation would never fail against real larch checkout; prevented by temp plugin tree setup.
- Missing-`git` branch untested while only missing-`gh` is shadowed would allow traceback regressions; prevented by separate git-only PATH shadow test.

## Testing strategy

- Run the focused harness:
  - `make test-voter-calibration`
- Run the repository lint target:
  - `make lint`
- Because a Python file changes, also run:
  - `make py-lint`
  - `make py-test`

## Acceptance

- `/voter-calibration --era all` segments the committed-log corpus into pre- and post-incentive eras and renders both an `## Agreement Table` and a `## Voter Severity Scoreboard` per era, so panel `High Rate` and `Calibration Score` are directly comparable across the incentive boundary.
- `--era pre` / `--era post` filter to a single era; `--era-since-date YYYY-MM-DD` sets a deterministic boundary that overrides auto-detection.
- The default (no `--era`) invocation is unchanged and byte-stable; every existing `test-voter-calibration.sh` assertion still passes.
- Auto-boundary degrades cleanly to a "pass `--era-since-date`" message with exit `0` (no traceback) when `gh` or `git` is missing, the repo is unresolved, the incentive issue is unshipped, or `closedAt` is unparseable.
- Runs whose `manifest.json` lacks a parseable `started_at` are excluded from both eras and counted in the report.
- `make test-voter-calibration && make lint && make py-lint && make py-test` all pass.

diff_lines: 445

## Test plan
(no test plan section in plan-file)
