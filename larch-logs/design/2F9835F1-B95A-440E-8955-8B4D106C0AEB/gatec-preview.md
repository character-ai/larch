## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Extend the existing `/analyze-bugs` coordinator rather than creating a second workflow. Pin each sweep to the synced `origin/main` tip. Enumerate first-parent commits after the saved discovery watermark, or from the prior 48 hours on first use.

Exclude log-only and release commits before ranking. Load ledger-backed chronic zones and rank chronic-zone commits first, then larger first-parent diffs. Sweep at most `--sweep-max` commits and report the remaining count.

Make capped coverage resumable. Persist skipped eligible SHAs in sweep state, advance the discovery watermark only with that pending frontier retained, and prioritize pending work on the next sweep. Mark capped reports as incomplete coverage rather than treating skipped commits as permanently omitted.

Build one bounded evidence bundle per selected commit. Include the first-parent diff, touched files, chronic-zone tags, and a minimal bounded scan for consumers of changed Python symbols. Dispatch the finder once per bundle, ingest its raw JSONL through an executable Python fence, then dispatch a refuter for each queue row emitted by that fence. Treat malformed, missing, rejected, or incomplete agent output as a failed sweep.

Run sweep preparation and executable agent-ingestion fences after prefetch but before the existing ledger and deep stages. The existing Stage 3 report remains the sole final rendering entrypoint, merging the validated sweep artifact with legacy results only after all enabled analysis stages complete. It creates or extends the combined follow-up body for sweep-only survivors, then writes sweep state last.

### UPDATED: python/larch/issue/analyze_bugs.py

- Add frozen sweep domain records for state, pending frontier entries, commits, bundles, findings, refutation results, refuter queue rows, and validated sweep artifacts.
- Define local sweep constants for schema version, default limit `20`, 48-hour initial window, diff caps, symbol and consumer caps, and allowed severity and confidence values.
- Add strict `sweep-state.json` loading beside the repository’s `ledger.jsonl`.
  - Require `last_sweep_sha`, `last_sweep_at`, `schema_version`, and `pending_shas` for the new schema.
  - Validate a unique bounded list of full SHAs in `pending_shas`, strict timestamps, and schema version.
  - Treat an absent file as a first sweep; reject malformed state rather than widening coverage.
  - Write with the existing private atomic JSON helper.
  - Define `last_sweep_sha` as the discovery watermark, while `pending_shas` is the resumable unswept frontier; do not claim that the watermark alone proves all preceding eligible commits were swept.
- Implement `sweep_enumeration`.
  - Pin `origin/main` once and use that exact tip throughout preparation, agent ingestion, and final rendering.
  - Verify both the saved watermark and every pending SHA are reachable from the pinned tip; fail loudly on force-pushed, unrelated, or unreadable state.
  - Enumerate first-parent commits after the saved watermark, or in the 48-hour first-run window.
  - Exclude subjects matching `^chore\(larch-logs\)` or `^Release v`, and commits whose changed paths are all under `larch-logs/`.
  - Combine carried `pending_shas` with newly eligible commits without duplication.
  - For every eligible commit, compute touched paths, diff size, changed symbols, and capped diff from its first-parent range, `MERGE_SHA^1..MERGE_SHA`; fail when the required parent or bounded evidence cannot be read.
  - Load the ledger path and use the existing `build_analytics_view` interface with a synthetic empty-bundle manifest generated after pinning.
  - Derive chronic-zone names from `analytics.chronic_zones`, tag a commit when `_zones_for_files(touched_paths)` intersects those names, and rank chronic-tagged commits first, then descending first-parent diff size, then deterministic history order or SHA.
  - Apply `--sweep-max`; retain every unselected eligible SHA as the pending frontier and report the skipped count.
- Build private per-commit sweep bundles in the active run directory.
  - Include the pinned tip, merge SHA, first-parent base SHA, subject, touched files, chronic tags, capped first-parent diff, and truncation notices.
  - Extract a bounded set of changed Python definitions and constants from the first-parent diff.
  - Use the injected `Runner` for bounded `git grep` consumer discovery, excluding the defining path and recording truncation.
  - Pass bundle paths to agents instead of inlining repository evidence.
  - Write a selected-merge manifest and deterministic bundle-path manifest in the run directory for ingestion identity checks.
- Implement dedicated strict sweep JSONL parsers and executable ingest helpers; do not reuse soft-success ledger ingest semantics.
  - `prepare` emits the pinned tip, selected-merge manifest path, bundle-path manifest, selected count, skipped count, pending SHAs, state path, and fixed raw-result paths under `RUN_DIR`.
  - `ingest-finder` reads only the fixed `RUN_DIR/sweep-finder.jsonl` raw capture and the prepared selected-merge manifest. For non-empty selected work, require the finder’s exact `merge_sha` and `findings` schema.
  - Validate selected SHAs, exact keys, enums, bounded strings, repository-relative files, and finding counts.
  - Reject duplicate merge rows, unknown or foreign SHAs, rejected rows, empty or missing input files when selected work was dispatched, and any missing selected merge.
  - Require `INGEST_ACCEPTED` to exactly match the prepared selected-merge manifest.
  - Write a deterministic `RUN_DIR/sweep-refuter-queue.jsonl`, containing one exact queue row per accepted finding with merge SHA, finding index, and the bounded finding evidence.
  - Emit `REFUTER_QUEUE_PATH`, `REFUTER_QUEUE_COUNT`, `INGEST_ACCEPTED`, and the pinned-tip and selected-manifest identities as machine-readable KVs.
  - When the selected-merge manifest is empty, bypass finder-file parsing and finder dispatch, write an empty refuter queue, and emit accepted count `0`; an absent raw finder file is valid only in this no-work case.
  - `ingest-refuter` reads only `REFUTER_QUEUE_PATH` and the fixed `RUN_DIR/sweep-refuter.jsonl` raw capture. Require exact rows of `{"merge_sha": str, "finding_index": int, "verdict": "survives"|"refuted"}`.
  - Reject missing, empty, duplicate, malformed, foreign, or incomplete refuter results when the queue is non-empty; require the accepted refuter key set to exactly equal the prepared queue key set before writing the validated sweep-result artifact.
  - When the refuter queue is empty, bypass refuter-file parsing and refuter dispatch, treat the empty queue as a successful zero-candidate result, and write the validated artifact without requiring a raw refuter file.
  - Keep only findings whose refuter verdict says the claim survives.
  - Escape or normalize agent-authored text before Markdown rendering.
- Implement `sweep_main(argv) -> int` subphases used by the skill:
  - `prepare` loads state, enumerates commits, writes bundles and manifests, and emits explicit paths and counts.
  - `ingest-finder` hard-validates captured finder JSONL and creates the bounded refutation queue.
  - `ingest-refuter` hard-validates captured refuter JSONL and writes a validated sweep-result artifact.
  - Return non-zero on any partial or invalid coverage; do not render the report or update durable sweep state in any sweep subphase.
- Extend the existing report path to consume a validated sweep-result artifact when present.
  - Preserve the existing Stage 3 report as the only final render after ledger and deep stages complete.
  - Verify the artifact’s pinned tip and selected-manifest identity before merging it with legacy results.
  - Add a `Sweep candidates` table with merge, file, symbol, severity, confidence, and description.
  - Print selected count, skipped count, pending-frontier count, and an explicit incomplete-coverage notice when pending work remains.
  - Print a distinct `ANALYZE_BUGS_SWEEP_COST_ESTIMATE=...` line based on bounded finder and refuter inputs using the existing Sonnet rate lookup.
  - Add surviving candidates to the existing `follow-up-issue.md`.
  - When sweep survivors exist but legacy follow-ups are empty, create `follow-up-issue.md` with a sweep section and emit its path in report output.
  - Preserve the non-sweep report path and do not create sweep state or sweep-only follow-up output without a validated sweep artifact.
  - Write `sweep-state.json` last, only after the final report, follow-up body, and other sweep artifacts complete successfully.
  - Advance the discovery watermark to the pinned `origin/main` tip and persist all unselected eligible SHAs as `pending_shas`, so capped work is retried rather than discarded.
- Preserve current behavior when `--sweep` is absent.

### UPDATED: python/larch/cli.py

- Register `("analyze-bugs", "sweep")` to `sweep_main`.
- Leave the existing prefetch, ledger, deep, and report registrations unchanged.

### NEW: .claude/agents/sweep-bug-finder.md

- Add a Sonnet agent with `Read`, `Grep`, and `Glob`.
- Define finder and refuter modes in one agent contract.
- In finder mode:
  - Require the agent to read the supplied bundle and inspect the synced checkout.
  - Ask it to assume the commit planted a bug observable within 48 hours.
  - Target contract breaks, wrong keys or field names, and static logic errors.
  - Emit only one required strict finder JSONL row for its supplied merge: `{"merge_sha": str, "findings": [...]}`.
  - Return an empty findings list when no supported defect exists.
- In refuter mode:
  - Require the agent to receive and use only one row from `REFUTER_QUEUE_PATH`, then independently read the cited code and relevant consumers.
  - Attempt to disprove the candidate rather than repeat the finder’s reasoning.
  - Emit only `{"merge_sha": str, "finding_index": int, "verdict": "survives"|"refuted"}` for that queue row.
- Fail closed on unreadable bundles, queue rows, or checkout evidence. Never invent file contents or tool results.
- Cap findings per merge to keep refuter fan-out bounded.

### UPDATED: .claude/skills/analyze-bugs/SKILL.md

- Add `--sweep` and `--sweep-max N` to the argument hint and flag allowlist.
- Parse sweep controls before prefetch, forward only legacy prefetch arguments to the existing prefetch command, and reject `--sweep-max` without `--sweep`.
- Default `--sweep-max` to `20`; reject non-positive or invalid values before Task dispatch.
- Keep the existing clean, synced `main` preflight.
- After Stage 0 prefetch establishes the active run directory and before existing ledger and deep stages, add sweep stages:
  - S0 invokes `python3 python/cli.py analyze-bugs sweep prepare` in a shell fence and requires its non-zero exit to abort before any Task dispatch.
  - S1 dispatches one finder per selected bundle, captures each agent’s JSONL-only response into the fixed `RUN_DIR/sweep-finder.jsonl`, then invokes `python3 python/cli.py analyze-bugs sweep ingest-finder` in a shell fence.
  - S1 requires successful Python ingest and exact accepted coverage before refuter dispatch or any legacy ledger/deep stage; it reads `REFUTER_QUEUE_PATH` and `REFUTER_QUEUE_COUNT` only from the ingest command’s KVs.
  - S2 dispatches one refuter per row in `REFUTER_QUEUE_PATH`, captures JSONL-only responses into the fixed `RUN_DIR/sweep-refuter.jsonl`, then invokes `python3 python/cli.py analyze-bugs sweep ingest-refuter` in a shell fence.
  - S2 requires successful Python ingest and exact queue-key coverage before continuing to legacy stages.
  - For zero selected merges, skip finder dispatch and finder parsing but still run the successful prepare and finder-ingest fences that create an empty queue.
  - For a zero-length refuter queue, skip refuter dispatch and raw refuter capture but still run the successful refuter-ingest fence that writes the zero-candidate validated artifact.
- Continue with the existing Stage 1 ledger and Stage 2 deep work. Keep the existing Stage 3 report as the single final rendering and state-commit step that merges legacy and sweep results.
- Stop without changing sweep state after Task failure, malformed JSONL, rejected rows, missing coverage, stale-tip identity failure, or final report failure.
- Print the selected count, skipped count, pending-frontier count, incomplete-coverage status when capped, and sweep cost estimate.
- Keep the existing approval prompt. On approval, invoke `/issue` once with the combined follow-up body and do not pass `--no-dedup`.
- Document `sweep-state.json` beside `ledger.jsonl`, its pending-SHA frontier, and the first-run 48-hour window.
- Set expectations clearly: static sweep can find contract breaks, wrong field or key names, and logic errors. It cannot establish that main is bug-free or detect timing failures, vendor CLI drift, GitHub-state failures, or other runtime-only defects.

### UPDATED: python/tests/issue/test_analyze_bugs.py

- Add offline first-parent enumeration fixtures covering:
  - Saved-marker and first-run 48-hour windows.
  - Flush-subject and release-subject exclusions.
  - Commits touching only `larch-logs/`.
  - Two eligible commits in the acceptance history.
  - First-parent merge-specific changes appearing in touched paths, diff evidence, and symbol extraction.
  - A non-ancestor or malformed saved marker and an unreachable pending SHA.
- Test strict sweep-state round trips, absent-state defaults, schema rejection, pending-SHA validation, and private atomic replacement.
- Test resumable capped coverage:
  - A capped run persists skipped eligible SHAs and marks coverage incomplete.
  - A later run selects pending SHAs before newly enumerated lower-priority work as defined by the combined ranking.
  - No eligible skipped SHA is silently lost when the discovery watermark advances.
- Add a ledger fixture with no current-run bundles that makes `analytics.chronic_zones` observable, proving chronic-zone commits outrank non-chronic commits before diff size.
- Prove state remains absent or unchanged after:
  - Finder failure.
  - Missing, empty, rejected, or malformed finder rows when selected work exists.
  - Partial, empty, missing, or malformed refuter output when queued findings exist.
  - Report generation failure.
- Test zero-work handling:
  - Zero selected merges bypass finder dispatch and raw finder-file parsing, produce an empty queue, and complete with a validated zero-candidate artifact.
  - Valid empty findings rows for every selected merge produce a zero-length refuter queue that bypasses refuter-file parsing and completes successfully.
  - Empty or absent raw result files remain failures whenever finder or refuter work was dispatched.
- Prove a completed final report advances the discovery watermark and writes the pending frontier only after report artifacts exist.
- Test chronic-zone-first and descending-diff prioritization, deterministic ties, `--sweep-max`, skipped-count output, and incomplete-coverage output.
- Test bundle caps, first-parent bases, touched paths, chronic tags, changed-symbol extraction, consumer matches, and truncation notices.
- Add exact finder and refuter JSONL contract tests for unknown keys, bad enums, duplicate rows, foreign SHAs, invalid paths, missing files, incomplete coverage, valid empty finder results, and exact queue-key acceptance.
- Test executable `prepare`, `ingest-finder`, and `ingest-refuter` CLI fences, including emitted manifest paths, fixed raw-result paths, `REFUTER_QUEUE_PATH`, queue count, and non-zero exits before refuter or legacy-stage continuation.
- Add a golden transcript fixture where a wrong consumer dictionary key is found and survives refutation.
- Test final Stage 3 report output for `Sweep candidates`, the sweep cost line, skipped-count logging, incomplete coverage, and inclusion in the combined follow-up body.
- Test sweep-only survivors create `follow-up-issue.md`, emit its path, and remain approval-gated with dedup enabled.
- Test that zero findings is distinct from failed agent output.
- Test `analyze-bugs sweep --help` dispatch and that sweep flags are not forwarded to prefetch.
- Pin the new agent’s model, tools, strict schemas, read requirement, adversarial finder language, refutation language, queue-row-only refuter handoff, and unreadable-evidence fallback.

## Edge cases

- A first sweep with no commits in 48 hours completes with zero findings, does not require finder or refuter raw result files, and records the pinned tip with an empty pending frontier.
- A later sweep with only excluded commits completes and advances the discovery watermark with no pending work.
- A capped sweep records every unselected eligible SHA, reports incomplete coverage, and retries that frontier on later sweeps.
- A force-pushed or unrelated saved watermark, or an unreachable pending SHA, fails rather than silently widening or discarding coverage.
- Empty finder results are valid only when every selected merge has one well-formed accepted row.
- A finder candidate that the refuter rejects never enters the report or follow-up body.
- An empty refutation queue is a successful zero-candidate result and does not require a refuter output file.
- Sweep-only surviving candidates still produce a follow-up body for the existing approval-gated filing path.
- Existing non-sweep runs neither read nor write sweep state.

## Failure modes

- Git enumeration, first-parent diff, analytics lookup, or consumer scans that cannot produce bounded evidence abort the sweep.
- A non-empty selected manifest with malformed, rejected, missing, empty, or incomplete finder JSONL aborts before refuter dispatch or legacy stages.
- A non-empty refuter queue with malformed, rejected, missing, empty, or incomplete refuter JSONL aborts before legacy stages.
- A stale pinned tip, state identity mismatch, invalid sweep artifact, or mismatch between accepted keys and the prepared manifest or queue aborts rather than mixing evidence from different main revisions.
- Report or follow-up-body failure leaves the prior sweep marker and pending frontier intact.
- `/issue` filing failure does not rewrite sweep analysis state because analysis completed before the separately approval-gated mutation.

## Testing strategy

- Run `python3 -m pytest python/tests/issue/test_analyze_bugs.py -q`.
- Run `python3 python/cli.py lint agent-tool-contract`.
- Run the changed-file Python lint and type checks through `make py-lint`.
- Exercise CLI help for the new verb and the existing prefetch, ledger, deep, and report verbs.
- Verify executable sweep prepare/finder-ingest/refuter-ingest fences, including zero-work bypasses and fail-closed non-zero exits.
- Verify sweep-only, sweep-plus-legacy, capped-resumption, and legacy report fixtures.

difficulty: HARD
diff_added: 861
diff_deleted: 24
mechanical_churn: false
diff_lines: 885
