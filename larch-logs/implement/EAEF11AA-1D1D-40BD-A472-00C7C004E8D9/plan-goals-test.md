## Goal
Implement issue #3619: [IMPLEMENTING] Conditional spawning of review agents in /design, /implement, /review based on accepted-finding performance in the last 2 rounds\n\nPerformance-based conditional spawning of review agents, to cut wasted review tokens. (Originally #3463.).

## Implementation Plan
## Plan

# Implementation Plan — Issue #3619: Conditional spawning of review agents (Part B)

## Goal

Cut wasted review tokens. From round 3 on, do not launch reviewer combos (tool × archetype slot) that produced zero accepted items in their last 2 launched rounds. Round 5 re-probes with the full panel. Applies to `/design` plan review, `/implement` Step 5 code review, and `/review` diff mode.

**Builds on #3662 (landed).** #3662 flattened the review-round cap to a uniform 5 across `/design` (both tiers) and `/implement` and removed the vestigial cap knobs (`scripts/lib-implement-round-cap.sh` deleted; `review-implement-step5-loop.sh` now uses a fixed `ROUND_CAP:-5`; entry inflation and the post-round bump are gone). Verified in the current tree. This plan builds on that landed end state and makes **no cap edits of its own**.

## Approach

One new shared helper, `scripts/reviewer-prune.sh`, with two subcommands:

- `record` — after a round's tally, write one row per launched slot to a run-stable ledger TSV. Inputs: `--ledger FILE --round N --manifest FILE --classification FILE [--label-map FILE]`. Ledger columns: `round`, `tool`, `slot`, `label`, `accepted_count`. `record` is **idempotent per round**: it rewrites the ledger as (rows where round != N) + the new rows (atomic temp + `mv`), so a retried round attempt replaces the discarded attempt's rows instead of stacking duplicates. `record` also supports an empty replacement set: invoking the per-round rewrite with zero rows clears that round's rows (used by `/implement` retry clearing below).
- `filter` — before a round's launch, rewrite the panel manifest to eligible slots only. Inputs: `--ledger FILE --round N --manifest FILE --out FILE`. Emits KVs: `PRUNE_ACTIVE`, `ELIGIBLE_COUNT`, `PRUNED_COUNT`, `PRUNED_COMBOS` (comma list), `PANEL_PRUNED_EMPTY`.

Combo identity is the manifest pair `tool:slot`. Both dispatchers already build a complete NDJSON slot manifest before launch (`panel-manifest.ndjson` for code review; `plan-review-slots.ndjson` for plan review), so `filter` hooks in at exactly one point per dispatcher: after the manifest is fully built (static + dynamic), before the waterfall launch.

**Canonical manifest basenames stay authoritative** (accepted scope reduction): `filter` writes to a temp `--out` path (never in place). When `PRUNE_ACTIVE=true` and `PRUNED_COUNT > 0`, the dispatcher first copies the unfiltered manifest to a `<canonical>.pre-prune.ndjson` forensics sidecar, then atomically replaces the canonical manifest (`panel-manifest.ndjson` / `plan-review-slots.ndjson`) with the filtered content. `PANEL_MANIFEST` keeps pointing at the canonical basename, so all post-dispatch consumers (slot counts, output-to-slot mapping, label-map generation, coverage gate, threshold denominators, `record`) read the filtered content with no path changes, and existing log/snapshot allowlists keep working. When nothing is pruned (rounds 1-2, round 5, `LARCH_REVIEWER_PRUNE=off`, clean-slate combos, or no `--prune-ledger` flag), the canonical manifest is left byte-identical and no sidecar is written. Degradation bookkeeping keys on the filtered counts: the waterfall denominator, floor-half thresholds, succeeded-paths comparisons, and `DEGRADED_ROUND` all derive from the post-filter slot count, so a fully successful pruned launch is never reported degraded.

Eligibility rule in `filter`:

- `LARCH_REVIEWER_PRUNE=off` (exact match) → all slots eligible; `PRUNE_ACTIVE=false`.
- Round N ≤ 2 or N ≥ 5 → all eligible (rounds 1-2 baseline; round 5 full re-probe; N > 5 defensive — rounds are hard-capped at 5 since #3662).
- Otherwise (N = 3 or 4): take the combo's ledger rows with `round < N`; dedupe per round keeping max `accepted_count`. Fewer than 2 such rounds → eligible (clean slate). Both of the 2 most recent such rounds have `accepted_count=0` → pruned. Else eligible.
- Missing or unparsable ledger → all eligible plus a warning KV (fail open).

**Launched rounds are strike rounds**: every row in the filtered manifest that the round actually launched counts in the strike window with its measured `accepted_count`, including slots whose output came back empty, NOT_SUBSTANTIVE, or dropped under `--no-fallback`. Slots never launched in a round (pruned, outage-skipped at dispatch, or not yet scouted) have no row for that round, so they keep their clean slate. Rounds that are rolled back or never settle write no rows at all (see `record` call sites below). Per accepted scope reduction (round-1 FINDING_12), `record` keys only on the filtered manifest plus the classification TSV — there is no collector-results input and no per-slot collection diagnostics column.

"Accepted" means `voting_result=accepted` rows in the round's findings-classification TSV, including accepted OOS rows (anything that scores +1 in the point competition). A slot's `accepted_count` is the number of accepted rows whose attribution cell contains the slot's label under **exact normalized token equality**: split code-review `reviewer_slots` cells on `|`; split plan-review `finding_reviewers` cells on commas **and whitespace runs** (one split pass on `[,[:space:]]+` after trimming the cell) so space- or tab-derived multi-reviewer cells tokenize correctly instead of collapsing into one unmatched token; trim surrounding whitespace from each token, then require token == label after normalization. No substring or prefix matching. Labels:

- Code review: label = output basename (e.g. `cursor-specialist-security-output.txt`), matching `reviewer_slots` cells. Before equality, normalize each cell token with the same transformations the code-review pipeline already applies: the `normalize_reviewer_label` phase2/phase3/retry suffix-strip loop from `collect-findings.sh` and the one-trailing-parenthetical strip used by `aggregate-findings.sh`. This keeps attribution following the slot when a retry basename or a parenthetical label form reaches the classification TSV.
- Plan review: the caller supplies `--label-map` (TSV `slot<TAB>label`) generated with the loop's existing `plan_slot_human_label` (e.g. `cursor-plan-arch` → `Cursor-Arch`), matching `finding_reviewers` cells. No mapping duplication.

**Round-number source**: the prune round is the skill's review-round counter, not an artifact index. For `/design`, `run-step3-review.sh` threads the pending Gate C review round (`STEP3_REVIEW_ROUND_NUM`, the value it persists to `review-round-count.txt`) into `plan-review-loop.sh` as a new `--prune-round-num`; the loop forwards it to the dispatcher's `filter` and to `record`. The existing `--round-num` keeps its artifact-path role (`plan-review/round-N/` forensics) unchanged — on SIMPLE it stays 1 across Gate C re-entries while the prune round advances 1 → 2 → 3. For `/implement` and `/review`, the existing `--round-num` already is the loop round and serves both purposes.

`record` call sites: only settled rounds that produced a final classification TSV (`complete` / zero-findings paths). The gate is the settled status (`LOOP_STATUS` / `TALLY_PLAN_REVIEW_STATUS` for `/design`; the post-round status for code review), never bare TSV existence. Zero-findings rounds still strike: the `/design` skipped-empty-findings branch creates an explicit header-only findings-classification TSV and passes it to `record` so every launched slot writes an `accepted_count=0` row. Rolled-back `/design` rounds (`tally-error`, `degraded-empty-collector`), `panel-failed`, MAV-deferred rounds, and pruned-empty rounds are not recorded — their absence fails open. For `/implement`, in-round degraded retries must leave the round's ledger rows reflecting **only the final attempt**: `review-and-fix.sh` wraps the retry `review-core.sh` invocation in `set +e` (like the first call), captures the retry rc/status, and — before returning or propagating any terminal — either lets the settled retry's `record` replace the first attempt's rows via the per-round idempotent rewrite, or clears the round (per-round rewrite with zero rows) when the final retry status is **not in the settled record set** (`main-agent-vote-required`, `panel-failed`, `aggregator-validation-exhausted`, or any unexpected non-settled status), so a discarded attempt's strikes cannot survive into later rounds.

**Pruned-empty rounds advance, not converge.** When `filter` leaves zero slots (`PANEL_PRUNED_EMPTY=true`), nothing spawns and the round consumes its counter slot, but the loops must keep the round-5 full re-probe reachable instead of terminating early:

- Code review dispatch short-circuits before the waterfall with success KVs; `review-core.sh` returns a distinct `REVIEW_CORE_STATUS=prune-skipped` (zero findings, empty artifacts, `PANEL_PRUNED_EMPTY=true` passed through) instead of plain `ok`.
- `/implement`: `review-and-fix.sh` maps `prune-skipped` to a non-terminal round outcome and keeps it out of the `zero-findings|ok → complete` mapping; `review-implement-step5-loop.sh` gets an explicit `prune-skipped` case arm placed before the fix-applied/substantiality logic, mirroring the `fix-applied` shape: while `round_num < ROUND_CAP`, set `IRF_LAST_ROUND_STATUS=prune-skipped`, increment `round_num`, and `continue`; at the cap boundary, emit the normal complete envelope. `prune-skipped` never enters `convergence_candidate_status` and is never classified degraded.
- `/review` standalone: Step 3f treats `prune-skipped` as "continue to next round" (not convergence) while under the cap.
- `/design`: `plan-review-loop.sh` handles the dispatcher's `PANEL_PRUNED_EMPTY=true` immediately after parsing dispatch output — before the raw-stdout replay, before the collector runs, and before the degraded-empty normalization tail can see zero collected outputs: write empty artifacts + "round skipped: all reviewer combos pruned" note, restore the prior cumulative OOS (`oos-accepted-design.md` / `oos.md`) so the skip does not truncate accepted-OOS state, set `LOOP_STATUS=complete`, `DEGRADED_PANEL=false`, emit a `WARN=` breadcrumb, then exit through `_snapshot_terminal_exit_preserving_status` (full script terminal exit) so control never reaches the `collect_ok_count=0` / `ACCEPTED_COUNT=0` degraded-empty-collector rewrite tail and the consumed round persists (`review-round-count.txt` advances; no rollback). The same `_snapshot_terminal_exit_preserving_status` exit (not a bare `return 0`) also guards the `TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings` zero-findings path so it cannot be rewritten to `degraded-empty-collector` either. The pruned-empty marker is threaded to the continuation check (below) so `/design` keeps scheduling rounds toward the round-5 re-probe.

**Pruned-empty visibility to `/design` continuation**: `plan-review-loop.sh` sets a `PANEL_PRUNED_EMPTY` shell variable on the pruned-empty branch and emits it both in `emit_loop_kvs` (before `_snapshot_terminal_exit_preserving_status`) and in the `write_step3_result_env` allowlisted KV set; `run-step3-review.sh` reads it in **all three** seams (the loop stdout KV parse case, the inner-env read allowlist, and the `result_env_kvs` / `phase_driver_write_result_env` set written to `.step3-review-result.env`); `plan-review-continuation.sh` reads it from `.step3-review-result.env` and returns `PLAN_REVIEW_CONTINUE=true` with reason `pruned-empty` while `REVIEW_ROUND_COUNT` is below the cap of 5, preserving non-degraded semantics. The continuation branch is placed **after** the cap-reached and `--approve` explicit-approve checks and **before** the heuristic small-clean default, so a pruned-empty round with zero accepted findings continues instead of stopping as small-clean (`--approve` still wins; at cap it stops). Without this end-to-end threading, a pruned-empty round 3 below cap would read as a small-clean stop and the round-5 full re-probe would be unreachable.

Cap surfaces are **out of scope**: #3662 already landed the fixed-cap-5 conversion (`/implement` entry/resume inflation removed, post-round `effective_round_cap` bump removed, `lib-implement-round-cap.sh` deleted, Step 5 telemetry fence reporting `ROUND_CAP=5`). This plan touches `review-implement-step5-loop.sh` only to add the `prune-skipped` round advancement.

## Files to modify/create

### NEW: `scripts/reviewer-prune.sh`

The shared helper. Bash 3.2-safe (`jq` for NDJSON, `awk` for TSVs; no associative arrays); `set -euo pipefail`; `lib-quiet.sh` KV output. `record` does the per-round replace-rewrite atomically (including the zero-row clearing form) and applies the code-review label normalization (phase2/phase3/retry suffix strip + one-trailing-parenthetical strip) before token equality; `filter` writes the filtered manifest to `--out` (never in place) and prints one `larch_err` line when it prunes (`→ review prune: round N drops <combos>`).

### NEW: `scripts/reviewer-prune.md`

Sibling contract: callers, ledger schema (`round`, `tool`, `slot`, `label`, `accepted_count`), launched-row strike rule, exact-token matching grammar (pipe split + suffix/parenthetical normalization for code cells; `[,[:space:]]+` split for plan cells), per-round replace semantics incl. zero-row clearing, eligibility rule incl. the rounds {3,4} window and round-5 re-probe, `LARCH_REVIEWER_PRUNE`, fail-open semantics, harness pointer.

### NEW: `scripts/test-reviewer-prune.sh`

Offline harness: record (code + design label styles); per-round replace-rewrite (re-record same round → rows replaced, other rounds untouched; zero-row invocation clears the round); launched-but-failed slot still strikes (row present with `accepted_count=0`); exact-token matching incl. shared-prefix labels and comma vs whitespace vs pipe cells — code-review fixtures use real manifest output basenames (classification `reviewer_slots` pipe tokens and ledger `label` column both `dyn-foo-output.txt` / `dyn-foo-codex-output.txt`) and assert `dyn-foo-output.txt` does NOT match `dyn-foo-codex-output.txt`; normalization fixtures: a `-phase2` retry basename and a one-trailing-parenthetical label form both credit the canonical slot; plan-review fixtures include a space/tab-separated multi-reviewer `finding_reviewers` cell mirroring the `test-findings-classification.sh` ballot shape; accepted OOS row counts; filter rounds 1/2/5/6 all-eligible; round-3 2-strike prune; 1-round history clean slate; `LARCH_REVIEWER_PRUNE=off` → `PRUNE_ACTIVE=false`; corrupt/missing ledger fail-open warning; `PANEL_PRUNED_EMPTY` on all-pruned manifest.

### NEW: `scripts/test-reviewer-prune.md`

Harness stub naming the primary.

### UPDATED: `skills/review/scripts/dispatch-panel.sh`

Accept `--prune-ledger FILE` (optional; absent → no filtering, today's behavior). After static + dynamic slots are finalized and before the waterfall call, run `reviewer-prune.sh filter` against `panel-manifest.ndjson` into a temp file, passing `--round "$ROUND_NUM"` (the same value as `review-core.sh --round-num`) so the filter applies its round-window eligibility rather than recording strikes against an unset round. When `PRUNE_ACTIVE=true` and `PRUNED_COUNT > 0`: copy the unfiltered manifest to `panel-manifest.pre-prune.ndjson`, atomically replace `panel-manifest.ndjson` with the filtered content, and recompute `STATIC_SLOT_COUNT` / `DYNAMIC_SLOTS` / the launch line counts from the now-filtered canonical manifest (static rows carry `agent`; dynamic rows carry `prompt_file`); `PANEL_MANIFEST` keeps its canonical path. When nothing is pruned, leave the canonical manifest byte-identical (no sidecar). Pass `PRUNED_COMBOS` through as a KV. On `PANEL_PRUNED_EMPTY=true`, short-circuit before the waterfall: emit `DISPATCH_OK=true`, `PANEL_MODE=waterfall`, `PANEL_SHAPE`, scout KVs as computed, zero `STATIC_SLOT_COUNT` / `SLOT_COUNT`, `PANEL_PRUNED_EMPTY=true`, empty `EXTERNAL_OUTPUT_FILES` / `CLAUDE_OUTPUT_FILES`, and exit 0.

### UPDATED: `skills/review/scripts/dispatch-panel.md`

Document the flag, hook position, canonical-basename filtering with `panel-manifest.pre-prune.ndjson` sidecar, short-circuit KVs, and that pruned rounds are not degraded.

### UPDATED: `skills/review/scripts/review-core.sh`

Accept `--prune-ledger` and **forward it on the `dispatch-panel.sh` invocation** (without the forward, the filter never runs and later rounds keep launching the full panel). Consume `PANEL_MANIFEST` (canonical path, post-filter content) for all downstream uses. Keep the existing `check-reviewer-failure-threshold.sh` **unchanged** (static-only) — per accepted scope reduction, the no-successful-output protection stays **local to `review-core.sh`** instead of expanding the threshold helper's contract. Add that narrow fail-closed guard inline: when pruning produced a filtered manifest with **zero static rows** (or, more generally, when every launched filtered slot failed/dropped/non-substantive) and there is no successful reviewer output, fail closed before the zero-findings convergence path rather than converging as clean. On `PANEL_PRUNED_EMPTY=true`: write empty findings artifacts and return `REVIEW_CORE_STATUS=prune-skipped` with zero counts plus an operator-visible prune-skip line, before collection, threshold math, the coverage gate, aggregation, and voting. Change `static_archetype_coverage_ok` to derive its expected archetype set from the filtered manifest's static rows instead of the hardcoded 4, so pruning one archetype's both vendors does not trip the gate; align it with the same narrow fail-closed rule for the no-static-rows case. On the zero-findings / `skipped-empty-findings` terminal path, snapshot the prior cumulative OOS (`oos-accepted-review.md` / `accumulated-oos.md`) before `write_empty_review_artifacts` clears it and restore it before the terminal exit — when the accumulated mirror is non-empty, re-mirror it to the parent (`mirror_oos_markdown`) or skip the OOS `copy_to_parent` on this path — mirroring the pruned-empty branch, so a clean zero-findings or prune-skipped round never silently truncates accepted-OOS state from earlier rounds. Wrap the `reviewer-prune.sh record` (and any zero-row clear) call in failure isolation: on a non-zero pruning sidecar operation, emit `WARN=` and preserve the settled `REVIEW_CORE_STATUS` rather than letting the ledger op abort an otherwise-settled round. After settled tallies that produced a classification TSV (normal and zero-findings branches; not MAV / panel-failed / aggregator-exhausted; gate on the settled status, not TSV existence), call `reviewer-prune.sh record` with the filtered manifest and the round's classification TSV. No-op when `--prune-ledger` was not supplied.

### UPDATED: `skills/review/scripts/review-core.md`

Document flag (incl. the dispatch-panel forward), record/filter points, `prune-skipped` status, canonical filtered-manifest consumption, coverage-gate change, the narrow in-`review-core.sh` no-successful-launched-rows fail-closed guard (the threshold helper stays static-only), the zero-findings/prune-skipped cumulative-OOS preservation (`oos-accepted-review.md` snapshot/restore), and the record/clear failure-isolation rule.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`

Pass `--prune-ledger "$IMPLEMENT_TMPDIR/reviewer-prune-ledger.tsv"` on every `review-core.sh` invocation (run-stable path; `REVIEW_TMPDIR` is round-scoped here). Map `REVIEW_CORE_STATUS=prune-skipped` to a non-terminal round outcome distinct from convergence and keep it out of the `zero-findings|ok → complete` status mapping. Retry hygiene: wrap the degraded-retry `review-core.sh` invocation in `set +e` exactly like the first call, capture the retry rc/status, update `core_rc` from the retry, and before any return or terminal propagation apply the final-attempt rule — settled retry outcomes let `record`'s per-round rewrite replace the first attempt's rows; when the final retry status is not in the settled record set (`main-agent-vote-required`, `panel-failed`, `aggregator-validation-exhausted`, or any unexpected non-settled status), invoke the per-round rewrite with zero rows to clear the first attempt's strikes. The clear-before-return rule is keyed on "final retry status not in the settled record set," not a short allowlist. Each clear call is failure-isolated (WARN, preserve the terminal status).

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.md`

Note the ledger threading, prune-skipped mapping, and the clear-before-return retry rule (settled-set trigger, not a short allowlist).

### UPDATED: `skills/review-and-fix/scripts/review-implement-step5-loop.sh`

Add an explicit `prune-skipped` case arm in the post-round status handling, placed before the fix-applied/substantiality and bulk-skip convergence logic, mirroring the `fix-applied` shape: while `round_num < ROUND_CAP`, set `IRF_LAST_ROUND_STATUS=prune-skipped`, increment `round_num`, `continue`; at the cap, emit the normal complete envelope. Never map `prune-skipped` to `complete`/`no-findings` mid-loop, never add it to `convergence_candidate_status`, never classify it degraded. No cap edits — the fixed-cap-5 conversion of this file already landed via #3662.

### UPDATED: `skills/review-and-fix/scripts/review-implement-step5-loop.md`

Document prune-skipped advancement and its placement relative to convergence logic.

### UPDATED: `skills/design/scripts/run-step3-review.sh`

Thread the pending Gate C review round into the loop: pass `--prune-round-num "$STEP3_REVIEW_ROUND_NUM"` (the value persisted to `review-round-count.txt` for this entry) on the `plan-review-loop.sh` invocation. Persist the loop's `PANEL_PRUNED_EMPTY` KV into `.step3-review-result.env` by adding it to **all three** seams: the loop-stdout KV parse case, the inner-env read allowlist, and the `result_env_kvs` / `phase_driver_write_result_env` set (normalized alongside `LOOP_STATUS`) so the continuation helper can see pruned-empty rounds.

### UPDATED: `skills/design/scripts/run-step3-review.md`

Document the new threading and add `PANEL_PRUNED_EMPTY` to the persisted/normalized-key table.

### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.sh`

Accept `--prune-round-num N` and `--prune-ledger FILE` (both optional; absent → today's behavior). After static + dynamic slots are written to `plan-review-slots.ndjson`, run `reviewer-prune.sh filter` into a temp file. When `PRUNE_ACTIVE=true` and `PRUNED_COUNT > 0`: copy the unfiltered manifest to `plan-review-slots.pre-prune.ndjson`, atomically replace `plan-review-slots.ndjson` with the filtered content, and recompute the waterfall slot total, `DYNAMIC_SLOT_COUNT`, the floor-half degradation threshold, and the succeeded-paths comparison from the now-filtered canonical manifest so `DEGRADED_ROUND` keys only on slots that actually launched; `PANEL_MANIFEST` keeps its canonical path. When nothing is pruned, leave the manifest byte-identical (no sidecar). On empty: `DISPATCH_OK=true`, `STATIC_DISPATCH_OK=true`, `FALLBACK_COUNT=0`, `COMBINED_FALLBACK_COUNT=0`, `DYNAMIC_SLOT_COUNT=0`, `DEGRADED_ROUND=false`, `PANEL_PRUNED_EMPTY=true`, empty `PANEL_PATHS_FILE`, exit 0 before the waterfall. The both-externals-absent Claude-generic path is untouched (no manifest; pruning does not apply).

### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.md`

Document new flags, canonical-basename filtering with `plan-review-slots.pre-prune.ndjson` sidecar, filtered-count degradation math, short-circuit.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`

Accept `--prune-round-num` and forward it with `--prune-ledger "$DESIGN_TMPDIR/reviewer-prune-ledger.tsv"` to the panel dispatcher. Extend the dispatch-output KV parser with a `PANEL_PRUNED_EMPTY)` arm (before the `WARN)` arm) so the flag is read. Consume `PANEL_MANIFEST` (canonical path, post-filter content) for `slot_count`, `plan_review_slot_for_reviewer` output-to-slot mapping, label-map generation, degradation checks, and `record`. Branch on `PANEL_PRUNED_EMPTY=true` immediately after the dispatch parse — before the raw dispatch-stdout replay, before the collector launch, and before the degraded-empty ("dispatch produced no reviewer paths" / zero-collected) handling: write empty artifacts + "round skipped: all reviewer combos pruned" note, restore the prior cumulative OOS before the terminal snapshot so accepted-OOS state is not truncated, set `LOOP_STATUS=complete`, `DEGRADED_PANEL=false`, emit `WARN=plan-review: round N skipped — all combos pruned` and `PANEL_PRUNED_EMPTY=true` in the result KVs, and exit via `_snapshot_terminal_exit_preserving_status` (full script terminal exit, **not** a bare `return 0` mirroring the zero-findings pattern) so the consumed round persists and the degraded-empty-collector normalization tail is never reached. Zero-findings rounds strike: the skipped-empty-findings branch creates an explicit header-only findings-classification TSV, snapshots the prior cumulative OOS before `write_empty_review_artifacts`, calls `record` (header-only TSV ⇒ launched slots write `accepted_count=0` rows) **inside that early-exit branch**, restores the cumulative OOS, then exits via `_snapshot_terminal_exit_preserving_status` so it cannot be rewritten to `degraded-empty-collector` and never truncates accepted-OOS state. The pruned-empty early-exit branch does **not** record (zero launched slots ⇒ zero ledger rows). The outer pre-`_snapshot_terminal_exit_preserving_status` `record` hook therefore covers only the **normal completion** path; it is pinned **after** the panel-failed / MAV / tally-error post-round status branches and gated on the settled `LOOP_STATUS` / `TALLY_PLAN_REVIEW_STATUS`, never on bare TSV existence; the no-record set is tally-error, panel-failed, MAV-deferred, and `PANEL_PRUNED_EMPTY`. For recorded rounds, build the slot→label map via `plan_slot_human_label` from the filtered manifest and call `record` with `--round` = the prune round and the round-N `findings-classification.tsv`. Every `record` / zero-row-clear call is wrapped in failure isolation: a non-zero ledger op emits `WARN=` and preserves the settled `LOOP_STATUS` instead of aborting the round.

### UPDATED: `skills/design/scripts/plan-review-loop.md`

Document prune-round/ledger threading, the dispatch-parser `PANEL_PRUNED_EMPTY)` arm, canonical filtered-manifest consumption, pruned-empty complete path (placement before raw replay/collect; `_snapshot_terminal_exit_preserving_status` exit; cumulative-OOS restore), zero-findings header-only TSV recording, the record hook pin (after status branches, before terminal snapshot), record gating + no-record set, MAV fail-open.

### UPDATED: `skills/design/scripts/plan-review-continuation.sh`

Read `PANEL_PRUNED_EMPTY` from `.step3-review-result.env` (via `kv_get`). Insert the pruned-empty branch **after** the cap-reached and `--approve` explicit-approve checks and **before** the heuristic small-clean default `elif` chain: when `PANEL_PRUNED_EMPTY=true` and `REVIEW_ROUND_COUNT < ROUND_CAP`, return `PLAN_REVIEW_CONTINUE=true` with `PLAN_REVIEW_CONTINUE_REASON=pruned-empty` (non-degraded semantics preserved); at cap, stop. `--approve` explicit-approve still wins by precedence. Without this placement the zero-accept pruned-empty round would fall through to the small-clean stop.

### UPDATED: `skills/design/scripts/plan-review-continuation.md`

Document the pruned-empty continue predicate.

### UPDATED: `skills/design/scripts/test-step3-review-cap.sh`

Extend the continuation coverage: pruned-empty round below cap → `PLAN_REVIEW_CONTINUE=true` reason `pruned-empty`; pruned-empty at cap → stop.

### UPDATED: `skills/design/scripts/test-run-step3-review.sh`

Allow `--prune-round-num` in the loop-stub seam and add a focused case: seed `review-round-count.txt`=2, assert the driver invokes the loop with `--prune-round-num 3` while `--round-num` keeps its artifact-round value, and assert `PANEL_PRUNED_EMPTY` from loop stdout is persisted into `.step3-review-result.env`.

### UPDATED: `scripts/test-design-structure.sh`

Extend `_plan_forward_flags` (and any seam whitelist) with `--prune-round-num`; pin that `run-step3-review.sh` passes `--prune-round-num "$STEP3_REVIEW_ROUND_NUM"` on the loop invocation.

### UPDATED: `scripts/lib-design-round-artifacts.sh`

Add `reviewer-prune-ledger.tsv` and the `plan-review-slots.pre-prune.ndjson` forensics sidecar to the round-snapshot allowlist.

### UPDATED: `scripts/lib-design-round-artifacts.md`

Note the new rows.

### UPDATED: `skills/review/SKILL.md`

Step 3 loop: add `--prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv"` to the `review-core.sh` call line; Step 3f: `prune-skipped` continues to the next round (not convergence) while under the cap; one sentence on rounds 3-4 reduced panels. Replace any remaining 3-round safety-limit instruction on the `/review` execution path with the 5-round cap, mentioning the round-5 full re-probe, so inline review cannot stop before round 5 by prose.

### UPDATED: `skills/review/references/heavy-worker.md`

Mirror the conditional-spawning contract for `/review --diff --subagent`: pass `--prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv"` on each `review-core.sh` round, document rounds 3-4 pruning, prune-skipped advancement, and align the round-cap prose with the 5-round behavior.

### UPDATED: `skills/design/SKILL.md`

Amend the two "full panel" prose sites: rounds 1-2 and 5 full; rounds 3-4 mechanically pruned via `reviewer-prune.sh` (`LARCH_REVIEWER_PRUNE=off` restores). Keep the "never abbreviate by judgment" spirit: pruning is mechanical, not orchestrator discretion. Check `scripts/test-design-structure.sh` pins on edited paragraphs.

### UPDATED: `skills/implement/SKILL.md`

Step 5: one-line conditional-spawning note (rounds 3-4 may launch a reduced panel; all-pruned rounds advance). #3662's fixed-cap telemetry fence/banner rewrite already landed — do not re-edit it here.

### UPDATED: `skills/design/references/plan-review.md`

Note the rounds-3/4 pruning rule, prune-round source, canonical-basename filtering, and `PANEL_PRUNED_EMPTY` semantics where the panel composition is described.

### UPDATED: `docs/configuration-and-permissions.md`

Document `LARCH_REVIEWER_PRUNE` (only exact `off` disables; other values = on + warning).

### UPDATED: `docs/point-competition.md`

Scoreboard attribution now also drives conditional spawning from round 3 (per-run only).

### UPDATED: `docs/linting.md`

Register the new harness.

### UPDATED: `Makefile`

Add `test-reviewer-prune` target; wire into aggregate target.

### UPDATED: `agent-lint.toml`

Add any exclusion needed so the new `scripts/test-reviewer-prune.sh` and its sibling `scripts/test-reviewer-prune.md` pass the dead-doc / script-md lint rules (mirror how the other `scripts/test-*.sh` + `.md` pairs are registered), so `make lint` is green before the feature is verifiable.

### UPDATED: `skills/review/scripts/test-dispatch-panel.sh`

Prune filtering drops a 2-strike static slot; canonical `panel-manifest.ndjson` carries the filtered content while `panel-manifest.pre-prune.ndjson` preserves the unfiltered rows; `PANEL_MANIFEST` path unchanged; no-prune rounds leave the manifest byte-identical with no sidecar; all-pruned short-circuit; no-flag unchanged behavior.

### UPDATED: `skills/review/scripts/test-review-core.sh`

Pin `--prune-ledger` forwarding in the dispatch-panel argv assertions; pruned-empty → `REVIEW_CORE_STATUS=prune-skipped` with no threshold/coverage failure; record runs on settled tallies; manifest-derived coverage gate ignores pruned archetypes; the in-`review-core.sh` fail-closed guard trips on a pruned panel with no successful launched output; a multi-round zero-findings/prune-skipped case asserts prior `oos-accepted-review.md` bytes survive; a stubbed `record` failure emits WARN and preserves the settled status.

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`

Pruned-empty → `LOOP_STATUS=complete` (asserted after full script exit, not `degraded-empty-collector`), `DEGRADED_PANEL=false`, empty artifacts, prior cumulative OOS preserved (`oos-accepted-design.md` bytes match the pre-round snapshot), **and `review-round-count.txt` still advances** (no rollback); pruned-empty writes no ledger rows; zero-findings round records `accepted_count=0` rows via the header-only TSV, preserves prior `oos-accepted-design.md`, and is not rewritten to degraded-empty-collector; partial-prune round stays non-degraded with counts from the filtered manifest; record gating skips tally-error/panel-failed/MAV paths; record uses `Cursor-Arch`-style labels and the prune round (simulate Gate C re-entry where prune round = 3 while artifact round stays 1).

### UPDATED: `skills/design/scripts/test-dispatch-plan-review-panel.sh`

Flag filtering with canonical-basename replacement + `plan-review-slots.pre-prune.ndjson` sidecar; degradation math keyed on filtered counts (fully successful pruned launch → `DEGRADED_ROUND=false`); short-circuit KVs.

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`

`--prune-ledger` forwarding; `prune-skipped` advances the loop without convergence or degraded classification; retry-clearing cases: first attempt records rows, in-round retry ends in each no-record terminal (`main-agent-vote-required`, `panel-failed`, `aggregator-validation-exhausted`, and a synthetic unexpected status) → the round's ledger rows are cleared before return (no stale strikes), and a settled retry replaces rows.

## Edge cases

- <2 launched prior rounds → eligible (fresh dynamic archetypes, outage-skipped slots, new runs).
- Launched-but-failed slots (empty output, NOT_SUBSTANTIVE, `--no-fallback` drop) → strike rows with `accepted_count=0`.
- MAV-deferred tallies and rolled-back rounds → no ledger row; retried `/implement` rounds → rows reflect only the final attempt (replace on settled retry, zero-row clear on no-record terminal).
- Re-scouted dynamic archetype → same slot name → history accrues (intended).
- Both vendors down: code review Claude-fallback rows keep `cursor:*` keys and strike normally; /design Claude-generic path bypasses pruning.
- `/review` description mode is single-pass → never prunes.
- No-prune rounds (1-2, 5, off-switch, clean slates) leave canonical manifests byte-identical — no sidecar, no path changes.
- /design SIMPLE: with the landed flat cap of 5 on both tiers, the prune round advances 1 → 5 across Gate C entries (artifact round may stay 1); rounds 3-4 prune, round 5 re-probes with the full panel on both tiers; pruned-empty rounds keep continuing via the `pruned-empty` continuation reason.

## Failure modes

1. **Pruned round misread as degraded or terminal** → wrong rollbacks/convergence, or `/design` stopping before the round-5 re-probe. Signal: `DEGRADED_ROUND=true`, degraded classification, convergence on a round-3+ skip, or a continuation stop on a pruned-empty round below cap. Mitigation: explicit `PANEL_PRUNED_EMPTY` KV threaded end-to-end, distinct `prune-skipped` status, `pruned-empty` continuation reason, degradation math keyed on filtered counts, harness assertions that degraded flags stay false and loops/counters advance.
2. **Label-mapping drift** → accepted_count always 0 → over-pruning to empty panels. Signal: all-zero ledger while voting-tally shows accepted findings. Mitigation: basename labels + pipeline-matching normalization (phase suffixes, trailing parenthetical) + exact token equality for code; reuse of `plan_slot_human_label` via `--label-map` for design; comma/whitespace tokenization for plan cells; shared-prefix and normalization fixtures from real artifacts.
3. **Stale strike rows from discarded attempts** → over-pruning keyed to rounds that never settled. Signal: ledger rows for a round whose terminal status was MAV/panel-failed/aggregator-exhausted. Mitigation: settled-status record gating, per-round replace-rewrite, zero-row clearing before terminal propagation, retry harness cases for every no-record terminal.
4. **Pruned/empty round rewritten as degraded-empty-collector** → counter rollback and unreachable round-5 re-probe. Signal: `LOOP_STATUS=degraded-empty-collector` on a pruned-empty or skipped-empty round; `review-round-count.txt` rollback. Mitigation: both branches exit via `_snapshot_terminal_exit_preserving_status` before the normalization tail; `PANEL_PRUNED_EMPTY` threaded through all three run-step3 seams; continuation branch placed before the small-clean default; harness asserts `complete` after full script exit and counter advance.
5. **Cumulative accepted-OOS truncated by an empty round** → accepted OOS from earlier rounds silently lost. Signal: `oos-accepted-design.md` / `oos-accepted-review.md` shorter after a zero-findings or pruned-empty round. Mitigation: snapshot-before-clear + restore-before-exit on both empty branches in both review-core and plan-review-loop; harness byte-equality assertions.
6. **Ledger sidecar failure aborts a settled round** → a green review round fails on a prune bookkeeping error. Signal: non-zero exit traced to `reviewer-prune.sh record`/clear. Mitigation: every record/clear call is failure-isolated (WARN, preserve settled status); stubbed-failure harness case.

## Testing strategy

New offline `scripts/test-reviewer-prune.sh` plus extended harnesses listed above; all fixture-based. `make lint` + `bash scripts/relevant-checks.sh`; same-PR launcher-harness updates per `.claude/rules/launcher-argv-test-coverage.md`.


## Acceptance


- Rounds 1-2 byte-identical with empty ledger — including canonical manifest paths and bytes (no sidecar, no rewrite); rounds 3-4 drop exactly 2-strike combos; round 5 always full.
- All-pruned round: nothing spawns, the round counter advances, loops continue toward round 5 (or the cap ends them), no degraded flags; `/design` continuation returns `PLAN_REVIEW_CONTINUE=true` reason `pruned-empty` below cap.
- A fully successful pruned (partial) round is never reported degraded — degradation denominators come from the filtered manifest.
- `LARCH_REVIEWER_PRUNE=off` restores today's behavior everywhere.
- Builds on #3662's landed flat cap of 5 (no cap edits in this issue); `prune-skipped` rounds advance the loop toward the cap; no 3-round stop remains on the `/review` execution path.
- `/design` pruning keys on the Gate C review round (engages at the third entry on both tiers).
- New + updated harnesses green; `make lint` green.


diff_lines: 1455

## Test plan
(no test plan section in plan-file)
