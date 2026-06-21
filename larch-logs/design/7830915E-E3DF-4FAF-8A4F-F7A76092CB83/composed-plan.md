## Plan

## Approach

Implement a report-only, retroactive OOS reconciler in `python/analyze_issues.py`.

Keep `python/voting.py::classify_result` and live OOS scoring unchanged. Accepted OOS still earns provisional `+1` at vote time.

Add a new `## Fate-adjusted OOS Scoring` section to `/analyze-issues` output. It should:

- Scan committed `larch-logs/{design,implement}/` evidence.
- Find filed OOS issue URLs and explicit legacy filed-issue references.
- Join each filed issue to the current GitHub issue dump fetched by `/analyze-issues`.
- Enrich only filed OOS candidate issues with targeted `gh issue view` data when the live path has a repo.
- Classify the issue fate.
- Report provisional points, fate-adjusted points, and docked counts per reviewer.

Use this fate policy:

- **Open issue**: keep provisional `+1`.
- **Closed by PR**: keep `+1` when `closedByPullRequestsReferences` is non-empty.
- **Closed unfixed**: dock to `0` when `stateReason` is `NOT_PLANNED`, or labels/body indicate wontfix or not planned.
- **Combined away**: dock to `0` when a combined-away marker or legacy `Combined into #N` close comment is present.
- **Closed ambiguous**: leave provisional and report as unknown, rather than docking without evidence.

Teach `/combine-issues` to write a durable combined-away marker in the close comment for future source closures. Preserve the human-readable `Combined into #<target>` text.

Suggested marker:

`<!-- larch:combined-away source=#<source> target=#<target> -->`

Keep the bulk `gh issue list` fetch lean. Add `stateReason` and `url` to the list JSON when supported. Do **not** bulk-fetch `comments` on the full issue list.

After log evidence collection, dedupe filed OOS issue numbers and fetch full per-issue classification fields only for that candidate set via `gh issue view` using the pattern from `python/issue_create.py`.

Targeted view fields:

- `number`
- `title`
- `body`
- `state`
- `url`
- `closedAt`
- `stateReason`
- `labels`
- `closedByPullRequestsReferences`
- `comments`

Merge view results into an in-memory issue index keyed by number before fate classification. If targeted issue fetch fails for an issue, classify from bulk issue data first. Treat combined-away as unknown unless another marker is present. Record per-issue fetch failures in a degraded bucket and continue the overall `/analyze-issues` run.

Do not rewrite committed `larch-logs/*`. Do not add a persistent reviewer ledger. Do not auto-commit anything.

### Shared report assembly and `filed_issue_details` handoff

`filed_issue_details` is an in-memory dict and cannot cross the `main(analyze_args)` argv-only boundary by itself. Use one shared report-assembly path for both live and offline entry points.

Add a shared helper, for example `_build_analyze_report(issues, *, log_root, filed_issue_details, repo=None) -> str`, that:

- Calls existing section builders in order.
- Appends `fate_adjusted_oos_scoring(...)` output after `reviewer_effectiveness()`.
- Wraps fate-section assembly in `try/except`; on failure, print a short warning and continue with the legacy sections only.

Wire entry points as follows:

- **`run_main` (live `/analyze-issues`)**: resolve repo from `--repo` or existing detection; call `fetch_main`; scan `log_root`; dedupe filed OOS issue numbers from evidence; call `_fetch_filed_oos_issue_details` only when repo and filed evidence exist; pass the merged `filed_issue_details` dict directly into `_build_analyze_report`; print the returned report.
- **`main()` / `analyze --json`**: load issues from `--json` or caller-supplied dump path; load `filed_issue_details` from an optional sidecar when present; otherwise use `{}`; call `_build_analyze_report` with `filed_issue_details={}` on normal offline reanalysis unless the caller supplied a sidecar.

Add explicit argv handoff for the offline/live split:

- `--log-root PATH` forwarded through `analyze_args`.
- `--filed-issue-details-json PATH` optional; when present, `main()` loads a JSON object `{ "<issue_number>": { ...view fields... } }` before fate scoring.
- `run_main` writes that sidecar to a temp file only when it needs to delegate through `main(analyze_args)`; prefer calling `_build_analyze_report` directly from `run_main` so live runs do not depend on temp-file round-tripping unless the existing `main()` dispatch is unavoidable.

Offline `analyze --json` must remain dump-only by default: no targeted `gh issue view` unless `filed_issue_details` is explicitly supplied via sidecar or direct helper call.

Explicitly append the fate section in `main()` stdout assembly: after `reviewer_effectiveness`, join `fate_adjusted_oos_scoring(...)` via `_build_analyze_report`; do not leave fate scoring as dead code reachable only from a private helper.

### Repo resolution and offline reanalysis

Add `--repo OWNER/REPO` to `parse_args`, defaulting to auto-detect on live runs.

Add `--log-root PATH` to `parse_args`, defaulting to `larch-logs`.

Add `--filed-issue-details-json PATH` to `parse_args` as optional input for offline or test harnesses.

Keep offline JSON reanalysis non-network by default:

- `run_main` is the live `/analyze-issues` path. It resolves repo, fetches the main issue dump, scans logs, fetches targeted filed-OOS issue details when evidence and repo are available, and passes the merged details into `_build_analyze_report`.
- The offline `analyze --json` path reuses the same scoring code with `filed_issue_details={}` unless `--filed-issue-details-json` is set. It must not silently become network-dependent.
- If repo detection fails on the live path, render the fate section from the issue dump only, mark targeted comment fetch as unavailable, and continue.

Add tests that `run_main` forwards `--repo` and `--log-root`, scans logs, dedupes filed OOS issue numbers, invokes targeted fetch only when filed OOS evidence exists, and passes enriched details into the shared report builder without requiring duplicate fetch logic outside `main()` / `run_main`.

### Stable ID normalization

Production `oos-issues.ndjson` rows use artifact-prefixed stable ids from `oos_filer._stable_identifier`, for example:

- `oos-accepted-review:OOS_1`
- `oos-accepted-main-agent:OOS_1`
- `oos-accepted-review:<16-char-hash>`

Same-run collisions are possible when multiple artifacts each carry `### OOS_1:` under different source keys. Multiple rounds can also reuse the same heading id.

Reuse `oos_filer._stable_source_key` and `_stable_identifier(title, body, source_key=...)` for hash alias generation. Do **not** delegate FINDING joins to unmodified `oos_filer._issue_covers_stable_id` alone. Its existing bare suffix logic may only match `OOS_\d+`.

Add analyze-local cover helpers, or a small shared public matcher in `oos_filer.py` if the implementer prefers one source of truth:

- `_bare_oos_item_suffix(stable_id) -> str | None` matching both `OOS_\d+` and `FINDING_\d+` after an optional `source_key:` prefix.
- `_stable_ids_cover(issue_stable_id, block_lookup_keys) -> bool` applying source-key rules equivalent to `oos_filer._issue_covers_stable_id`, but using the widened suffix matcher and block index keys below.

When indexing accepted markdown blocks, compute:

- `heading_id`: bare `OOS_N` or `FINDING_N` from the `###` heading.
- `canonical_stable_id`: `f"{source_key}:{heading_id}"` when heading id is present.
- `hash_stable_id`: `oos_filer._stable_identifier(title, body, source_key=source_key)` for ndjson hash joins.
- `artifact_relpath`: path relative to the run directory, for example `round-1/oos-accepted-review.md`.

Index each block under all of:

- namespaced heading key, `source_key:OOS_N` or `source_key:FINDING_N`;
- hash alias, `source_key:<digest>`;
- secondary bare heading suffix, `OOS_N` or `FINDING_N`, only for legacy lookup when source key is known on the ndjson side;
- round-qualified key, `(artifact_relpath, heading_id)`, for disambiguation.

When matching ndjson `Stable ID` lines to blocks, try hash alias, namespaced heading id, then widened cover logic. When a bare legacy id matches multiple same-run blocks across rounds or artifacts, do not pick arbitrarily. Prefer the match whose `artifact_relpath` is cited in ndjson body or path evidence when present. Otherwise mark reviewer attribution `unknown` and keep scoring by stable id or URL when possible, or skip with an `ambiguous_stable_id` bucket.

### Log evidence model

Evidence collection is run-scoped for implement logs and design-run-scoped for design logs.

1. **Per run directory** under `log_root/{design,implement}/*/`:

   - Recursively collect `**/oos-accepted-*.md`.
   - Read run-root `oos-issues.ndjson` and `oos-issues-created.md` when present.

2. **Within each implement run directory**, join round markdown to ndjson before scoring:

   - Parse accepted blocks from `**/oos-accepted-*.md` with `source_key = path.stem` and `artifact_relpath` relative to the run root.
   - Build block index keyed by hash alias, namespaced heading id, round-qualified `(artifact_relpath, heading_id)`, plus secondary bare-suffix keys for legacy lookup.
   - For each `oos-issues.ndjson` record, parse `Stable ID` lines, `Filed URL`, `Filed as #N`, and explicit legacy `Filed OOS issue #N` or `Filed OOS issue: <url>` body forms.
   - Do **not** treat arbitrary bare `#N` references as filed OOS issue evidence.
   - When `Stable ID:` lines are absent, extract cited `OOS_N` or `FINDING_N` tokens from disposition prose, markdown table cells, and bullet excerpts in the filed section only. Join each extracted id to same-run markdown blocks via widened cover logic and round/path disambiguation.
   - Attach each ndjson stable id to the matching accepted block's `Reviewer` or `Reviewer(s)` from the same run when unambiguous.
   - Map `oos-accepted-main-agent` stable ids with prefix `oos-accepted-main-agent:OOS_N`, or bare `OOS_N` matched only through main-agent source rules, to reviewer label `Main agent` when no round markdown block exists.

3. **Cap-rollup expansion** for implement runs:

   - Expand only when `_is_cap_rollup_record(record)` is true.
   - Treat a record as cap-rollup when ndjson title or body indicates `Aggregated rollup`, or when the record body or `Stable ID` lines explicitly cite member `OOS_N`, `FINDING_N`, or namespaced stable ids.
   - First fan out through explicit stable-id citations and persisted rollup prose excerpt lists.
   - Resolve rollup members with widened `_stable_ids_cover` / `oos_filer._issue_covers_stable_id` semantics, not strict `source_key` stem equality alone. This must bridge aggregate ids such as `oos-accepted-main-agent:OOS_1` to member blocks under `round-*/oos-accepted-review.md`.
   - If the record title matches `Aggregated rollup of N capped OOS items` and explicit citations recover fewer than `N` member rows, use a fallback.
   - Fallback order:
     - Prefer a same-run accepted markdown block whose title is itself an aggregated rollup. Map its excerpt bullets to member blocks by normalized title/body when possible, again using widened cover logic across source keys.
     - Otherwise infer `source_key` from the aggregate stable id when present, select same-source accepted blocks that lack their own inline `Filed URL`, order by `artifact_relpath` then heading number, and take up to `N` distinct `(artifact_relpath, heading_id)` blocks **only when the unfiled same-source candidate count is exactly `N`**. If more than `N` unfiled same-source candidates exist, emit `ambiguous_rollup_expansion` and do not guess by taking the first `N`.
     - If no source key can be inferred, select up to `N` unfiled accepted blocks across the run only when the candidate count is exactly `N`; otherwise mark the rollup expansion ambiguous.
   - Docking the rollup issue zeros adjusted points for every expanded member row.
   - Do **not** fan out a non-rollup single filed URL to every unattached same-run block.

4. **Design runs** do not use the ndjson join path.

   - Parse `oos-issues-created.md` and `oos-accepted-design.md` at the design run root.
   - Also parse recursive `oos-accepted-*.md` if present.
   - Join `OOS_FILE_MAP\t<N>\t<url>` rows to `### OOS_N:` blocks in `oos-accepted-design.md` using `design_oos._block_range` semantics, mirrored or imported.
   - Prefer block `Reviewer` or `Reviewer(s)` and inline `Filed URL` when present.
   - Fall back to map URL only when block fields are absent.

5. **Scoring unit**:

   - Emit one score record per distinct OOS item identity when available.
   - Primary implement dedupe key: `(run_id, artifact_relpath, heading_id)` when heading id is known.
   - Primary hash key: `(run_id, hash_stable_id)` when ndjson cites hash stable id.
   - Secondary key: `(run_id, canonical_stable_id)` only when unambiguous within the run.
   - Fallback key: `(reviewer_label, issue_number)` when URL is absent but an explicit filed issue number was parsed.
   - Last resort: `(reviewer_label, issue_url)` for URL-only legacy evidence without stable id.
   - Multiple canonical stable ids sharing one filed URL each receive the joined issue fate independently.

6. **Reviewer attribution**:

   - Split `Reviewer` or `Reviewer(s)` with `python/voting.py::tokenize_finding_reviewers`, or `grow_attribution_labels` over known reviewer labels mined from the run.
   - Emit one provisional point row per reviewer token before item-level dedupe.
   - Treat comma-lists like live OOS scoring. Each co-proposer gets `+1` for the same filed item.

## Files to modify/create

### UPDATED: python/analyze_issues.py

Add small helpers near the existing reviewer analysis code:

- `extract_issue_number_from_url(url: str) -> int | None`
- `extract_filed_issue_number_from_text(text: str) -> int | None`
- `issue_labels(issue) -> set[str]`
- `issue_comments(issue) -> list[str]`
- `has_combined_away_marker(issue) -> bool`
- `classify_oos_issue_fate(issue) -> dict`
- `_bare_oos_item_suffix(stable_id: str) -> str | None`
- `_canonical_stable_id(source_key: str, bare_id: str) -> str`
- `_hash_stable_id(title: str, body: str, source_key: str) -> str`
- `_stable_ids_cover(issue_stable_id: str, block_keys: set[str]) -> bool`
- `_parse_oos_accepted_blocks(path: Path, *, run_dir: Path) -> list[dict]`
- `_index_accepted_blocks_by_stable_id(blocks) -> dict[str, dict]`
- `_extract_legacy_stable_ids_from_ndjson_body(body: str) -> list[str]`
- `_is_cap_rollup_record(record: dict) -> bool`
- `_expand_cap_rollup_records(run_dir, ndjson_record, blocks, indexed_blocks) -> list[dict]`
- `_parse_oos_issues_created(path: Path, *, accepted_design_path: Path | None) -> list[dict]`
- `_parse_oos_issues_ndjson(path: Path) -> list[dict]`
- `_join_implement_run_records(run_dir: Path) -> list[dict]`
- `_fetch_filed_oos_issue_details(repo: str, issue_numbers: set[int]) -> dict[int, dict]`
- `_load_filed_issue_details_json(path: Path | None) -> dict[int, dict]`
- `iter_filed_oos_records(log_root: Path) -> list[dict]`
- `fate_adjusted_oos_scoring(issues, log_root, *, filed_issue_details: dict[int, dict]) -> tuple[str, dict]`
- `_build_analyze_report(issues, *, log_root, filed_issue_details, repo=None) -> str`

`extract_filed_issue_number_from_text` must only parse explicit filed-OOS evidence:

- `Filed URL: <url>`
- `Filed as #N`
- `Filed OOS issue #N`
- `Filed OOS issue: <url>`
- markdown table URL cells that are part of filed-OOS rows

It must not parse arbitrary bare `#N` references from finding prose.

`issue_comments(issue)` must normalize `gh issue view` comment shape:

- Accept `comments` as a list of objects.
- Return `str(comment.get("body") or "")` for dict comments.
- Ignore non-dict entries.
- Also tolerate pre-normalized string comments in tests or legacy merged data.

`_fetch_filed_oos_issue_details` should call `gh issue view <number> --repo <repo> --json number,title,body,state,url,closedAt,stateReason,labels,closedByPullRequestsReferences,comments`.

Merge targeted view records over bulk list records by issue number before fate classification.

Implement tolerant parsers as in the original plan for accepted markdown, design map files, and ndjson records.

**`fetch_main` update (mandated, not optional)**:

- First attempt `gh issue list` with expanded JSON fields including `url` and `stateReason` alongside the existing field set.
- On non-zero exit, retry once with the current supported field set only: `number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences`.
- Record degraded availability for `stateReason` and `url` when the retry path is used so `classify_oos_issue_fate` can degrade not-planned detection without aborting `run_main`.

**Main wiring**:

- Add `--log-root PATH`.
- Add `--repo OWNER/REPO`.
- Add `--filed-issue-details-json PATH` optional loader for offline/test paths.
- Resolve repo in `run_main` from `--repo` or repo detection.
- Scan logs before targeted detail fetch so the filed issue candidate set is known.
- Fetch targeted filed OOS issue details only for deduped filed issue numbers and only on live paths with a repo.
- Pass `filed_issue_details` into `_build_analyze_report` from `run_main` directly.
- In `main()`, load optional `--filed-issue-details-json`, default to `{}`, and call `_build_analyze_report` so the fate section is appended after `reviewer_effectiveness()` in the printed report join list.
- Keep offline JSON reanalysis dump-only unless the caller explicitly supplies targeted details.

Render a concise section after `Reviewer/Persona Tables`:

- Overall totals: provisional, adjusted, docked.
- Reviewer rows sorted by adjusted score descending, then reviewer label.
- Fate buckets:
  - kept by PR
  - provisional open
  - provisional unknown
  - docked closed-unfixed
  - docked combined-away
  - skipped missing issue
  - ambiguous stable id
  - ambiguous rollup expansion
  - degraded comment fetch

Keep the section diagnostic. It must not alter `reviewer_effectiveness()` or the executive summary unless the implementer chooses to mention the new section briefly.

If fate section assembly fails inside `_build_analyze_report`, print a short warning and continue the rest of the report.

### UPDATED: python/oos_filer.py

Add a small shared helper used by analyze:

- `_bare_oos_item_suffix(stable_id: str) -> str | None` matching `OOS_\d+` and `FINDING_\d+`.

Optionally refactor `_issue_covers_stable_id` internals to call the widened suffix helper for OOS paths.

Keep filing behavior unchanged.

### UPDATED: python/test_analyze_issues.py

Add focused tests with temp `larch-logs` fixtures.

Cover fate buckets with mocked issue dump and mocked per-issue view details:

- Open filed OOS issue keeps `+1`.
- Closed issue with `closedByPullRequestsReferences` keeps `+1`.
- Closed issue with `stateReason: NOT_PLANNED` docks to `0`.
- Closed issue with combined-away marker in `comments[].body` docks to `0`.
- Legacy `Combined into #N` in `comments[].body` docks to `0`.
- `issue_comments` extracts `body` from `gh issue view` comment objects.
- Targeted comment fetch failure leaves combined-away unknown with degraded bucket note.
- Filed issue absent from bulk list but present in targeted view can still classify PR-closed, NOT_PLANNED, labels, and comments.
- Arbitrary bare `#N` in finding prose is not treated as filed OOS evidence.

Cover log layout, join, dedup, stable-id normalization, and wiring:

- Nested `round-1/oos-accepted-review.md` is found via recursive walk.
- Namespaced join yields reviewer-specific provisional and adjusted totals.
- Bare ndjson `Stable ID: OOS_1` joins only when source-key rules match widened cover behavior.
- Same-run collision fixture attributes reviewers independently and does not cross-match wrong artifacts.
- Same-id across rounds fixture uses `(artifact_relpath, heading_id)` and does not collapse blocks.
- Legacy `### FINDING_3: [OUT_OF_SCOPE]` block joins namespaced, bare, and hash stable ids.
- Comma-separated `Reviewer(s): a, b, c` emits three reviewer rows.
- Two distinct canonical stable ids sharing one `Filed URL` score independently.
- Duplicate identical `(run_id, artifact_relpath, heading_id)` evidence counts once.
- Legacy ndjson body `Filed OOS issue #3435` joins by issue number without URL.
- Legacy ndjson body listing multiple `FINDING_N` or `OOS_N` references under one filed URL yields one row per cited id.
- Cap-rollup with explicit cited member ids expands to multiple scored rows.
- Cap-rollup with title `Aggregated rollup of 2 capped OOS items`, one aggregate stable id, and same-run pre-cap markdown blocks expands via fallback to two unfiled same-source blocks when candidate count is exactly 2.
- Cap-rollup with `N=3` and eight same-source unfiled candidates emits `ambiguous_rollup_expansion` and does not expand.
- Main-agent aggregate stable id `oos-accepted-main-agent:OOS_1` expands to review-path markdown member blocks via widened cover logic.
- Docking a cap-rollup issue zeros all expanded members.
- Non-rollup single-URL ndjson with multiple unattached same-run blocks does not fan out to every block.
- Ambiguous rollup fallback reports `ambiguous_rollup_expansion` rather than guessing.
- Design `OOS_FILE_MAP` row joins `### OOS_N:` reviewer from `oos-accepted-design.md`.
- Design bare URL line is parsed when map join absent.
- Missing issue numbers/URLs are skipped and reported.
- `run_main` forwards `--log-root`.
- `run_main` forwards `--repo`.
- `run_main` invokes mocked targeted fetch when filed OOS evidence exists and passes enriched details into `_build_analyze_report` / printed output.
- `main()` appends the fate-adjusted section after reviewer effectiveness in stdout output.
- Offline JSON reanalysis does not invoke targeted fetch by default.
- `fetch_main` retries without `stateReason`/`url` when expanded list JSON fails.

Keep existing fixture assertions stable. Add only targeted new assertions for the new section.

### UPDATED: python/test_oos_filer.py

Add regression tests for widened `_bare_oos_item_suffix` and FINDING cover behavior if helpers are added to `oos_filer.py`.

### UPDATED: python/combine_issues.py

Update `_close_issue_with_retry(issue, repo, combined)` to include the machine-readable marker in the `--comment` body.

Keep the existing readable line first:

`Combined into #<combined>`

Then add a blank line and the marker:

`<!-- larch:combined-away source=#<source> target=#<combined> -->`

Do not change closure sequencing, retry behavior, or eligibility logic.

### UPDATED: python/test_combine_issues.py

Update close-command expectations to include the new multi-line close comment.

Add one assertion that the comment includes both:

- `Combined into #99`
- `larch:combined-away source=#<source> target=#99`

Keep existing retry and partial-close tests intact.

### UPDATED: .claude/skills/combine-issues/SKILL.md

Document that `close-sources` writes a durable combined-away marker in each source issue close comment.

State that prompt prose must still call `python/cli.py combine-issues close-sources`. It must not call raw `gh issue close`.

### UPDATED: .claude/skills/analyze-issues/SKILL.md

Document the new fate-adjusted OOS section.

Add `--log-root PATH` to usage and flags.

Add `--repo OWNER/REPO` to usage and flags.

Add `--filed-issue-details-json PATH` for offline/test enrichment when explicitly supplied.

State that the report is diagnostic only and does not mutate logs or live voting scores.

Note that live runs may enrich filed OOS candidates with targeted per-issue `gh issue view` calls. Offline JSON reanalysis should remain dump-only unless explicitly supplied with details.

Note that implement-phase scoring depends on same-run joins between `oos-issues.ndjson` and nested `round-*/oos-accepted-*.md`.

Mention:

- namespaced and hash stable ids consistent with `oos_filer._stable_identifier`;
- round-qualified dedupe keys;
- cap-rollup expansion for explicit rollups and cited members, including main-agent aggregate ids bridged to review-path markdown;
- fallback expansion only when unfiled candidate count exactly matches parsed rollup `N`;
- design `OOS_FILE_MAP` block joins;
- legacy body citation fallback;
- explicit filed issue references only, not arbitrary bare `#N` mentions.

Note that combined-away detection uses targeted per-issue comment fetch for filed OOS issues only, not bulk list comments.

Note that `fetch_main` retries without optional list JSON fields when older `gh` builds reject them.

### UPDATED: docs/point-competition.md

Update OOS scoring prose:

- Accepted OOS earns provisional `+1` at vote time.
- `/analyze-issues` can report fate-adjusted OOS points.
- Closed-unfixed and combined-away filed OOS issues become `0` in that retroactive report.
- Open OOS issues remain provisional.
- No `-1` retroactive penalty is added.
- The retroactive report is diagnostic and does not change live voting results.

### UPDATED: skills/shared/voting-protocol.md

Update OOS scoring language to distinguish:

- Live voting outcome points.
- Retroactive fate-adjusted reporting.

Explicitly say `python/voting.py::classify_result` remains the live classifier and does not inspect GitHub issue fate.

### MAY_UPDATE: docs/skills.md

Update the `/analyze-issues` generated or catalog prose only if this file is manually maintained in this repo.

Add the fate-adjusted OOS section, `--log-root`, `--repo`, and optional `--filed-issue-details-json`.

### MAY_UPDATE: docs/linting.md

Update the `make test-analyze` row only if the new tests materially change the harness description.

## Edge cases

- Historical OOS records may lack `Filed URL`. Join by explicit `Filed OOS issue #N` or `Filed as #N` when present. Otherwise skip and count in a skipped bucket.
- Arbitrary issue mentions like `#4683` in finding prose must not create filed OOS evidence.
- Historical source issues may have no comments in the targeted view fetch. Treat combined-away as unknown unless `stateReason`, labels, body, or legacy close text provides another signal.
- A closed issue can have no PR link and no not-planned signal. Keep it provisional and report `closed_unknown`.
- Multiple log records can point at the same filed issue. Score each distinct item identity separately. Dedupe only exact duplicate evidence keys.
- A single filed issue may aggregate several OOS items. Count each canonical or round-qualified item once per reviewer token derived from its accepted block.
- Security-held OOS without a public issue URL must not be scored as filed OOS.
- Legacy code-review OOS blocks use `FINDING_N` ids. ndjson stable ids may be hash-based. Joins must use hash alias and widened suffix rules, not bare suffix equality alone.
- `oos-accepted-main-agent` items use `Main agent` when ndjson stable id matches main-agent source rules and no round markdown block exists; rollup expansion must still reach review-path member blocks when widened cover applies.
- Cap-rollup ndjson may list one aggregate stable id while round markdown retains many member blocks. Fallback expansion must recover the parsed rollup count only when candidates are unambiguous; excess same-source unfiled blocks must not be truncated heuristically.
- Same-run `OOS_1` in multiple artifacts or rounds must never share reviewer attribution through stem-only or bare-suffix-only indexing.
- Design `oos-issues-created.md` map rows without `oos-accepted-design.md` blocks still contribute URL fate rows with reviewer `unknown`.
- Filed OOS issue numbers absent from the bulk issue list can still classify if targeted view fetch succeeds.
- Offline dump-only analysis may classify fewer fates because comments and missing issue numbers are unavailable.
- `filed_issue_details` must not be dropped when `run_main` delegates through `main()`; use direct `_build_analyze_report` or an explicit JSON sidecar loader in `main()`.

## Failure modes

- If `gh issue list --json stateReason,url` is unsupported, `fetch_main` retries without those fields and records degraded `stateReason`/`url` availability for fate classification instead of aborting the live report.
- If repo detection fails, skip targeted `gh issue view` enrichment, report degraded comment fetch unavailable, and continue.
- If targeted `gh issue view` fetch fails for some filed OOS issues, continue with list data, mark those issues `degraded_comment_fetch`, and avoid docking combined-away without evidence.
- If a filed issue appears only in logs and targeted fetch fails, mark it skipped or unknown according to available URL/number evidence.
- If the fate section itself raises inside `_build_analyze_report`, print a short warning and continue the rest of the report.
- If `larch-logs` is missing, render `No filed OOS run-log evidence found.` and continue.
- If an issue URL points outside the fetched repo, skip it and count it as skipped.
- If implement ndjson exists without accepted markdown in the same run, attribute reviewer as `unknown` but still score by stable id or URL when possible.
- If cap-rollup fallback cannot identify member blocks safely, including when unfiled same-source candidates exceed parsed `N`, report `ambiguous_rollup_expansion` and do not guess.

## Testing strategy

Run:

- `make py-lint`
- `make py-test`
- `make test-analyze`
- `make lint`

Also run targeted tests during development:

- `PYTHONPATH=python pytest python/test_analyze_issues.py -q`
- `PYTHONPATH=python pytest python/test_combine_issues.py -q`
- `PYTHONPATH=python pytest python/test_oos_filer.py -q` if oos_filer helpers are added

Do not run or require live GitHub calls in unit tests. Mock issue dumps, per-issue view results, repo detection, `fetch_main` retry behavior, and combine close runners.

## Acceptance

- `/analyze-issues` output includes a new `## Fate-adjusted OOS Scoring` section after the reviewer/persona tables, reporting provisional points, fate-adjusted points, and docked counts per reviewer.
- Fate policy holds: open or PR-closed filed OOS keeps `+1`; `NOT_PLANNED` / wontfix and combined-away dock to `0`; ambiguous-closed stays provisional.
- `python/voting.py::classify_result` and live OOS `+1` scoring are unchanged (no live-tally behavior diff).
- `/combine-issues` close comments carry the durable `<!-- larch:combined-away source=#<source> target=#<target> -->` marker and preserve the human-readable `Combined into #<target>` line.
- Diagnostic only: no committed `larch-logs/*` TSV is rewritten, no persistent reviewer ledger is added, nothing is auto-committed.
- Offline `analyze --json` stays dump-only unless `--filed-issue-details-json` is supplied.
- `make py-test`, `make test-analyze`, `make py-lint`, and `make lint` pass.

review_status: complete
rounds_completed: 5
diff_lines: 905
