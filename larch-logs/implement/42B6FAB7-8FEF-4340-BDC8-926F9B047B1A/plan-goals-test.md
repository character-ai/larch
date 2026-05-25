## Goal
Fix five small bugs bundled into one PR: #2764 plan-review dedup splitter, #2780 Step 0b tier mapping + SUMMARY_MODE_STRING jq filter, and #2778 docstring-only updates to lib-voter-parse-rate.sh and tracking-issue-read.sh.

## Implementation Plan
## Plan

Fix five related small bugs in the `/design` and shared-scripts surface, bundled into one PR because all changes are small, mechanical, and individually low-risk. A sixth sub-task from #2778 is verified as a no-op against current code and not included.

1. **#2764** — Plan-review dedup splitter emits duplicate `### OOS_N:` headings in multi-reviewer scenarios, causing `tally-plan-review.sh` rc=2.
2. **#2780 Bug 1** — Step 0b tier mapping in SKILL.md omits the `design_classification=<TOKEN>` value, causing `write-run-params.sh` to reject inferred `--classification "TRIVIAL"` and silently downgrade the user's tier to HARD.
3. **#2780 Bug 2** — Final-summary `SUMMARY_MODE_STRING` jq filter reads non-existent `.classification` field at three SKILL.md sites; render always shows `**Mode**: N/A` instead of the actual tier.
4. **#2778 sub-task 1 (originally #2770)** — `scripts/lib-voter-parse-rate.sh` CODE retry preamble names `FINDING_N` only; forward-aware nit that documents the FINDING-only-by-design asymmetry between CODE and PLAN ballots.
5. **#2778 sub-task 2 (originally #2772)** — `scripts/tracking-issue-read.sh` file-header output contract for `--sentinel` lists `ISSUE_NUMBER` and `ADOPTED` but omits `RUN_ID`, which `emit_kv RUN_ID` at lines 268-278 already emits. Docstring update only.

**Verify-and-skip** — **#2778 sub-task 3 (originally #2773)**: the bug as described (`|| true` suppression + `upstream-context.log` stderr redirect at `skills/implement/SKILL.md:646-658`) is **not present** in the current code. Line 655 reads `${CLAUDE_PLUGIN_ROOT}/scripts/get-issue-context.sh --issue "$TARGET_ISSUE_NUMBER" --repo "$UPSTREAM_REPO" --tmpdir "$IMPLEMENT_TMPDIR"` (no `|| true`, no log redirect), and line 658 says "On helper failure, print `**⚠ Step 0 tracking: tracking issue — upstream issue context fetch failed: $ERROR. Aborting.**` and skip to Step 18." (fail-closed). Note that the source issue #2773 was closed because it was bundled into #2778, NOT because it was independently fixed — so this is either (a) an independent fix landed in another PR between #2773 filing and now, or (b) the original description was inaccurate.

The implementer MUST re-verify the current state at PR time (`grep -n 'get-issue-context\|upstream-context\.log\|\|\| true' skills/implement/SKILL.md`) before treating sub-task 3 as a no-op. If the cited constructs are absent: no code change; record the verification in the PR body. If they are present: add an explicit `append-tool-failure.sh` invocation under `### Tool Failures` (or `### Warnings` for non-fatal context fetch failures) before the existing abort path so the failure is captured in `$IMPLEMENT_TMPDIR/execution-issues.md` for operator visibility.

### Files to modify

**UPDATED: `skills/design/scripts/plan-review-loop.sh`** (#2764)

Modify the Python dedup helper heredoc (currently at lines ~373-474):

1. Replace `split_blocks(text, prefix)` (lines ~395-403) with a unified `split_all_blocks(text)` that splits at any FINDING/OOS heading and classifies each block by the kind of its leading heading:

   ```python
   def split_all_blocks(text):
       parts = re.split(r"(?m)^(?=### (?:FINDING|OOS)_[0-9]+:)", text)
       fins, oos = [], []
       for p in parts:
           p = p.strip()
           if not p:
               continue
           m = re.match(r"^### (FINDING|OOS)_[0-9]+:", p)
           if not m:
               continue
           (fins if m.group(1) == "FINDING" else oos).append(p)
       return fins, oos
   ```

2. Replace the two `split_blocks(raw, "FINDING")` / `split_blocks(raw, "OOS")` calls in `main()` (lines ~453-454) with one `fins, oos = split_all_blocks(raw)`. Delete the now-unused `split_blocks` definition. Keep `dedup()`, `what_text()`, `merge_reviewers()` and the renumbering loop at lines 462-466 unchanged.

No other changes — the `findings-oos.md` extraction at lines 499-504 already uses a regex that terminates at any `### ` heading and is correct.

**UPDATED: `skills/design/scripts/test-plan-review-loop.sh`** (#2764)

Add a fourth integration test case after the existing three. Stub three reviewer slots, each emitting one OOS row and one FINDING row (per-reviewer numbering restarts at 1, reproducing the #2764 scenario), run `plan-review-loop.sh` end-to-end, and assert:

- `$DESIGN_TMPDIR/findings.md` contains exactly one `### OOS_1:`, one `### OOS_2:`, one `### OOS_3:` (no duplicates).
- `$DESIGN_TMPDIR/findings.md` contains FINDING headings with strictly monotonically increasing IDs starting at 1.
- `$DESIGN_TMPDIR/ballot.txt` exists, non-empty, with the same heading-uniqueness guarantees.
- Tally run completes without rc=2 from `split_ballot_to_blocks`.

Extend the existing `write_dispatch_one_slot` / `write_collect` stub helpers (or add `write_dispatch_three_slots` + `write_collect three_distinct`) to emit a 3-slot `plan-review-slots.ndjson`, a 3-row `panel-paths.txt`, and a `<reviewer>.tsv` per path with one `in_scope` (FINDING) and one `out_of_scope` (OOS) row, with distinct `what` text per reviewer so Jaccard merging does NOT collapse them. Use the same `run_loop` / `LARCH_AGGREGATOR_DISABLED=1` machinery as the existing cases.

**UPDATED: `skills/design/SKILL.md`** (#2780 Bug 1 + Bug 2)

Two edits:

1. **Step 0b tier mapping** (lines ~195-197) — make `design_classification` explicit per tier:

   ```diff
   -- `trivial`: `sketch_budget=0`, `quick_mode=true`, `review_budget=quick`, `workflow_path=SIMPLE` (classification follows existing trivial doc-only carve-out when the router scan applies).
   -- `simple`: `sketch_budget=2`, `quick_mode=true`, `review_budget=full`, `workflow_path=SIMPLE`.
   -- `hard`: `sketch_budget=4`, `quick_mode=false`, `review_budget=full`, `workflow_path=HARD`.
   +- `trivial`: `design_classification=TRIVIAL_DOC_ONLY`, `sketch_budget=0`, `quick_mode=true`, `review_budget=quick`, `workflow_path=SIMPLE`.
   +- `simple`: `design_classification=SIMPLE`, `sketch_budget=2`, `quick_mode=true`, `review_budget=full`, `workflow_path=SIMPLE`.
   +- `hard`: `design_classification=HARD`, `sketch_budget=4`, `quick_mode=false`, `review_budget=full`, `workflow_path=HARD`.
   ```

2. **`SUMMARY_MODE_STRING` jq filter** at three sites (lines ~260, ~894, ~896) — replace `.classification` with `.design_classification`:

   ```diff
   -SUMMARY_MODE_STRING="$(jq -r '.classification // "N/A"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo N/A)"
   +SUMMARY_MODE_STRING="$(jq -r '.design_classification // "N/A"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo N/A)"
   ```

   Apply the same diff at the two Step 5c sites (items 7 and 9) where `--mode "$(jq -r '.classification ...')"` appears inline in `render-final-summary.sh` invocations.

**UPDATED: `skills/design/references/flags.md`** (#2780 Bug 1)

Mirror the Step 0b explicit `design_classification` mapping in the public flag descriptions (around lines 15-17). Replace the parenthetical "the trivial doc-only carve-out follows the Step 0 router scan in `SKILL.md`" with an explicit token mapping consistent with the SKILL.md change. Same three tier lines, same token values (`TRIVIAL_DOC_ONLY` / `SIMPLE` / `HARD`).

**UPDATED: `scripts/lib-voter-parse-rate.sh`** (#2778 sub-task 1, originally #2770)

Add a short comment immediately above `VOTER_PARSE_RATE_RETRY_PREFIX_CODE` (line ~10) documenting the CODE-vs-PLAN ballot-ID asymmetry, so future readers maintaining either preamble can see the constraint at a glance:

```diff
+# CODE ballots are FINDING-only by design (no OOS ids); PLAN ballots accept
+# both FINDING_N and OOS_N. If CODE ballots ever grow OOS support, update
+# VOTER_PARSE_RATE_RETRY_PREFIX_CODE to mirror the PLAN preamble wording.
 VOTER_PARSE_RATE_RETRY_PREFIX_CODE='IMPORTANT: ... Each line MUST start with FINDING_N: followed by ...'
```

No behavior change. Pure docstring annotation.

**UPDATED: `scripts/tracking-issue-read.sh`** (#2778 sub-task 2, originally #2772)

In the file header output-contract list (lines ~25-29), add `RUN_ID` to the `--sentinel`-only emission alongside `ISSUE_NUMBER` and `ADOPTED`. The implementation at lines 268-278 already emits `emit_kv RUN_ID "$RUN_ID_VAL"`; the header docstring just needs to reflect it. Suggested wording:

```diff
 #   ISSUE_NUMBER=<N or empty>
 #   TASK_SOURCE=issue-plus-prompt|issue-only|prompt  (omitted for --sentinel)
 #   TASK_FILE=<path>                                  (omitted for --sentinel)
+#   RUN_ID=<id or empty>                              (only --sentinel)
 #   ADOPTED=<true|false|>                             (only --sentinel; strict
```

(Or place the `RUN_ID` line in the order that best matches the emission order in code.) Pure docstring change.

### Approach

All five fixes are localized and mechanical. The dedup fix (#2764) is the only one requiring code-level reasoning — Option A from the original issue body is chosen because the unified splitter eliminates the FINDING/OOS asymmetry at the source rather than patching it twice. The SKILL.md, `flags.md`, `lib-voter-parse-rate.sh`, and `tracking-issue-read.sh` edits are pure prescription/docstring corrections.

Downstream code paths require no changes for any of the five fixes.

### Edge cases

- **Empty / whitespace-only input** to `split_all_blocks`: `re.split` returns `['']`; loop guards drop empty chunks.
- **Single heading with no body**: classified correctly; renumber loop still works.
- **Mixed FINDING/OOS interleaved within one reviewer's contribution**: each block cleanly bounded by next-heading lookahead.
- **Leading blank-line padding** from `_findings_tmp` concatenation: captured into discarded prefix chunk.
- **`dedup()` Jaccard merge** now operates on correct concern text instead of multi-block tails.
- **Optional defensive `write-run-params.sh` synonym** (`TRIVIAL` → `TRIVIAL_DOC_ONLY`): explicitly NOT included; prompt fix alone closes the failure mode.
- **`render-final-summary.sh` opaque `--mode`**: NOT defensively normalized; SKILL.md jq-filter fix is sufficient.
- **`lib-voter-parse-rate.sh` comment placement**: keep it above the CODE constant only; the PLAN constant already mentions both `FINDING_N: or OOS_N:` and is self-documenting.

### Failure modes

- **Risk: unified regex over-matches `### FINDING_5:` inside fenced code** — out-of-scope: TSV emitter never wraps headings in code fences.
- **Risk: aggregator masks remaining FINDING duplicates** — source-level fix removes the leak so the aggregator never sees duplicates.
- **Risk: SKILL.md edits break unrelated callers of `run-params.json`** — none exist; `design_classification` is the field name in every consumer that reads this file.
- **Risk: docstring edits in `lib-voter-parse-rate.sh` / `tracking-issue-read.sh` accidentally break consumers** — both edits are comment-only; no logic surface changes.
- **Risk: regression test passes against buggy dedup code** — guarded by explicit OOS heading-uniqueness assertion.

### Testing strategy

- Run `bash skills/design/scripts/test-plan-review-loop.sh` — confirm all four cases pass (three pre-existing + new 3-reviewer fixture).
- Run `make lint` — confirm structural pins (`scripts/test-design-structure.sh`, `scripts/test-tracking-issue-read.sh` if present, etc.) still pass with the SKILL.md and `scripts/` docstring edits.
- Manual smoke: run `/design --trivial <issue>` on any small bug after the PR lands, and verify (a) Step 0b accepts trivial without recovery downgrade, (b) the `larch:final-summary` comment shows `**Mode**: TRIVIAL_DOC_ONLY` rather than `**Mode**: N/A`, (c) a subsequent `/design --simple` multi-reviewer run does not trip the dedup splitter.
- Optional regression guard: extend `skills/design/scripts/test-design-structure.sh` with a grep assertion that no SKILL.md fenced block references `.classification` from `run-params.json` (only the valid fields). One-line guard; recommended but not strictly required for landing this PR.

diff_lines: 60

## Acceptance

### From #2764

- `skills/design/scripts/plan-review-loop.sh` dedup helper emits unique `### FINDING_N:` and `### OOS_N:` headings regardless of how the per-reviewer TSV emitter numbered each reviewer's items.
- `findings.md`, `findings-oos.md`, and `ballot.txt` all contain monotonically increasing OOS and FINDING IDs with no duplicates.
- `tally-plan-review.sh` accepts the ballot (no `rc=2` from `split_ballot_to_blocks`) on any input shape where the per-reviewer TSV emitter restarted numbering at 1.
- Regression fixture in `test-plan-review-loop.sh` reproduces the 3-reviewer / each-emits-OOS_1 scenario and asserts the post-dedup heading set.
- The misleading aggregator footer `No \`### OOS_N:\` blocks were present in the supplied input.` no longer contradicts the ballot body.

### From #2780

- `skills/design/SKILL.md` Step 0b explicitly states the `design_classification` token for each tier (trivial → `TRIVIAL_DOC_ONLY`, simple → `SIMPLE`, hard → `HARD`).
- `skills/design/references/flags.md` mirrors the explicit Step 0b mapping in the public flag descriptions.
- A subsequent `/design` invocation with each tier selection reaches Step 0b and runs `write-run-params.sh` successfully without orchestrator inference.
- All three `jq -r '.classification // "N/A"'` filters in `skills/design/SKILL.md` (lines ~260, ~894, ~896) are replaced with `.design_classification`.
- A subsequent `/design` invocation renders `**Mode**: TRIVIAL_DOC_ONLY` (or `SIMPLE` / `HARD`) in `final-summary.md` and the upserted `larch:final-summary` issue comment, rather than `**Mode**: N/A`.

### From #2778

- `scripts/lib-voter-parse-rate.sh` carries a brief comment above `VOTER_PARSE_RATE_RETRY_PREFIX_CODE` explicitly documenting that CODE ballots are FINDING-only by design and pointing maintainers at the PLAN preamble for future OOS support.
- `scripts/tracking-issue-read.sh` file-header output contract for `--sentinel` includes `RUN_ID` alongside `ISSUE_NUMBER` and `ADOPTED`, matching the implementation at lines 268-278.
- #2778 sub-task 3 (originally #2773) is re-verified at PR time via `grep -n 'get-issue-context\|upstream-context\.log\|\|\| true' skills/implement/SKILL.md`. If the cited constructs are absent (the state at plan composition), no code change is required and the verification is recorded in the PR body. If present, an explicit `append-tool-failure.sh` invocation is added before the existing abort path.

diff_lines: 60

## Test plan
(no test plan section in plan-file)
