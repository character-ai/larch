# Review Round 1

- Mode: `diff`
- 11 accepted, 7 rejected (6 neutral)

## Accepted Findings

### FINDING_1: Main-agent rollup fallback disables source filtering
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When cap-rollup fallback runs with `source_key == "oos-accepted-main-agent"`, the filter `block.get("source_key") == source_key or source_key == "oos-accepted-main-agent"` matches every unfiled block in the run. If exactly `N` unfiled blocks exist across unrelated artifacts, fallback can pair the wrong blocks and credit the wrong reviewers instead of emitting `ambiguous rollup expansion`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Restrict main-agent rollups to widened-cover matches (review-path members bridged from the aggregate id), or require `len(candidates) == expected` only after that narrowed set; otherwise emit `ambiguous rollup expansion`.


### FINDING_2: Filed OOS fate scoring joins by issue number only and ignores URL repo
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-oos-reconciler-output.txt, dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: Filed OOS evidence stores only the issue number parsed from URLs; `fate_adjusted_oos_scoring` looks up `index.get(parsed_number)` against the analyzed repo dump without validating `owner/repo`. A log URL like `https://github.com/other/repo/issues/42` can be scored against `#42` in the current repo, producing wrong keep/dock totals and wrong reviewer attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Pass normalized repo into fate scoring, parse owner/repo from filed URLs, skip mismatched URL repos, and assume current repo only for number-only filed evidence.
  - From cursor-specialist-edge-cases-output.txt: Parse owner/repo from filed URLs and skip or bucket rows whose repo does not match `--repo`.
  - From codex-specialist-edge-cases-output.txt: Parse owner/repo from filed URLs, pass repo into fate scoring, and skip mismatched repos.
  - From codex-specialist-testing-output.txt: Pass repo into `fate_adjusted_oos_scoring`, validate issue_url owner/repo against it, and skip mismatches.
  - From dyn-oos-reconciler-output.txt: Parse owner/repo from each filed URL (or compare against `run_main`'s resolved `--repo`) and skip/bucket mismatched rows; thread `repo` through to the scorer for that validation.
  - From dyn-gh-fate-fetch-output.txt: Parse owner/repo from filed URLs, compare to the active `--repo` / detected repo, skip non-matching rows into `skipped missing issue` (or a dedicated bucket), and only include matching numbers in `candidate_numbers` for targeted `gh issue view`.


### FINDING_3: Cap-rollup fallback returns partial members instead of ambiguous expansion
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_expand_cap_rollup_records` only emits `ambiguous rollup expansion` when `out` is empty (`elif not out` at line 1003). When explicit stable-id resolution recovers some members but fewer than parsed `N`, and unfiled candidate count is not exactly `N`, the function returns the partial `out` silently. That under-scores docked rollups and violates the plan rule to mark excess-candidate rollups ambiguous instead of guessing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: When expected N is set and recovered rows are fewer than N, require fallback candidates to equal N; otherwise discard partial rows and emit `ambiguous_rollup_expansion`.
  - From cursor-specialist-edge-cases-output.txt: After fallback, if expected > 0 and len(out) < expected, emit ambiguous rollup expansion and do not score partial members.
  - From codex-specialist-edge-cases-output.txt: Return `ambiguous_rollup_expansion` whenever expected N is not safely recovered exactly.
  - From cursor-specialist-testing-output.txt: Treat len(candidates) != expected (including > expected) after explicit recovery as ambiguous; add the plan N=3/eight-candidate fixture test.
  - From codex-specialist-testing-output.txt: When expected is set and fewer than expected members are recovered, only score fallback if it recovers exactly expected safe members; otherwise emit `ambiguous_rollup_expansion`.
  - From dyn-oos-reconciler-output.txt: After the fallback attempt, if `expected > 0` and `len(out) < expected`, return an `ambiguous rollup expansion` row (or merge only the still-missing members when the candidate set is uniquely determined); never return a silently truncated member set.


### FINDING_4: Documented `--filed-issue-details-json` flag not accepted by `run_main`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: `/analyze-issues` usage and skill docs advertise `--filed-issue-details-json`, but `run_main` only registers `--log-root`, `--repo`, and existing run flags. Forwarding the documented flag to `python/cli.py analyze-issues run` fails with argparse unrecognized arguments before analysis starts. The sidecar loader lives on the offline `analyze-issues analyze` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Add the flag to run_main and load or merge the sidecar, or remove it from the run-skill docs and document it only for the offline analyze --json subcommand.
  - From codex-specialist-edge-cases-output.txt: Accept and load the sidecar in run_main, or document the flag only for the offline analyze subcommand.
  - From codex-specialist-testing-output.txt: Add the flag to run_main and load/merge the sidecar, or remove it from run-facing docs and document it only for the offline analyze subcommand.
  - From dyn-scoring-contract-docs-output.txt: Split usage into live vs offline surfaces: keep `--log-root` and `--repo` on `run`, document `--filed-issue-details-json` only for `python/cli.py analyze-issues analyze --json …`, and add a short offline reanalysis example so the two-entry-point contract matches `python/analyze_issues.py`.
  - From dyn-scoring-contract-docs-output.txt: Mirror the SKILL split in `docs/skills.md`: document live flags on `run`, and describe `--filed-issue-details-json` under an explicit offline `analyze-issues analyze` reanalysis path.


### FINDING_5: `_larch_degraded_fields` written on fetch but never consumed during fate classification
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: `fetch_main` stamps `_larch_degraded_fields` on dump items when optional list fields are omitted, but `classify_oos_issue_fate` / `_has_not_planned_signal` never read it. On older `gh` builds where `stateReason` is missing from the bulk dump, a filed OOS issue closed `NOT_PLANNED` only via `stateReason` can stay at provisional +1 instead of docking to 0, with no operator-visible degradation note in the fate section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Read `_larch_degraded_fields` in `classify_oos_issue_fate`/`_has_not_planned_signal` and skip stateReason-based docking when that field is degraded.
  - From dyn-scoring-contract-docs-output.txt: Either consume `_larch_degraded_fields` during fate classification and add a list-fetch degradation bucket/note in the fate section, or tighten the SKILL/docs prose to say degradation is recorded only on the saved JSON dump unless targeted per-issue fetch succeeds.


### FINDING_7: `__fetch_failed__` issue stubs still earn provisional +1 adjusted points
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When targeted `gh issue view` fails and the issue is absent from the bulk dump, `_fetch_filed_oos_issue_details` inserts `{number, __fetch_failed__: True}` into the merged index. `classify_oos_issue_fate` treats that stub as provisional unknown and awards +1 adjusted, even though there is no list data and comments were not fetched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat `__fetch_failed__` stubs without state/closedAt as non-scoring unknown or skipped rather than adjusted +1.
  - From codex-specialist-edge-cases-output.txt: Do not index failure-only details without a bulk issue, or classify them as skipped missing issue with zero points.
  - From dyn-oos-reconciler-output.txt: If `__fetch_failed__` is set and the bulk index had no substantive fields for that number (`state`/`closedByPullRequestsReferences`/etc. missing), skip scoring (or bucket as `skipped missing issue` / degraded-only) instead of applying `provisional unknown` points.


### FINDING_8: Main-agent stable ids can cross-match ordinary review blocks outside rollup expansion
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent stable ids can cross-match ordinary review blocks outside rollup expansion. A main-agent `OOS_1` record can inherit a reviewer from unrelated review `OOS_1` evidence via widened cover logic in ordinary joins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Restrict main-agent bridging to rollup expansion or require source-key equality in ordinary joins.


### FINDING_9: Cap-rollup fallback overwrites explicit stable-id matches when candidate count equals N
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When fallback runs and `len(candidates) == expected`, the code replaces `out` entirely instead of unioning with members already resolved in the stable-id loop. Explicitly matched rows are dropped before scoring, so reviewers on those blocks lose provisional/adjusted credit even though the rollup issue was filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Build fallback rows into a separate list and merge into `out` keyed by `(artifact_relpath, heading_id)`; only use fallback to fill the gap up to `expected`, never overwrite existing members.


### FINDING_10: `_is_cap_rollup_record` heuristic routes non-rollup multi-id records through expansion
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_is_cap_rollup_record` treats any ndjson row with more than one `Stable ID` and rollup-like prose (`capped`, `rollup`, `aggregate`, etc.) as a cap rollup, even when it is a normal multi-id disposition under one filed URL. That routes non-rollup records through `_expand_cap_rollup_records`, which can fan out or fallback-guess members incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Tighten the heuristic to require the `Aggregated rollup` title pattern or explicit rollup member citations before expansion; otherwise use the standard per-stable-id join path in `_join_implement_run_records`.


### FINDING_12: Transient `gh issue list` failures mislabeled as optional-field degradation
- **Reviewer(s)**: dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: `fetch_main` treats any first `gh issue list` non-zero exit as optional fields unsupported, retries with a reduced field set, and stamps `_larch_degraded_fields`. Transient failures (auth blip, rate limit, network timeout) get the same path, so a successful fallback run can be mislabeled degraded and lose `stateReason`/`url` for bulk classification even when the expanded request would have worked on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-fate-fetch-output.txt: Retry the expanded field set once on transient errors before falling back; only set `_larch_degraded_fields` when the expanded request fails with a field-support error (or when the fallback omits fields by design).


### FINDING_13: Live run hard-exits on repo detection or bulk fetch failure
- **Reviewer(s)**: dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: On live `/analyze-issues`, repo detection failure is a hard exit before report assembly, and `fetch_main` failure aborts the whole run. The plan required continuing with list-only fate scoring and marking targeted comment fetch unavailable when repo detection or enrichment is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-fate-fetch-output.txt: When repo detection fails, still render legacy sections plus a fate section from logs and any existing dump/sidecar, with an explicit "targeted comment fetch unavailable" note; when bulk `gh issue list` fails, keep the same partial-report behavior instead of returning exit 1 with no output.


