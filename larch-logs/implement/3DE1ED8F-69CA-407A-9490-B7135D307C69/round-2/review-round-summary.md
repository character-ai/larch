# Review Round 2

- Mode: `diff`
- 16 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Cap-rollup ambiguous fallback discards partially resolved explicit members
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When `_expand_cap_rollup_records` has explicit stable-id matches in `out` but fallback expansion fails (`len(candidates) != expected`), the ambiguous path returns only `{"bucket": "ambiguous rollup expansion", ...}` and discards already-resolved member rows. Partially recoverable rollups then score zero members (or lose provisional +1 on resolved members) instead of scoring resolved rows and flagging only the remainder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: On ambiguous fallback, keep `out` and append an ambiguous marker (or per-member skip rows). Return ambiguous-only when `out` is empty. Increment `ambiguous rollup expansion` without wiping explicit matches.


### FINDING_2: Legacy stable-id extraction scans full ndjson body without Filed markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When no Filed markers exist, legacy stable-id extraction scans the full ndjson body. An ndjson disposition that mentions `OOS_2` in review prose but only files `OOS_1` can join and score `OOS_2` as filed evidence without a Filed URL/Stable ID contract.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_10: Merged targeted details retain `_larch_degraded_fields`, blocking `stateReason` override
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Merged targeted issue details retain `_larch_degraded_fields` from fallback bulk rows. `_has_not_planned_signal` then ignores a targeted `stateReason: NOT_PLANNED`, so an old-`gh` fallback plus successful `gh issue view` can leave a closed-unfixed OOS issue as `provisional unknown` instead of docking it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: When targeted details include `stateReason`, remove `stateReason` from the degraded field list, or let `__targeted_fetch_ok__` stateReason override degraded bulk metadata.


### FINDING_11: Failed targeted fetch on missing issue still awards provisional reviewer point
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: A missing issue with failed targeted fetch still awards a provisional reviewer point. `classify_oos_issue_fate` returns `provisional: 0` for skipped missing issues, but `int(fate.get("provisional") or 1)` coerces that to `1` when the fetch-failure placeholder dict is truthy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Use an explicit default only when the key is absent, for example `int(fate["provisional"])`, and skip reviewer scoring for the `skipped missing issue` bucket.


### FINDING_13: Main-agent aggregate rollups do not expand to all review-path member blocks
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Main-agent aggregate rollups with one aggregate stable id do not expand to review-path member blocks. For `Aggregated rollup of 3 capped OOS items` with `oos-accepted-main-agent:OOS_1` and member blocks `OOS_1..OOS_3`, filtering keeps only the suffix-matching `OOS_1` block, then emits `ambiguous rollup expansion` instead of scoring all three members.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: For main-agent aggregate fallback, bridge to the unfiled review-path candidate set by expected rollup count or aggregate prose mapping, not only by matching the aggregate stable-id suffix.


### FINDING_14: `oos-issues-created.md` fallback regex-scans arbitrary prose for GitHub URLs
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: The design `oos-issues-created.md` fallback treats any GitHub issue URL in the file as filed-OOS evidence when map/accepted joins produce no rows. `design_oos.py` only accepts whole-line bare URLs; this path uses `_GITHUB_ISSUE_URL_RE.finditer(text)` on the full file. Incidental URLs in comments or prose can create spurious scored rows with `reviewer: unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Mirror `design_oos`: iterate `splitlines()`, accept only stripped lines starting with `http`, or require `OOS_FILE_MAP` / explicit filed-OOS forms. Do not regex-scan arbitrary prose.


### FINDING_15: Design runs skip recursive `oos-accepted-*.md` when `oos-issues-created.md` exists
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: Design runs skip recursive `**/oos-accepted-*.md` whenever `oos-issues-created.md` exists. The plan requires map joins plus recursive accepted markdown. Filed URLs present only in nested design artifacts are omitted from fate scoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: After `_parse_oos_issues_created`, always walk `run_dir.glob("**/oos-accepted-*.md")` and merge blocks with `filed_url`, deduping on `(run_id, artifact_relpath, heading_id)` like implement runs.


### FINDING_16: Cap-rollup fallback omits planned excerpt-based first tier
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: Cap-rollup fallback omits the planned first tier: locating a same-run aggregated-rollup markdown block and mapping excerpt bullets to member blocks. The code jumps to source-key / unfiled-candidate counting. Rollups whose members are only described in pre-cap markdown excerpts may fail fallback and hit ambiguous rollup expansion even when excerpt mapping would resolve them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Implement the excerpt-based tier from the plan before source-key inference: find rollup summary blocks, normalize excerpt titles/bodies, join members via widened `_stable_ids_cover`, then run the exact-count unfiled fallback only if still short.


### FINDING_17: `_stable_ids_cover` too broad when either side lacks `source_key`
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_stable_ids_cover` returns `True` when either side lacks a `source_key`. That is broader than the plan's bare-suffix-only-for-legacy-lookup rule. A namespaced ndjson id can cover-match any block sharing the bare `OOS_N` / `FINDING_N` suffix; with a single cover hit, `_resolve_blocks_for_stable_id` returns one block without setting `ambiguous`, which can attribute the wrong reviewer across rounds/artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Require the ndjson stable id to carry a source prefix before bare-suffix bridging, or treat any bare-suffix cover match without artifact-path citation in the ndjson body as ambiguous (same rule as multi-match direct resolution).


### FINDING_23: `repo` not cleared when `repo_valid` is false after bulk-fetch skip
- **Reviewer(s)**: dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: When repo detection fails, `run_main` sets `repo = ""` and skips targeted enrichment. When detection succeeds but bulk fetch is skipped (`sanitized` empty), `repo_valid` becomes false while `repo` keeps the original value, so `_fetch_filed_oos_issue_details(repo, ...)` can still run against a repo that bulk fetch already refused. That produces predictable per-issue `__fetch_failed__` stubs and extra doomed `gh` traffic instead of cleanly degrading comment fetch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-fate-fetch-output.txt: Clear or gate `repo` whenever `repo_valid` is false (same as the detection-failure path) before candidate collection and targeted fetch.


### FINDING_28: combine-issues SKILL blurs `close-sources` and `close-stale` closure contracts
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/combine-issues/SKILL.md:165` says to always call `close-sources` for "source closures," but the same step documents stale-only closures via `close-stale` with `not planned` comments. That blurs two closure contracts: combination closures must emit `Combined into #<target>` plus `larch:combined-away` marker for fate docking, while stale closures must not. An operator following line 165 during oos-2 could close stale `[OOS]` sources through `close-sources`, writing a false "combined into" marker and misclassifying fate as combined-away instead of closed-unfixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Split the guidance: reserve `close-sources` for post-combination host closures (oos-7), and state explicitly that stale-only closures in oos-2/oos-4 use `close-stale` only and must not carry the combined-away marker.


### FINDING_29: combine-issues SKILL omits machine-readable `larch:combined-away` HTML envelope
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The skill documents a durable `larch:combined-away` marker but not the machine-readable envelope that `python/analyze_issues.py` matches (`<!-- larch:combined-away source=#<source> target=#<target> -->`). Without the HTML comment shape, the documented contract does not match the detector consumers rely on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Document the full two-line close comment: human-readable `Combined into #<target>`, blank line, then the exact HTML comment with `source=#<source>` and `target=#<target>`.


### FINDING_30: `docs/skills.md` mis-scopes `--filed-issue-details-json` to top-level `/analyze-issues`
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The catalog entry mentions offline reanalysis with `--filed-issue-details-json PATH` under `/analyze-issues` without scoping it to the `analyze` subcommand. That conflicts with `.claude/skills/analyze-issues/SKILL.md:41`, which limits the flag to `python/cli.py analyze-issues analyze --json …`. Operators may forward the sidecar flag to `analyze-issues run`, which does not accept it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Mirror the SKILL split: list `--filed-issue-details-json` only on the offline `analyze --json` invocation, not in the top-level `/analyze-issues` arguments line.


### FINDING_31: `docs/voting-process.md` contradicts updated provisional OOS scoring contract
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: `docs/voting-process.md:124` still states that accepted OOS "earns +1" with no provisional qualifier and no fate-adjusted diagnostic split, while the branch updates `skills/shared/voting-protocol.md` and `docs/point-competition.md` to the dual contract (provisional live +1, retroactive `/analyze-issues` docking). Contradictory scoring semantics remain across canonical docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Align the OOS bullet with voting-protocol/point-competition: provisional live +1, fate-adjusted diagnostic report, and an explicit note that `python/voting.py::classify_result` does not inspect issue fate.


### FINDING_32: Runtime competition notices still promise unconditional OOS +1
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: Runtime competition notices in `skills/shared/reviewer-templates.md` and `skills/design/references/plan-review.md` still tell reviewers that panel-accepted OOS "earns +1" unconditionally. The branch updates static scoring docs but not these live prompt surfaces, weakening the scoring-contract boundary. `plan-review.md:32` shares the same stale incentive wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Update competition-notice prose to "provisional +1 at vote time" and add one sentence that `/analyze-issues` may retroactively dock filed OOS to 0 without changing live vote tallies; regenerate any shipped agent outputs if templates are generated.


### FINDING_33: analyze-issues SKILL does not state offline non-network default
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The plan requires stating that offline `analyze --json` stays dump-only unless `--filed-issue-details-json` is supplied. The SKILL documents the sidecar path but never states the non-network default, so the live vs offline architectural boundary is only implied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Add an explicit sentence under the offline block: default offline reanalysis performs no `gh issue view` calls; enrichment requires `--filed-issue-details-json` or a live `run` path.


