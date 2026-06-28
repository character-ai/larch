# Review Round 1

- Mode: `diff`
- 10 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Multipart priority label failure still creates later parts
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-oos-priority
- **Severity**: important
- **Concern**: On `priority_label` failure inside the multipart part loop (`_split_to_github_limit`), `continue` lets later parts of the same item still be created. A failed earlier part may be cleaned up while a later part is filed, producing fragmented issues, incomplete sentinel state, and high-risk deferrals left unlabeled or inconsistently labeled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Break out of the part loop (or skip remaining parts for that item_index) after priority label failure instead of continue.
  - From dyn-dyn-oos-priority: On `priority_label` failure for any part of an item, stop processing further parts for that `item_index` (break/return for the item), record the URL in `batch.filed` when it should be retried, and drive partial persistence from that state.


### FINDING_2: Duplicate match URLs omitted from `batch.filed` on priority label failure
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-priority
- **Severity**: important
- **Concern**: When `issue create-one` returns a duplicate URL for a high-risk item and `_apply_priority_label` fails, the batch loop `continue`s without appending that `FiledIssue`. The live duplicate stays without `oos-correctness`, the URL is omitted from sentinel/partial persistence, and label-only retry or backfill cannot target it. If it was the only outcome, partial persistence may be skipped entirely (`batch.filed` empty).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Append duplicate FiledIssue rows to filed even on label failure, or persist failed duplicate URLs for backfill before returning partial failure.
  - From cursor-specialist-edge-cases: Record duplicate URLs in filed/partial persistence on label failure, or append FiledIssue before counting the failure.
  - From cursor-specialist-testing: Append duplicate rows to filed on label failure without cleanup, or track them for retry; add duplicate+high-risk+label-fail test.
  - From dyn-dyn-oos-priority: On duplicate label failure, still append the `FiledIssue` (with `oos_priority=True`) to `batch.filed` and/or always persist failed duplicate URLs into the sentinel before returning `priority_label` / `priority_label_partial_failure`; do not rely on filtered cleanup for duplicates.


### FINDING_3: Implement backfill returns empty when filed URL count ≠ combined block count
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-oos-priority
- **Severity**: important
- **Concern**: `_priority_urls_from_combined_order` (used by `_backfill_priority_labels_from_sentinel`) returns an empty set whenever `len(real_filed)` is neither `1` nor equal to `len(combined_blocks)`. After partial create failures, slot gaps, or sentinel-only idempotent reruns, backfill can miss high-risk URLs even when `oos-combined.md` still marks specific indices as correctness/regression. Design-side `_label_only_url_priority_map` already handles slot-index gaps; implement backfill does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Port slot-index overlay mapping (design _label_only_url_priority_map) into implement backfill instead of strict length equality.
  - From codex-specialist-correctness: Map each persisted URL against the post-cap combined blocks directly, using the sentinel and ordering sidecars plus stable IDs, instead of gating on count equality.
  - From dyn-dyn-oos-priority: Port the slot-index overlay (filing order + optional stdout/sentinel slot map) into implement backfill, or set `oos_priority=True` on successful `FiledIssue` rows and map combined indices to sentinel URLs by stable ID / slot before applying labels.


### FINDING_5: Label-only priority mapping loses filing order after partial failures
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, codex-generalist
- **Severity**: important
- **Concern**: `_label_only_url_priority_map()` and related annotate paths compress or mis-order surviving URLs when `oos-issue.stdout.txt` is absent (e.g., after partial `/larch:issue` failures, `$DESIGN_TMPDIR` cleanup, or fresh-session label-only retry). Filing-order sidecar and `OOS_FILE_MAP` slot indices are ignored or collapsed via `enumerate(sentinel_urls, start=1)` or sorted URL sets, so a high-risk survivor from one slot can be checked against the wrong combined block, miss `oos-correctness`, or have pending state cleared incorrectly. A related failure mode treats any single surviving URL across multiple combined blocks as a “cap rollup” and labels it whenever any block is high-risk, so a non-priority survivor can inherit priority from the wrong slot. Normal annotate also writes a sorted set of raw GitHub URLs, losing original slot order when blocks already had Filed URL lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require filing-order sidecar on label-only paths or derive order only from OOS_FILE_MAP rows, never sorted bare URLs.
  - From codex-specialist-correctness: Use the filing-order sidecar to reconstruct original slot indices even without stdout, or fail closed instead of compressing survivors.
  - From cursor-specialist-edge-cases: Parse OOS_FILE_MAP slot indices (or persist stdout in durable sidecars) for slot-aligned mapping when stdout is missing.
  - From codex-specialist-edge-cases: keep the original slot map from `oos-design-filing-order.txt` and stdout, and only use the any-match shortcut when you can prove the batch was truly rolled up to one issue.
  - From codex-specialist-testing: Build the slot map from the filing-order sidecar first and keep failed-slot gaps, then use stdout only as an overlay.
  - From codex-generalist: Preserve original slot indices in `_urls_from_sentinel` or parse `OOS_FILE_MAP` slot numbers in `_label_only_url_priority_map`, and never clear pending when slot-to-combined mapping is ambiguous.
  - From codex-specialist-correctness: Persist every filed URL in original slot order, including already-filed blocks, rather than falling back to a sorted set.


### FINDING_7: Sole-URL backfill fallback mislabels non-priority survivor
- **Reviewer(s)**: codex-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: `_priority_urls_from_combined_order()` treats “one persisted URL plus multiple combined blocks” as proof of a true cap rollup. On a rerun after partial create failure, it can backfill `oos-correctness` onto the lone surviving issue even when the high-risk block was a different slot that failed to create, or when a non-priority OOS was persisted while a separate high-risk block remains unfiled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: derive backfill targets from stable-id or slot evidence, and do not treat "one persisted URL plus multiple combined blocks" as proof of a true rollup by itself.
  - From codex-generalist: Only use the sole-URL any-priority fallback when the post-cap combined file has one aggregate block or when stable-id/title evidence ties that URL to the high-risk source.


### FINDING_8: Missing mixed-batch priority_label partial persistence test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: No test covers implement mixed-batch `priority_label` partial persistence with a surviving non-priority issue. A refactor that treats any batch failure like `hard_create` could delete or omit the cosmetic survivor from sentinel/ndjson while only the high-risk row fails labeling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a two-item test; fail _apply_priority_label on the correctness row only; assert priority_label_partial_failure payload, sentinel contains cosmetic URL, and cleanup is not invoked for the survivor.


### FINDING_9: Missing cap-rollup priority labeling end-to-end test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Cap rollup priority labeling is untested end-to-end despite plan acceptance criteria. Under `OOS_ISSUES_PER_RUN_CAP=1` a rolled-up block with embedded `focus-area: correctness` may never receive `oos-correctness` in production without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add cap=1 test with indented correctness line in rollup body; assert label provision and create/edit labeling.


### FINDING_10: Missing annotate-label-failed Step 5b.5 gate test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: No lifecycle test proves `annotate-label-failed` blocks Step 5b.5 advance. A regression could restore mark-complete/continue-to-5b.5 on non-zero annotate with stdout, publishing diagrams while high-risk OOS issues lack labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add step5b annotate test emitting annotate-label-failed; assert _determine_step stays below 5b.5 and .completed/step-5b.5 is absent.


### FINDING_11: Missing REPO fail-closed test for design annotate labeling
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Missing REPO fail-closed test for design annotate labeling. If REPO is unset in a consumer repo, annotate may return `annotate-label-failed` without a regression test ensuring no silent gh calls or false success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Annotate priority fixture with empty repo resolution; assert annotate-label-failed and no gh invocations.


### FINDING_12: Priority backfill runs before sentinel-recovery snapshot is available
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Priority backfill runs before the sentinel-recovery snapshot is materialized and only looks at the current combined file. A clean rerun with only `oos-issues-created.md` persisted can finish idempotently without reapplying `oos-correctness` to high-risk URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Restore or synthesize the accepted snapshot before backfill, or let the helper recover priority from persisted sentinel rows plus the durable recovery snapshot when combined is absent.


