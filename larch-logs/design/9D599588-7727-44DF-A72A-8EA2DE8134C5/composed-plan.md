## Plan

Fix the plan-review dedup splitter in `skills/design/scripts/plan-review-loop.sh` so it terminates at any `### (FINDING|OOS)_N:` heading rather than only at headings of a single prefix. Apply Option A from the issue body: replace the prefix-keyed `split_blocks(text, prefix)` helper with a unified `split_all_blocks(text)` that classifies each block by its leading heading. Extend `skills/design/scripts/test-plan-review-loop.sh` with a 3-reviewer regression fixture that exercises both OOS and FINDING dedup paths.

### Files to modify

**UPDATED: `skills/design/scripts/plan-review-loop.sh`**

Modify the Python dedup helper heredoc (currently at lines ~373-474):

1. Replace the `split_blocks(text, prefix)` function definition (~lines 395-403) with a unified `split_all_blocks(text)` that splits at any FINDING/OOS heading and classifies each block by the kind of its own leading heading:

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

2. Replace the two `split_blocks(raw, "FINDING")` / `split_blocks(raw, "OOS")` calls inside `main()` (~lines 453-454) with one `fins, oos = split_all_blocks(raw)`. Delete the now-unused `split_blocks` definition. Keep the existing `dedup()`, `what_text()`, `merge_reviewers()` helpers and the renumbering loop at lines 462-466 unchanged — they already operate correctly on cleanly-bounded blocks.

No other changes to `plan-review-loop.sh` (the `findings-oos.md` extraction at lines 499-504 already uses a regex that terminates at any `### ` heading and is correct).

**UPDATED: `skills/design/scripts/test-plan-review-loop.sh`**

Add a fourth integration test case at the end of the existing three cases. The case stubs **three reviewer slots** with one OOS row and one FINDING row each (per-reviewer numbering restarts at 1 inside the existing TSV emitter, reproducing the #2764 scenario), then runs `plan-review-loop.sh` end-to-end and asserts:

- `$DESIGN_TMPDIR/findings.md` contains exactly one `### OOS_1:`, exactly one `### OOS_2:`, exactly one `### OOS_3:` (no duplicates).
- `$DESIGN_TMPDIR/findings.md` contains FINDING headings with strictly monotonically increasing IDs starting at 1 (no duplicate `### FINDING_N:` headings).
- `$DESIGN_TMPDIR/ballot.txt` exists, non-empty, with the same heading-uniqueness guarantees.
- The downstream tally run completes without `rc=2` from `split_ballot_to_blocks` ("duplicate or malformed FINDING/OOS headings in ballot").

Implementation shape: extend the existing `write_dispatch_one_slot` / `write_collect` stub helpers (or add `write_dispatch_three_slots` + `write_collect three_distinct`) to emit:
- A `plan-review-slots.ndjson` with three slot entries (e.g., `cursor-plan-arch`, `cursor-plan-edge`, `cursor-plan-pragmatic`).
- A `panel-paths.txt` with three reviewer output paths.
- A `<reviewer>.tsv` per path containing exactly two rows: one `in_scope` (the FINDING) and one `out_of_scope` (the OOS), with distinct `what` text per reviewer so Jaccard merging does NOT collapse them.

Use the same `run_loop`/`LARCH_AGGREGATOR_DISABLED=1` machinery as the existing cases.

### Approach

The bug is localized to two lines (`fins = split_blocks(raw, "FINDING")` / `oos = split_blocks(raw, "OOS")`) and one helper definition (`split_blocks(text, prefix)`). Option A is preferred over Option B (trim trailing content per block) because (a) the diff is smaller (one helper replaces one), (b) the unified splitter eliminates the asymmetry between FINDING and OOS handling at the source rather than patching it twice, and (c) the unified regex `(?m)^(?=### (?:FINDING|OOS)_[0-9]+:)` is a faithful structural match.

Downstream code paths (LLM aggregator on `findings-in-scope.md`, ballot composition, tally, voting) require no changes.

### Edge cases

- Empty / whitespace-only input → loop guards drop empty chunks, `fins` / `oos` empty.
- Single heading with no body → classified correctly; renumber still works.
- Mixed FINDING/OOS interleaved within one reviewer's contribution → each block cleanly bounded by next-heading lookahead.
- Leading blank-line padding from `_findings_tmp` concatenation → captured into discarded prefix chunk.
- `dedup()` Jaccard merge now operates on correct concern text instead of multi-block tails.

### Failure modes

- Regex over-match inside fenced code → out-of-scope (TSV emitter never wraps headings in fences).
- Aggregator masks remaining bugs → source-level fix removes the leak so aggregator never sees duplicates.
- Test could pass against buggy code → guarded by explicit OOS heading-uniqueness assertion (the documented failure mode).

### Testing strategy

Add the 3-reviewer fixture to `skills/design/scripts/test-plan-review-loop.sh`. Run `bash skills/design/scripts/test-plan-review-loop.sh` and `make lint`; confirm the pre-existing 3 cases still pass and the new 4th case verifies unique heading IDs in `findings.md`/`ballot.txt` and clean tally exit.

## Acceptance

- `skills/design/scripts/plan-review-loop.sh` dedup helper emits unique `### FINDING_N:` and `### OOS_N:` headings regardless of how the per-reviewer TSV emitter numbered each reviewer's items.
- `findings.md`, `findings-oos.md`, and `ballot.txt` all contain monotonically increasing OOS and FINDING IDs with no duplicates.
- `tally-plan-review.sh` accepts the ballot (no `rc=2` from `split_ballot_to_blocks`) on any input shape where the per-reviewer TSV emitter restarted numbering at 1.
- Regression fixture in `test-plan-review-loop.sh` reproduces the 3-reviewer / each-emits-OOS_1 scenario and asserts the post-dedup heading set.
- The misleading aggregator footer `No \`### OOS_N:\` blocks were present in the supplied input.` no longer contradicts the ballot body.

diff_lines: 40
