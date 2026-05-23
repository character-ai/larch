## Goal
Add --paths-file flag to dispatch scripts and collect-agent-results.sh to fix cross-subshell ALL_OUTPUT_FILES persistence hazard in /design Step 3 plan-review

## Implementation Plan
# Implementation Plan: Paths-file additive contract for dispatch + collect cross-subshell handoff

## Plan

Fix the cross-subshell `ALL_OUTPUT_FILES` shell-variable hazard from issue #2637 by introducing an **additive, deterministic paths-file** that all three dispatchers (`dispatch-with-waterfall.sh`, `dispatch-plan-voters.sh`, `dispatch-code-voters.sh`) emit alongside their existing stdout KVs. `collect-agent-results.sh` learns a new `--paths-file <file>` flag that is mutually exclusive with positional output-file arguments and fails closed on empty/missing/unreadable files (preserving the existing anti-pattern-#4 invariant — "never collect zero entries"; the new flag is permitted when it yields at least one non-blank line).

The orchestrator-side change in `skills/design/SKILL.md` Step 3 and `skills/design/references/plan-review.md` replaces the in-memory `ALL_OUTPUT_FILES` parse + `read -r -a _all_output_files <<< "$ALL_OUTPUT_FILES"` snippet with a `--paths-file` invocation that reads the deterministic paths-file written by the dispatcher in the prior Bash block. No shell-variable crosses Bash-tool subshells.

The contract is **strictly additive** at the dispatcher stdout layer: `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, `VOTER_*_PATH`, and every existing emit_kv line is preserved unchanged. The only new emissions are `ALL_OUTPUT_FILES_PATH=<path>` (waterfall) and `VOTER_PATHS_FILE=<path>` (voter dispatchers).

Per the codebase audit (Round 1 Decision 5), the only prompt-side inline cross-subshell hazard exists in `skills/design/SKILL.md` Step 3 + `skills/design/references/plan-review.md`. Other consumers wrap dispatchers inside script wrappers (`skills/review/scripts/dispatch-panel.sh`, `aggregate-findings.sh`, `review-core.sh`) which keep `ALL_OUTPUT_FILES` inside a single subshell, so no edits are needed in `skills/review/`. Voter dispatchers' single-path `VOTER_N_PATH` KVs have no multi-word RHS hazard; their paths-file is symmetric documentation per Round 1 Decision 4 (user-mandated), not a hazard fix.

### Files to modify

#### Dispatchers (additive paths-file emissions)

1. **`scripts/dispatch-with-waterfall.sh`** — Multiple additions:
   - Add `--paths-file <path>` argparse case (optional override). Default path when omitted: `<SLOTS_FILE>.output-files`.
   - **Add an empty-manifest guard** immediately after `slot_count=${#slot_names[@]}` (around line 101): if `slot_count -eq 0`, `larch_err` with a clear "slots file contains no slot rows" message and exit 2. Pre-existing behavior accepted empty manifests and emitted `DISPATCH_OK=true` + empty `ALL_OUTPUT_FILES`; new guard prevents that footgun and is required because the new paths-file consumer relies on at least one valid entry.
   - **Validate output paths reject CR/LF** before writing the paths-file. For each path in `final_outputs[*]`, exit 2 with a clear error if the value contains a literal carriage return or newline character. This protects the line-oriented paths-file format against newline-bearing NDJSON `output` values that the existing jq validator does not catch.
   - **Unconditionally truncate** the resolved paths-file at the start of the write step (before appending paths) so a stale paths-file from an interrupted re-dispatch in the same `$DESIGN_TMPDIR` cannot survive into the next collect block.
   - Write final paths-file via `mktemp` in the same directory + `mv` atomic rename. Emit `ALL_OUTPUT_FILES_PATH=<resolved-path>` via `emit_kv` adjacent to the existing `ALL_OUTPUT_FILES` line. Preserve existing `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` emissions verbatim.

2. **`scripts/dispatch-with-waterfall.md`** — Document the new flag, default-path derivation, the new `ALL_OUTPUT_FILES_PATH` KV, the empty-manifest exit-2 guard, the CR/LF rejection rule, the unconditional truncate-then-write behavior. Behavior is purely additive for existing callers.

3. **`scripts/dispatch-plan-voters.sh`** — After `VOTER_2_PATH` / `VOTER_3_PATH` are resolved (around line 235 emit cluster), write `$DESIGN_TMPDIR/plan-voter-paths.txt` containing both non-empty/non-failed voter paths one-per-line, atomic mv. Emit `VOTER_PATHS_FILE="$DESIGN_TMPDIR/plan-voter-paths.txt"` adjacent to existing `VOTER_*_PATH` lines.

4. **`scripts/dispatch-plan-voters.md`** — Document the new emission + paths-file layout.

5. **`scripts/dispatch-code-voters.sh`** — Write `$REVIEW_TMPDIR/code-voter-paths.txt` (use the existing required `--review-tmpdir` only; no `--design-tmpdir` fallback — the script does not accept it) listing `VOTER_1_PATH`, `VOTER_2_PATH`, `VOTER_3_PATH` one-per-line, skipping empty/skipped voters (round 2+ omits `VOTER_2_PATH`). Emit `VOTER_PATHS_FILE` adjacent to existing `VOTER_*_PATH` lines.

6. **`scripts/dispatch-code-voters.md`** — Document.

#### Collector (mutually-exclusive `--paths-file` consumer)

7. **`scripts/collect-agent-results.sh`** — Argparse + early-population pattern:
   - Add `--paths-file <file>` case to the argparse `while` loop. Set a new local `PATHS_FILE=""` default.
   - **CRITICAL ORDERING**: paths-file parsing must populate `OUTPUT_FILES` **before** the existing `${#OUTPUT_FILES[@]} -eq 0` guard at line ~210-213. The control flow must be: argv parse → mutual-exclusion check → readability/empty checks on PATHS_FILE → populate OUTPUT_FILES from PATHS_FILE → existing "at least one output file is required" guard (now serves as the final invariant covering both positional and paths-file modes).
   - Mutual exclusion: if `PATHS_FILE` non-empty AND `OUTPUT_FILES` already non-empty (from positional args), exit 1 with "`--paths-file` is mutually exclusive with positional output-file arguments".
   - Readability: if `PATHS_FILE` is set but the file is missing/unreadable, exit 1 with "paths-file not readable: <path>".
   - Empty (no non-blank lines): exit 1 with "paths-file contains no entries (preserves anti-pattern #4)".
   - Read loop, Bash 3.2 compatible, treating whitespace-only lines as blank: `while IFS= read -r path; do if [[ "$path" =~ [^[:space:]] ]]; then OUTPUT_FILES+=("$path"); fi; done < "$PATHS_FILE"`. This matches the "no non-blank lines" empty-file rule exactly.
   - **Update the file-header Usage comment block** (currently lines 16-64) to describe `--paths-file` and its mutually-exclusive contract.
   - **Update the `--help` emit string** (currently around line 196) to describe `--paths-file`.

8. **`scripts/collect-agent-results.md`** — Document:
   - The new `--paths-file` flag, mutually-exclusive contract, and each failure mode.
   - **Trust model**: paths-files are dispatcher-written session-local artifacts trusted within the `/design` and `/review` orchestration model. Listed paths drive `wait-for-reviewers.sh` sentinel polling and downstream file reads; a tampered paths-file could aim reads/waits at unintended local paths. Optional defense-in-depth (deferred follow-up): caller-side prefix allowlisting against `$DESIGN_TMPDIR` / `$REVIEW_TMPDIR` if a future surface opens paths-files to less-trusted writers.
   - Cross-reference: the anti-pattern #4 invariant in `skills/design/SKILL.md` is preserved — the new flag is permitted only when it yields at least one non-blank line.

#### Skill prompt updates (replace hazardous snippets)

9. **`skills/design/SKILL.md` Step 3** — Two specific edits:
   - **Update the "Step 2 — Build manifest and dispatch through waterfall" Bash block** (ending around line 591): in the parsing loop, drop the `ALL_OUTPUT_FILES|ALL_OUTPUT_TOOLS` capture branch. Remove the dead `ALL_OUTPUT_FILES=""` and `ALL_OUTPUT_TOOLS=""` initializers. Keep `DISPATCH_OK` and `WARN` capture only. Update the prose immediately following the block: "The dispatcher writes the final output-file list to `$_manifest.output-files` (one path per line). Use that file via `--paths-file` in the next Bash block. The `ALL_OUTPUT_FILES_PATH=<path>` stdout KV gives the explicit location for callers that need it. The `DISPATCH_OK` and `WARN` KVs continue to be parsed here."
   - **Update anti-pattern NEVER #4** (around line 96-98): change from "NEVER call `collect-agent-results.sh` with zero positional arguments" to "NEVER call `collect-agent-results.sh` with zero entries: it must receive at least one output path either via positional arguments OR via a `--paths-file` flag that names a readable file yielding at least one non-blank path-line." Update the "How to apply" line to mention both invocation modes.

10. **`skills/design/references/plan-review.md`** — Replace the existing `read -r -a _all_output_files <<< "$ALL_OUTPUT_FILES"` snippet (around line 78-80) with a single-physical-line `collect-agent-results.sh` invocation that includes the canonical Bash prelude:
    ```bash
    [ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh
    _manifest="$DESIGN_TMPDIR/plan-review-slots.ndjson"
    "${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh" --timeout 1860 --substantive-validation --validation-mode --structured-reviewer-validation --paths-file "$_manifest.output-files"
    ```
    The `collect-agent-results.sh` invocation MUST stay on **one physical line** so `scripts/test-design-structure.sh` Check 7 (lines 216-229) continues to match its single-line grep pipeline pinning issue #661 substantive-validation flags. Update the surrounding prose paragraph to: (a) reference the deterministic paths-file pattern instead of the `ALL_OUTPUT_FILES` shell variable, and (b) retarget Phase-3 `TOOL=claude` correlation — instead of "Phase 3 Claude subprocess outputs will appear in `ALL_OUTPUT_FILES` with `TOOL=claude` in the corresponding `ALL_OUTPUT_TOOLS` position", say "Phase 3 Claude subprocess outputs appear in the paths-file alongside Phase 1/2 outputs; tool attribution per output comes from `collect-agent-results.sh`'s emitted `TOOL=` field for each result block (or each output's `.meta` file's `TOOL=` row), not from `ALL_OUTPUT_TOOLS` positional alignment."

#### Tests (extend existing harnesses + update sibling .md docs)

11. **`scripts/test-dispatch-with-waterfall.sh`** — Extend existing harness. Add assertions:
    - Deterministic paths-file `<slots-file>.output-files` exists after dispatch.
    - File content order + count match `final_outputs` exactly (compare against the dispatcher's pre-`emit_kv` `final_outputs` array — NOT against the post-split `ALL_OUTPUT_FILES` KV, which is lossy for paths with embedded spaces).
    - `ALL_OUTPUT_FILES_PATH=<path>` is emitted on stdout.
    - Backward-compat: existing `ALL_OUTPUT_FILES=<space-separated>` and `ALL_OUTPUT_TOOLS=...` lines still emitted unchanged.
    - `--paths-file <override>` writes to override location and emits that path.
    - Empty-manifest regression: a slots-file with zero rows → dispatcher exits 2 with the new error.
    - CR/LF rejection regression: an NDJSON row whose `output` contains an escaped newline → dispatcher exits 2.

12. **`scripts/test-dispatch-with-waterfall.md`** — Update to reference new assertions per `script-md-siblings.md` edit-in-sync rule.

13. **`scripts/test-dispatch-plan-voters.sh`** — Extend existing harness. Assert `VOTER_PATHS_FILE` emit + file contents (2 paths one-per-line; skipped-voter skip semantics).

14. **`scripts/test-dispatch-plan-voters.md`** — Update to reference new assertions.

15. **`scripts/test-dispatch-code-voters.sh`** — Extend existing harness. Assert `VOTER_PATHS_FILE` emit + file contents for both round 1 (3 paths) and round 2+ (skipping `VOTER_2_PATH`). Section-gating: the harness is split via `--section` Makefile shards (Makefile lines around 594-617); add the new assertions to the section that already exercises the post-dispatch emit block (or add a new dedicated section) and update Makefile targets so every CI shard exercises them.

16. **`scripts/test-dispatch-code-voters.md`** — Update to reference new assertions and to name the affected Makefile section targets.

17. **`scripts/test-collect-agent-results.sh`** — Extend existing harness. Add a new section asserting:
    - Happy path: `--paths-file <file-with-paths>` produces the same output blocks as positional args.
    - Empty file: exit 1 with "paths-file contains no entries".
    - Whitespace-only file: exit 1 with the same "no entries" error.
    - Missing/unreadable file: exit 1 with "paths-file not readable".
    - Mutually exclusive: passing both `--paths-file` and positional args → exit 1.
    - Anti-pattern #4 invariant preserved: zero positional + zero `--paths-file` → existing "at least one output file is required" error.

18. **`scripts/test-collect-agent-results.md`** — Update to reference the new paths-file assertions.

### Edge cases

- **Empty slot manifest**: explicitly rejected by the new dispatcher guard; harness regression locks this in.
- **Newline-bearing NDJSON `output` value**: explicitly rejected by the new CR/LF guard; harness regression locks this in.
- **Whitespace-only line in paths-file**: skipped by the `[[ "$path" =~ [^[:space:]] ]]` check. If the file contains ONLY whitespace-only lines, the empty-entries guard fires.
- **Failed slot in `phase3_failed`**: `final_outputs[idx]` still holds the phase3 output path; paths-file includes it. Collector reports STATUS=FAILED/EMPTY_OUTPUT/etc. — same as before.
- **Concurrent dispatcher runs in same session**: impossible — `/design` enforces single-runner invariant.
- **Re-dispatch within same run** (e.g., dispatch-plan-voters retry path at line 167-186): the retry-waterfall call writes to its own slots-file-derived paths-file. Dispatcher's unconditional truncate-then-write guarantees no stale content survives.

### Failure modes

1. **Paths-file write race** — Mitigation: atomic write via `mktemp` in same directory + `mv`. The `mv` is atomic when target and source are on the same filesystem (always true here).
2. **Caller forgets to read the paths-file and falls back to `ALL_OUTPUT_FILES`** — Existing behavior unchanged; the old space-separated KV still works.
3. **`collect-agent-results.sh --paths-file` accidentally combined with positional args** — Mitigation: mutually-exclusive guard fires with clear error; CI test asserts this.
4. **Stale paths-file from interrupted prior run** — Mitigation: dispatcher unconditionally truncates the paths-file at the start of its write step.

### Testing strategy

- Extend three existing dispatcher harnesses with paths-file assertions; identify Makefile sections for `test-dispatch-code-voters.sh` shard coverage.
- Extend `scripts/test-collect-agent-results.sh` with `--paths-file` happy-path + 5 failure-mode tests.
- Update all four sibling `scripts/test-*.md` files per `script-md-siblings.md`.
- Run `make lint` (agent-lint, lint-bash32, markdownlint pre-commit battery).
- Run `scripts/test-design-structure.sh` to verify Check 7's single-line grep still matches the new `plan-review.md` snippet.
- Manual smoke test: invoke `/design --simple <some-issue>` end-to-end.
- Backward-compat verification: re-run `test-dispatch-with-waterfall.sh` and confirm existing internal `ALL_OUTPUT_FILES` consumers (e.g., `dispatch-plan-voters.sh` line 112) continue to work unmodified.

## Acceptance

Implementation is complete when ALL of the following hold:

1. **`scripts/dispatch-with-waterfall.sh`**: accepts `--paths-file <path>`; writes paths-file (default `<slots-file>.output-files`); emits `ALL_OUTPUT_FILES_PATH=<resolved-path>` on stdout adjacent to existing `ALL_OUTPUT_FILES`.
2. **Empty-manifest rejection**: a slots-file with zero JSON rows causes `dispatch-with-waterfall.sh` to exit 2 with a clear error and produce no paths-file.
3. **CR/LF rejection**: an NDJSON `output` value containing CR or LF causes `dispatch-with-waterfall.sh` to exit 2 before any paths-file write.
4. **Unconditional truncate**: the paths-file is truncated by the dispatcher at the start of each run; stale content from a prior interrupted run cannot survive.
5. **`scripts/dispatch-plan-voters.sh`** emits `VOTER_PATHS_FILE="$DESIGN_TMPDIR/plan-voter-paths.txt"` after the existing `VOTER_*_PATH` emit cluster; file contains one path per non-failed voter slot.
6. **`scripts/dispatch-code-voters.sh`** emits `VOTER_PATHS_FILE="$REVIEW_TMPDIR/code-voter-paths.txt"` (uses only `--review-tmpdir`; no `--design-tmpdir` fallback); file content respects round-1 vs round-2+ semantics (skips `VOTER_2_PATH` in round 2+).
7. **`scripts/collect-agent-results.sh`** accepts `--paths-file <file>`; paths-file population happens **before** the `${#OUTPUT_FILES[@]} -eq 0` guard.
8. **Mutual exclusion**: `collect-agent-results.sh` exits 1 with a clear error when `--paths-file` is combined with positional output-file arguments.
9. **Fail-closed**: `collect-agent-results.sh --paths-file` exits 1 on missing file, unreadable file, empty file, and whitespace-only file.
10. **Anti-pattern #4 preserved**: `collect-agent-results.sh` with zero positionals AND no `--paths-file` still exits 1 with "at least one output file is required".
11. **`skills/design/SKILL.md` Step 3 anti-pattern NEVER #4** amended to permit zero positionals when `--paths-file` is provided.
12. **`skills/design/SKILL.md` Step 3** parse loop drops the `ALL_OUTPUT_FILES|ALL_OUTPUT_TOOLS` case branch and dead initializers; surrounding prose updated to reference the deterministic paths-file pattern.
13. **`skills/design/references/plan-review.md`** collect snippet is single-physical-line (preserves `test-design-structure.sh` Check 7), includes the canonical Bash prelude `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh`, uses `--paths-file "$_manifest.output-files"`, and retargets Phase-3 tool attribution from `ALL_OUTPUT_TOOLS` positions to per-output `TOOL=` from collector/`.meta`.
14. **Backward compat**: existing dispatcher stdout KVs (`ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, `VOTER_*_PATH`, `DISPATCH_OK`, `WARN`, etc.) are preserved unchanged; existing internal consumers (e.g., `dispatch-plan-voters.sh:112`, `dispatch-code-voters.sh:398`) continue to work.
15. **Sibling `.md` updates**: `scripts/test-dispatch-with-waterfall.md`, `scripts/test-dispatch-plan-voters.md`, `scripts/test-dispatch-code-voters.md`, `scripts/test-collect-agent-results.md` reference the new paths-file assertions per `.claude/rules/script-md-siblings.md`.
16. **`collect-agent-results.sh`** file-header Usage comment block AND `--help` output describe `--paths-file` and its mutually-exclusive contract.
17. **`scripts/test-design-structure.sh`** passes — Check 7's single-line grep still matches the new `plan-review.md` snippet.
18. **`scripts/test-dispatch-code-voters.sh`** `--section` shards and Makefile targets cover the new `VOTER_PATHS_FILE` assertions (every CI shard exercises them).
19. **`make lint` passes** (agent-lint S017/desc-no-trigger, lint-bash32, markdownlint, script-md-siblings, drift-prone-prose-in-docs).
20. **End-to-end smoke**: `/design --simple <issue>` Step 3 plan review completes via the new paths-file cross-subshell handoff without the original `ALL_OUTPUT_FILES` `read -r -a` snippet running.

diff_lines: 350

## Test plan
(no test plan section in plan-file)
