## Goal
Fix paired-PID prose conflicts in research/validation docs, add defensive unset LARCH_PAIRED_PID_FILE guards to all dispatch-with-waterfall.sh callers with linter enforcement, and implement a fallback_group dedup mechanism in dispatch-with-waterfall.sh to prevent double Codex launches in paired vendor slots.

## Implementation Plan
## Plan

Reconcile paired-PID prose conflicts in research/validation phase docs, add defensive `unset LARCH_PAIRED_PID_FILE` to every caller of `dispatch-with-waterfall.sh` with linter enforcement that handles variable-backed invocations, and add a dual-vendor-slot dedup mechanism (`fallback_group`) to `dispatch-with-waterfall.sh` that is wired into the production manifest producers, serializes within a group, tracks every phase OK result (not just phase-2 fallback), registers reused slots in the existing output bookkeeping, and validates TSV ledger fields.

### Files to modify/create

#### UPDATED: `skills/research/references/research-phase.md`
Replace the post-fence prose at line 215 (`Use \`timeout: 1860000\` on the Bash tool call. Do NOT set \`run_in_background: true\`.`) with: `Use \`run_in_background: true\` and \`timeout: 1860000\` on the Bash tool call. The paired \`breadcrumb-monitor.sh\` invocation in the same message provides the synchronization point and surfaces live breadcrumbs while the collector runs.` The fence body (lines 184-214 — env-var allocation, `# Tool JSON: run_in_background: true` comment, `# Background pair required: see BASH_AUTHORING.md §4` comment, paired `breadcrumb-monitor.sh` invocation with `--paired-pid-file`) and the `**⚠ Background required — must be paired with breadcrumb-monitor.sh.**` banner at line 188 are already correct and MUST be preserved byte-for-byte.

#### UPDATED: `skills/research/references/validation-phase.md`
Identical reconciliation for the post-fence prose at line 209 — same replacement text as research-phase.md. Banner at line 182 and fence body (lines 184-206) are already correct and MUST be preserved byte-for-byte.

#### UPDATED: `skills/design/scripts/dispatch-plan-review-panel.sh`
Two changes:
1. Add `unset LARCH_PAIRED_PID_FILE` on its own line immediately before line 140 (the actual `_dispatch_out=$("$DISPATCH_WATERFALL_SH" \` invocation), so the line is at most 1 line before the call (well within the 5-line look-back window).
2. Wire `fallback_group` into BOTH manifest builders. In the static archetype loop (lines 84-97), add `--arg fallback_group "plan-${_archetype}"` to both `jq -nc` rows (cursor and codex) and merge the field into the produced object (`{slot,tool,output,prompt_file,fallback_group:$fallback_group}`). In the dynamic slots loop (lines 109-120), add `--arg fallback_group "plan-dyn-${_slug}"` to both `jq -nc` rows (`dyn-cursor-plan-${_slug}` and `dyn-codex-plan-${_slug}`) and merge the field into the produced object the same way. Both paired vendor rows in a single archetype share the same group string.

#### UPDATED: `skills/design/scripts/decompose-panel-dispatch.sh`
Two changes:
1. Add `unset LARCH_PAIRED_PID_FILE` on its own line immediately before line 153 (the actual `_dispatch_out=$("$WATERFALL_SH" \` invocation). Single callsite — the `:171` mention in the original issue is a `--tool "dispatch-with-waterfall.sh"` diagnostic argument inside an `append-execution-issue.sh` call, NOT an invocation; the linter rule (below) must exclude diagnostic-string mentions from the anchor set.
2. Wire `fallback_group` into the paired manifest builders (lines 131-142). Add `--arg fallback_group "decomp-${_a}"` to both `jq -nc` rows (`decomp-cursor-${_a}` and `decomp-codex-${_a}`) and merge the field into the produced object (`{slot,tool,output,prompt_file,fallback_group:$fallback_group}`).

#### UPDATED: `skills/design/scripts/decompose-aggregator.sh`
Single change: add `unset LARCH_PAIRED_PID_FILE` on its own line immediately before line 116 (the actual `_agg_out=$("$WATERFALL_SH" \` invocation). The aggregator is a single-slot caller — do NOT add `fallback_group` here (no paired vendor row exists, so dedup is inapplicable).

#### UPDATED: `skills/review/scripts/aggregate-findings.sh`
Single change: add `unset LARCH_PAIRED_PID_FILE` on its own line immediately before line 730 (the actual `"$DISPATCH_SH" \` invocation, which lives inside the per-loop dispatcher body). Single-slot caller — do NOT add `fallback_group`.

#### UPDATED: `skills/review/scripts/dispatch-panel.sh`
Single change: add `unset LARCH_PAIRED_PID_FILE` on its own line immediately before line 404 (the actual `waterfall_output=$("$DISPATCH_WATERFALL" "${waterfall_args[@]}")` invocation). Line 25 is a variable definition (`DISPATCH_WATERFALL="$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"`), NOT an invocation, and must be excluded from the linter anchor set via the variable-backed scanning rule (below).

#### UPDATED: `scripts/lint-foreground-markers.sh`
Add a shell-script scanner that enforces the parent-unset-before-nested-Family-B-child invariant AND handles variable-backed invocations:
- Define a new global token `PARENT_UNSET_REQUIRED_CHILDREN` (newline-delimited list) containing `dispatch-with-waterfall.sh`. Future nested-only Family B children can be added here.
- Add a new function `scan_shell_file_for_unset_before_nested_child(path)` that operates in two passes per file:
  - **Pass 1 (variable resolution)**: walk the file line-by-line and capture simple assignments of any child basename into a variable. Match shell-assignment forms `NAME="$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"`, `NAME=...dispatch-with-waterfall.sh` (any path ending in the basename), and `NAME="${OTHER:-...dispatch-with-waterfall.sh}"` (default-expansion form used by `DISPATCH_PLAN_REVIEW_WATERFALL_SH` / `DECOMPOSE_PANEL_WATERFALL_SH` / `AGGREGATE_DISPATCH_SH`). Store `NAME` in a session-local newline-delimited file (Bash 3.2 compatible — no `declare -A`) as `<varname>\t<basename>` rows. Skip assignments where the right-hand side contains command substitution (`$(...)`) that does not literally resolve at scan time.
  - **Pass 2 (invocation scan)**: walk the file again, treat each line as a candidate invocation. A line is an INVOCATION anchor if (a) the basename appears as a final path segment in a command position (existing `is_anchor_for_basename` logic) AND it is not inside a `--tool "..."` or similar diagnostic-string argument, OR (b) the line invokes a variable captured in Pass 1 in command position: shapes `"$NAME" args`, `$NAME args`, `_x=$("$NAME" args)`, `_x=$("$NAME" "${args[@]}")`. For each anchor line, look BACK up to 5 NON-BLANK NON-COMMENT lines (excluding `#`-only and pure-whitespace lines) for an `unset LARCH_PAIRED_PID_FILE` statement. When no preceding `unset` is found, emit `printf '%s:%s: missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested %s\n' "$rel" "$line_num" "$bn" >&2` and increment `VIOLATIONS`.
- Add a per-line suppression escape hatch: lines ending in `# lint-foreground-markers: ok <reason>` are excluded from the new rule (mirror existing inline-suppression patterns elsewhere in the linter).
- Add a second top-level traversal loop after the existing markdown loop at line 506-508: walk `scripts/*.sh`, `skills/*/scripts/*.sh`, and `skills/shared/scripts/*.sh` if it exists. Exclude `larch-logs/**`, any `*/test-*.sh`, and the script that IS the child (`scripts/dispatch-with-waterfall.sh` itself). Call `scan_shell_file_for_unset_before_nested_child` on each.
- The existing markdown scanning behavior is unchanged.

Also add a NEW markdown post-fence prose check: in `scan_markdown_file`, after a fenced block closes whose body contained both `run_in_background: true` AND `breadcrumb-monitor.sh`, scan the NEXT 10 markdown lines for the contradictory phrase `Do NOT set \`run_in_background: true\`` (allow whitespace and prefix punctuation around the phrase; case-sensitive on `run_in_background`). When matched, emit `printf '%s:%s: contradictory post-fence prose "Do NOT set run_in_background: true" after background+monitor fence\n' "$rel" "$line_num" >&2` and increment `VIOLATIONS`. Use the same `# lint-foreground-markers: ok <reason>` inline-suppression mechanism.

#### UPDATED: `scripts/lint-foreground-markers.md`
Add two new sections:
1. **Parent-unset rule** (shell-script linter): trigger pattern (basename-anchored OR variable-backed invocation of `dispatch-with-waterfall.sh`), required pre-call statement (`unset LARCH_PAIRED_PID_FILE` within prior 5 NON-BLANK NON-COMMENT lines), excluded paths (`larch-logs/**`, `*/test-*.sh`, the child script itself), excluded shapes (`--tool "<basename>"` diagnostic strings, variable definitions without invocation), variable-assignment recognition list (default-expansion form supported), suppression syntax (`# lint-foreground-markers: ok <reason>`), and rationale (paired-PID file is owned only by top-level Family B writers per `BASH_AUTHORING.md` §4; nested children must not inherit it).
2. **Post-fence contradiction rule** (markdown linter): after a background+monitor fence (run_in_background: true + breadcrumb-monitor.sh), scan the next 10 markdown lines for `Do NOT set \`run_in_background: true\``. Required to prevent the research-phase.md / validation-phase.md regression pattern.

#### UPDATED: `scripts/test-lint-foreground-markers.sh`
Add regression coverage for BOTH new rules:
- **Parent-unset positive cases**:
  - Fixture invoking `dispatch-with-waterfall.sh` literally without preceding `unset` — lint exits non-zero.
  - Fixture invoking `"$WATERFALL_SH"` after an earlier `WATERFALL_SH=".../dispatch-with-waterfall.sh"` assignment, without preceding `unset` — lint exits non-zero (variable-backed path).
  - Fixture invoking `"$DISPATCH_WATERFALL_SH"` after a default-expansion assignment `DISPATCH_WATERFALL_SH="${EXTERNAL:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"`, without preceding `unset` — lint exits non-zero.
- **Parent-unset negative cases (compliant)**:
  - Fixture with `unset LARCH_PAIRED_PID_FILE` 1, 3, and 5 NON-BLANK NON-COMMENT lines before a literal invocation — all pass.
  - Same with variable-backed invocation — all pass.
- **Parent-unset distance edge**: `unset` 6+ non-blank lines before invocation — lint exits non-zero (look-back boundary).
- **Parent-unset suppression**: invocation tagged `# lint-foreground-markers: ok <reason>` without preceding `unset` — lint exits zero.
- **Parent-unset carve-outs**: `test-*.sh` fixture (in test directory) ignored; the `--tool "dispatch-with-waterfall.sh"` diagnostic-string shape not anchored.
- **Post-fence prose positive**: fixture markdown with a background+monitor fence followed by `Do NOT set \`run_in_background: true\`` within 10 lines — lint exits non-zero.
- **Post-fence prose negative**: fixture with a background+monitor fence followed by valid prose — lint exits zero.
- **Post-fence prose suppression**: contradictory line with trailing `# lint-foreground-markers: ok <reason>` — exits zero.
Fixtures live in the existing `$BATS_TMPDIR/lint-foreground-markers-XXXX/` temp-dir pattern from the file.

#### UPDATED: `scripts/dispatch-with-waterfall.sh`
Add the `fallback_group` dedup mechanism with phase-aware ledger, group-serialized phase-2, ledger anchoring, TSV validation, and reused-slot bookkeeping:

1. **Manifest parse (Bash 3.2 compatible)**: when parsing the slots NDJSON, populate parallel arrays `slot_names[]`, `slot_tools[]`, `slot_outputs[]`, `slot_prompt_files[]`, and a NEW `slot_fallback_groups[]`. Use `jq -r '.fallback_group // empty'` (or `jq -r 'if has("fallback_group") then .fallback_group else "" end'`) to extract per-row; empty string means "no group, legacy path".

2. **TSV-safety validation** (immediately after manifest parse): for each non-empty `slot_fallback_groups[i]` and `slot_names[i]` and `slot_outputs[i]`, REJECT any value containing tab (`$'\t'`), CR (`$'\r'`), or LF (`$'\n'`). On rejection, write a `STEP_FAILED=MANIFEST_VALIDATION` line to stdout, emit a diagnostic to stderr, and exit non-zero.

3. **Ledger anchoring**: derive the per-call tmpdir from `dirname` of the resolved slots-file path passed via `--slots-file`, then create `<tmpdir>/waterfall-group-results.tsv` (touch on first ledger write). Do NOT read `RESEARCH_TMPDIR`/`DESIGN_TMPDIR`/`REVIEW_TMPDIR` env vars in the dispatcher — anchoring solely on slots-file dirname avoids cross-run leakage. Resolve `--slots-file` via `realpath` (or `readlink -f` fallback) before computing `dirname`.

4. **Ledger schema (TSV, single-token status)**: rows are 5 tab-separated fields: `group<TAB>slot_name<TAB>tool<TAB>output_path<TAB>status`. The status field is a SINGLE token: `ok` for primary success or fresh fallback success; `reused` for a slot that copied another slot's result. (No comma-embedded `OK,reused` form.) Add `source_slot` as an OPTIONAL 6th column ONLY on `reused` rows.

5. **Phase-1 ledger writes**: in `collect_phase` (or wherever phase-1 collection settles), for every slot `i` whose `slot_fallback_groups[i]` is non-empty AND whose phase-1 STATUS is OK, atomically append a ledger row `<group><TAB><slot_name><TAB><tool><TAB><output_path><TAB>ok`. Use `printf '%s\t%s\t%s\t%s\t%s\n' ... >>"$ledger"`.

6. **Group-serialized phase-2 dispatch** (addresses the race): change phase-2 launch logic from "background all queued phase-2 slots, then `wait` once" to per-group serialization for grouped slots:
   - **Ungrouped slots** (`slot_fallback_groups[i]` empty): launch in parallel as today.
   - **Grouped slots**: for each unique `fallback_group` in the queued phase-2 set, iterate group members ONE AT A TIME within that group. Before launching each member: scan the ledger for an existing `ok` row matching `(fallback_group, fallback_tool)`. **Match found**: invoke the `reuse_slot_result(idx, source_row)` helper (item 7) instead of launching. **No match**: launch the slot normally, wait for completion, write the resulting ledger row, then proceed to the next group member.
   - Within a group, members are strictly sequential. Inter-group phase-2 may run in parallel if implementation allows.

7. **Reused-slot bookkeeping helper** (`reuse_slot_result(idx, source_slot_name, source_output_path, source_tool)`):
   - Copy `source_output_path` content to `slot_outputs[idx]` (preserve permissions).
   - Write a sidecar `${slot_outputs[idx]}.dedup` with exactly two lines `DEDUPE_REUSED_FROM=<source_slot_name>` and `DEDUPE_REUSED_TOOL=<source_tool>`.
   - Append a ledger row with status `reused` and the optional `source_slot` 6th column.
   - Emit structured KV breadcrumbs: `DEDUPE_REUSED=true`, `DEDUPE_REUSED_FROM=<source_slot_name>`, `DEDUPE_REUSED_TOOL=<source_tool>`.
   - Set `final_outputs[idx]="${slot_outputs[idx]}"` and `final_tools[idx]="$source_tool"`.
   - Mark `idx` as excluded from any subsequent phase collection (add to a `_reused_indices` newline-delimited file the phase-3 fallback loop reads to skip).

8. **Backward compatibility**: when `slot_fallback_groups[i]` is empty for ALL slots, skip ALL ledger logic. Dispatcher behavior is byte-equivalent to pre-change.

#### UPDATED: `scripts/dispatch-with-waterfall.md`
Document the new optional `fallback_group` manifest field, the ledger file location (`<dirname-of-slots-file>/waterfall-group-results.tsv`) and the 5-or-6-field TSV schema with single-token `status` (`ok` / `reused`), the phase-1+phase-2 OK row writing semantics, the group-serialized phase-2 invariant ("within a fallback_group, phase-2 launches are sequential; ungrouped slots remain parallel"), the reused-slot contract (`.dedup` sidecar schema, `DEDUPE_REUSED_FROM`/`DEDUPE_REUSED_TOOL` KV breadcrumbs, bookkeeping integration with `final_outputs`/`final_tools`), and the absence semantics (no group → no ledger, byte-equivalent legacy behavior). Add a worked example with `decomp-cursor-arch` + `decomp-codex-arch` paired with `fallback_group="decomp-arch"`: phase-1 codex succeeds, phase-1 cursor fails → cursor's phase-2 reuses codex result, emits `DEDUPE_REUSED_FROM=decomp-codex-arch`.

#### UPDATED: `scripts/test-dispatch-with-waterfall.sh`
Add regression coverage for the new dedup mechanism:
- **No-dedup baseline**: existing tests pass unchanged (no `fallback_group` → legacy path).
- **Single-group two-slot phase-2 dedup hit (both primaries fail)**: assert exactly one Codex process across the group.
- **Phase-1 OK + phase-1 fail (the explicit OOS-2898 scenario)**: assert zero Codex launches in phase-2; output reuse.
- **Cross-group isolation**: two groups, both Codex launches fire (no cross-group dedup).
- **Mixed manifest**: A grouped, B ungrouped — A participates, B legacy path.
- **Reused slot is settled in final arrays**: `ALL_OUTPUT_FILES` contains the reused slot; not in phase-3 Claude fallback queue.
- **`.dedup` sidecar contract**: reused slot produces the two-line sidecar.
- **TSV validation rejection**: manifest with `fallback_group` containing tab/CR/LF → `STEP_FAILED=MANIFEST_VALIDATION` exit.
- **Counter-based launch assertions**: stub `LAUNCH_REVIEW_SH` increments a counter on each Codex launch; assert exact counts (0, 1, or 2).

Use the existing fixture-temp-dir pattern.

#### UPDATED: `skills/design/scripts/test-decompose-panel-dispatch.sh`
Add an assertion that the produced manifest emits paired `fallback_group="decomp-${archetype}"` for both vendor rows in every archetype. Verify (a) field present on every row, (b) two paired rows for the same archetype share the same value, (c) value matches the expected `decomp-<archetype>` pattern.

#### NEW: `skills/design/scripts/test-dispatch-plan-review-panel-manifest.sh`
A test asserting (a) static archetype rows emit `fallback_group="plan-${archetype}"` for both vendor rows, (b) dynamic slot rows emit `fallback_group="plan-dyn-${slug}"` for both vendor rows, (c) every paired vendor row shares the same group value with its peer. If a `test-dispatch-plan-review-panel.sh` already exists, EXTEND it instead and drop this NEW file.

#### UPDATED: `BASH_AUTHORING.md` §4
Three updates: (1) parent-unset narrative explicitly names the `dispatch-with-waterfall.sh` linter enforcement (look-back: 5 non-blank non-comment lines; variable-backed shapes supported; suppression syntax `# lint-foreground-markers: ok <reason>`); (2) note that research/validation phase docs now match the Family B background+monitor pattern and that `lint-foreground-markers.sh` detects post-fence contradictory `Do NOT set run_in_background: true` prose; (3) canonical top-level Family B writer list (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`) unchanged.

### Approach

Three independent fixes share one PR. Sequencing within the PR is critical to avoid mid-merge CI breakage:

1. **Item A first** (prose-only, no executable impact): research-phase.md, validation-phase.md, BASH_AUTHORING.md prose updates.
2. **Item B next** in two steps: (a) add the `unset LARCH_PAIRED_PID_FILE` lines to all five callers BEFORE turning on the new linter rules; (b) extend `lint-foreground-markers.sh` with the parent-unset rule AND the post-fence contradiction rule, plus regression coverage in `test-lint-foreground-markers.sh`. Atomic merge preferred so CI does not break on the intermediate state.
3. **Item C last** (largest behavioral change): add `fallback_group` parsing + ledger + group-serialized phase-2 + reused-slot bookkeeping + TSV validation to `dispatch-with-waterfall.sh`, document in `dispatch-with-waterfall.md`, wire `fallback_group` into the `decompose-panel-dispatch.sh` and `dispatch-plan-review-panel.sh` manifest builders, and add regression coverage in `test-dispatch-with-waterfall.sh` + `test-decompose-panel-dispatch.sh` (+ plan-review panel manifest assertion).

The `fallback_group` field is additive on the manifest schema. Existing callers that do NOT set it skip ALL ledger logic — the dispatcher is byte-equivalent to pre-change. Ledger anchoring uses `dirname` of the resolved `--slots-file` (not env vars) to avoid cross-run leakage. Phase-2 is restructured to per-group serialization so the dedup invariant holds given existing dispatcher concurrency; ungrouped slots keep parallel behavior to preserve performance for non-opted-in callers.

### Edge cases

- `fallback_group` on a single slot (no peer): ledger row written but unread; identical to legacy.
- First slot's Codex fails (no `ok` row): peers launch their own Codex (independent failure path).
- Phase-1 codex-OK + cursor-fail in same group (explicit OOS-2898 scenario): cursor's phase-2 reuses codex result. Test mandatory.
- Slot whose primary tool IS codex: dedup applies symmetrically — ledger `tool` column captures the actual result tool.
- Linter look-back boundary at file top: treat missing `unset` as violation unless suppressed.
- Heredoc / `--tool "..."` diagnostic-string mention: NOT anchored.
- TSV validation: only tab/CR/LF rejected; underscores, hyphens, slashes, dots, alphanumerics all valid.
- Concurrent `/design` + `/implement` dispatchers: each has its own `--slots-file` → per-call ledger anchoring keeps them isolated.

### Failure modes

1. **Dedup race within a group** — group serialization implemented incorrectly. Test: "single-group two-slot phase-2 dedup hit" asserts exactly one Codex. Mitigation: strict per-group sequential loop.
2. **Linter false-positive on legitimate suppression cases** — covered by `# lint-foreground-markers: ok <reason>` inline suppression.
3. **Post-fence contradiction regression** — new linter check fills the gap that `fence_stale_foreground_markers` did not cover; regression test in `test-lint-foreground-markers.sh`.
4. **Reused slot not settled in final arrays** — `reuse_slot_result` MUST perform all four bookkeeping steps; "reused slot is settled" test catches omission.
5. **TSV corruption from buggy manifest** — `STEP_FAILED=MANIFEST_VALIDATION` exit at manifest parse rejects tab/CR/LF.
6. **Ledger anchored under wrong dir if slots-file is relative** — resolve to absolute via `realpath` / `readlink -f` before `dirname`.

### Testing strategy

- `make lint-foreground-markers` (alias `make lint-foreground`) must pass — new parent-unset AND post-fence contradiction rules enforced via the same target.
- `bash scripts/test-lint-foreground-markers.sh` covers literal, variable-backed, default-expansion variable, look-back boundary, suppression, carve-outs, and post-fence prose cases.
- `bash scripts/test-dispatch-with-waterfall.sh` covers all dedup cases including the explicit OOS-2898 phase-1 OK + phase-1 fail scenario.
- `bash skills/design/scripts/test-decompose-panel-dispatch.sh` asserts `fallback_group` is present on every paired manifest row with the expected `decomp-<archetype>` value.
- The new (or extended) plan-review panel manifest test verifies `plan-<archetype>` and `plan-dyn-<slug>`.
- `bash scripts/relevant-checks.sh` (or `make lint`) must pass repo-wide.
- Existing tests (`scripts/test-dispatch-plan-voters.sh`, `scripts/test-dispatch-code-voters.sh`, etc.) continue to pass.
- Spot-check: `grep -L "unset LARCH_PAIRED_PID_FILE"` over the seven dispatch-with-waterfall callers prints nothing.

## Acceptance

- Item A: `skills/research/references/research-phase.md` and `skills/research/references/validation-phase.md` post-fence prose replaced with the background+monitor wording; existing banner and fence body preserved byte-for-byte.
- Item B: All five callers of `dispatch-with-waterfall.sh` (`dispatch-plan-review-panel.sh`, `decompose-panel-dispatch.sh`, `decompose-aggregator.sh`, `aggregate-findings.sh`, `dispatch-panel.sh`) contain `unset LARCH_PAIRED_PID_FILE` within 5 non-blank non-comment lines immediately before the actual invocation line. `grep -L "unset LARCH_PAIRED_PID_FILE"` over these five files plus the pre-existing `dispatch-code-voters.sh` and `dispatch-plan-voters.sh` prints nothing.
- `scripts/lint-foreground-markers.sh` extended with two new rules: shell-script parent-unset (handles literal AND variable-backed invocations, including the default-expansion `${EXTERNAL:-…}` form) and markdown post-fence contradiction (catches `Do NOT set run_in_background: true` after a background+monitor fence). `scripts/lint-foreground-markers.md` documents both rules including suppression syntax. `scripts/test-lint-foreground-markers.sh` covers positive, negative, suppression, distance-edge, and carve-out cases for both rules.
- Item C: `scripts/dispatch-with-waterfall.sh` accepts optional `fallback_group` manifest field; TSV-safety validation rejects tab/CR/LF in `fallback_group`, slot_name, and output_path; ledger anchored at `dirname` of resolved `--slots-file`; phase-1 OK rows written for grouped slots; phase-2 launches serialized within a `fallback_group`; reused slots produce `.dedup` sidecars, `DEDUPE_REUSED_FROM` / `DEDUPE_REUSED_TOOL` KV breadcrumbs, and are settled in `final_outputs` / `final_tools`.
- `skills/design/scripts/decompose-panel-dispatch.sh` jq manifest rows emit `fallback_group="decomp-${archetype}"` on both vendor rows. `skills/design/scripts/dispatch-plan-review-panel.sh` static archetype rows emit `fallback_group="plan-${archetype}"` and dynamic slot rows emit `fallback_group="plan-dyn-${slug}"`, both vendor rows in each archetype share the same group string.
- `skills/design/scripts/test-decompose-panel-dispatch.sh` asserts paired rows share the field with the expected `decomp-<archetype>` value. A test (extension of existing harness or new `test-dispatch-plan-review-panel-manifest.sh`) asserts the analogous invariant for `dispatch-plan-review-panel.sh`.
- `scripts/test-dispatch-with-waterfall.sh` covers: no-dedup baseline, single-group two-slot phase-2 dedup hit (exactly one Codex launch), phase-1 OK + phase-1 fail OOS-2898 scenario (zero Codex launches in phase-2), cross-group isolation, mixed manifest, reused-slot-settled-in-final-arrays, `.dedup` sidecar shape, and TSV validation rejection (tab/CR/LF).
- `BASH_AUTHORING.md` §4 updated with the parent-unset enforcement language and the research/validation prose reconciliation note. Canonical Family B writer list unchanged.
- `make lint-foreground-markers` (alias `make lint-foreground`), `bash scripts/relevant-checks.sh`, and all existing repo tests pass on the modified branch.

diff_lines: 550

## Test plan
(no test plan section in plan-file)
