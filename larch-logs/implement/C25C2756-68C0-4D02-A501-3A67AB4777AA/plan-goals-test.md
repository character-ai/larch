## Goal
Implement 5 OOS follow-up items for diagnostic sanitization and SKIP_REASON contract (step-7a, sanitize-mermaid, ci-failed-jobs, lib-quiet, test-step-7a)

## Implementation Plan
## Plan

# Implementation Plan — #2897 OOS combined follow-up (5 items)

## Files to modify/create

### UPDATED: `scripts/lib-quiet.sh`
Add a shared `sanitize_diagnostic_line` function. **Do NOT modify `larch_err` or `larch_errf`** — keep them byte-for-byte unchanged so existing multi-line callers (e.g. `git-force-push.sh:71` emitting `git status --porcelain` rows) continue working without LF/tab loss.

Specific edits (Item E — narrowed scope):

1. Define the helper between `larch_quiet_init` and `larch_err` (around line 95, immediately above `larch_err`):

   ```sh
   # Strip C0 control bytes and DEL from a single diagnostic line (stdin).
   # LC_ALL=C keeps tr byte-oriented on BSD/macOS with malformed input.
   # Callers that forward EXTERNAL content into larch_err / larch_errf
   # MUST pipe through this helper explicitly before doing so. Multi-line
   # callers should pipe per line so LF boundaries survive.
   sanitize_diagnostic_line() {
       LC_ALL=C tr -d '[:cntrl:]'
   }
   ```

2. Do NOT modify `larch_err` or `larch_errf`. The OOS Item E concern was that `ci-failed-jobs.sh`'s LOCAL helper duplicates policy and that new scripts forwarding external content would each reinvent it. Promoting the helper to `lib-quiet.sh` (a sourced library) satisfies that without changing the implicit behavior of `larch_err`. Existing multi-line `larch_err` callers (`git-force-push.sh:63,71`, `breadcrumb-monitor.sh` WARN paths) are unaffected.

### UPDATED: `scripts/ci-failed-jobs.sh`
Remove the duplicated local helper and sanitize `job_name` IMMEDIATELY at the parse boundary, BEFORE the non-empty guard, so all-control-byte rows are dropped cleanly.

Specific edits (Items D + E coupling, F2/F5/F7/F12/F16/F21/F34/F36):

1. Delete the local `sanitize_diagnostic_line` definition (current lines 29-33). The helper now lives in `lib-quiet.sh` and is in scope because the file already `source`s `lib-quiet.sh` at line 8.

2. Inside the `while IFS= read -r raw_name` loop (lines 106-145), reorder so sanitization runs FIRST and the non-empty guard runs AFTER sanitization:

   ```sh
   while IFS= read -r raw_name || [ -n "$raw_name" ]; do
       raw_name=$(printf '%s' "$raw_name" | sanitize_diagnostic_line)
       [ -n "$raw_name" ] || continue
       count=$((count + 1))
       …
   done < "$tmp_stdout"
   ```

   This drops all-control-byte names entirely — `count` is not incremented, no empty TSV row, no `=malformed-job-name` tuple. All downstream consumers (`job_name=$raw_name`, TSV emit at line 132, KV emit at line 134, `unfixable_list` tuple at line 142) inherit the sanitized value.

3. Leave the existing `tr -d '[:cntrl:]'` pipe on line 86 (the `larch_err "$line"` path on `gh` failure) in place — but rewrite the line so it calls the shared helper from `lib-quiet.sh` for consistency:

   ```sh
   larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"
   ```

   Same byte-level behavior, single helper definition site.

### UPDATED: `scripts/sanitize-mermaid-fragment.sh`
Replace the `awk -F'[ =]'` parser at line 283 with the prefix-strip pattern used canonically by `generate-code-flow-diagram.sh:109`.

Specific edit (Item C — harden parser only, no contract expansion):

1. Replace the current line 283:

   ```sh
   tokens="$(awk -F'[ =]' '/^REASON_TOKEN=/{print $2}' "$reasons" | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
   ```

   with:

   ```sh
   tokens="$(awk '/^REASON_TOKEN=/{sub(/^REASON_TOKEN=/, ""); sub(/[[:space:]].*$/, ""); print}' "$reasons" | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
   ```

   The new awk strips only the literal `REASON_TOKEN=` prefix, then strips trailing whitespace-delimited metadata, preserving any embedded `=` inside the token. POSIX/BSD awk compatible.

2. Do NOT change any code that EMITS `REASON_TOKEN=` lines. The contract today is "tokens have no embedded `=`"; this edit only hardens the consumer against future tokens that might.

### UPDATED: `skills/implement/scripts/step-7a.sh`
Wire `kv_value SKIP_REASON "$gen_out"` into `CODE_FLOW_SKIP_REASON` on the `skipped` and `failed` branches, falling back to the existing literal when the generator emitted no reason.

Specific edits (Item A):

1. In the `case "$gen_status"` block (currently lines 359-382), update the `skipped` and `failed` branches to read SKIP_REASON from the generator stdout and use it when non-empty:

   ```sh
   skipped)
       DIAGRAM_STATUS=skipped
       DIAGRAM_PATH=""
       _skip_reason=$(kv_value SKIP_REASON "$gen_out")
       if [ -n "$_skip_reason" ]; then
           CODE_FLOW_SKIP_REASON="$_skip_reason"
       else
           CODE_FLOW_SKIP_REASON="Code flow diagram not available."
       fi
       ;;
   failed)
       DIAGRAM_STATUS=failed
       DIAGRAM_PATH=""
       _skip_reason=$(kv_value SKIP_REASON "$gen_out")
       if [ -n "$_skip_reason" ]; then
           CODE_FLOW_SKIP_REASON="$_skip_reason"
       else
           CODE_FLOW_SKIP_REASON="Code flow diagram not available."
       fi
       append_failure "Warnings" "step-7a" "generate-code-flow-diagram.sh" "$gen_rc" "$gen_err"
       ;;
   *)
       DIAGRAM_STATUS=failed
       DIAGRAM_PATH=""
       CODE_FLOW_SKIP_REASON="Code flow diagram not available."
       append_failure "Warnings" "step-7a" "generate-code-flow-diagram.sh" "$gen_rc" "$gen_err"
       ;;
   ```

   The wildcard branch keeps the literal fallback. Use case: unknown `STATUS` token (parse failure) or an entirely missing `STATUS=` line — `kv_value SKIP_REASON` could still return data, but the orchestrator does not trust an unrecognized envelope and falls back to the safe literal. If a future generator change makes the wildcard path informative, it can be revisited then.

2. Do NOT change the `is_small_non_runtime_change` branch (line 343-347) — that placeholder text ("Code flow diagram skipped — small/non-runtime change") is produced by Step 7a itself, not by the generator, and Round 1 confirmed it stays unchanged.

### UPDATED: `skills/implement/scripts/step-7a.md`
Update the sibling contract doc so the "Invariants" section reflects the new behavior (F30).

Specific edits:

1. Replace the bullet currently reading `Step 7a still upserts the larch:diagrams comment with the placeholder body when generate-code-flow-diagram.sh reports STATUS=skipped or STATUS=failed; only empty ISSUE_NUMBER gates the upsert.` with:

   `Step 7a upserts the larch:diagrams comment with the generator-emitted SKIP_REASON value (e.g. pipe-in-node-label fence=mermaid line=7) when generate-code-flow-diagram.sh reports STATUS=skipped or STATUS=failed and a non-empty SKIP_REASON KV; falls back to the literal "Code flow diagram not available." when SKIP_REASON is empty (e.g. generator crash, unknown STATUS). Only empty ISSUE_NUMBER gates the upsert.`

### UPDATED: `skills/implement/scripts/test-step-7a.md`
Reconcile the 21-case ledger to 23 cases using harness `new_case` labels AND update rejected-mode descriptions so they match harness assertions and the post–Item A SKIP_REASON behavior.

Specific edits (Item B + F9 + F18):

1. Renumber/rename the case list (lines 7-25 currently) so labels match `new_case <label>` invocations in `test-step-7a.sh` (kebab-case identifiers):
   - `green path` → `green`
   - `diagram-skip` (unchanged)
   - `diagram-skip-forked` (unchanged)
   - `diagram-generate-forked` (unchanged)
   - `diagram-rejected` (unchanged)
   - `diagram-rejected-br-in-participant-alias` (unchanged)
   - `diagram-rejected-dollar-in-participant-alias` (unchanged)
   - `diagram-rejected-unclosed-frontmatter` (unchanged)
   - `diagram-generation-failure` → `diagram-failure`
   - `diagram-failure-sanitizer` (unchanged label; description fixed — see step 2)
   - `summary-upsert-failure` → `upsert-failure`
   - `flush-failure` (unchanged)
   - `flush-failure-no-logs-commit` (unchanged)
   - `no-logs-commit honored` → `no-logs-commit`
   - `forked-target rebase argv` → `forked-target`
   - `ISSUE_NUMBER empty gate` → `issue-empty`
   - `generator-crash` (unchanged)
   - `rebase-conflict` (unchanged)
   - `rebase-failed` (unchanged)
   - **ADD**: `rebase-unexpected-rc` — `STEP7A_REBASE_MODE=unexpected` causes the probe to return rc 5 with `REBASE_OUTCOME=failed`, `REBASE_ERROR=unexpected-rc-5`; the helper exits 5 and emits `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
   - `quiet-rebase-contract` (unchanged)
   - **ADD**: `quiet-diagram-skip-contract` — with quiet mode enabled, the helper still relays the `⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=0s` line on the caller-visible contract stream.
   - `argv error` → `argv-error`

2. Update rejected/failure case descriptions for the new SKIP_REASON behavior:
   - `diagram-rejected`: previously "writes expected summary diagrams". New wording: "posts the placeholder summary comment carrying the generator-emitted SKIP_REASON value (default `pipe-in-node-label fence=mermaid line=7`)."
   - `diagram-rejected-<sanitizer_token>` (all three): "posts the placeholder summary comment carrying `<token> fence=mermaid line=7`."
   - `diagram-failure`: "posts the placeholder summary comment carrying SKIP_REASON `helper-error` (or whatever `STEP7A_GEN_FORCE_SKIP_REASON` overrides to), appends a Warnings entry, and exits 0."
   - `diagram-failure-sanitizer`: replace "suppresses the summary upsert" wording with "a failed generator that emits a sanitizer rejection token (via `STEP7A_GEN_FORCE_SKIP_REASON='pipe-in-node-label fence=mermaid line=7'`) still posts the placeholder summary comment with that SKIP_REASON and emits `DIAGRAM_STATUS=failed` with `COMMENT_URL` set."
   - `generator-crash`: leave as-is — this is the true empty-SKIP_REASON fallback case (stub exits 99 with no stdout, so `kv_value SKIP_REASON` returns empty and Item A's fallback path triggers, restoring `"Code flow diagram not available."`).

3. The trailing prose under the case list (description of fixtures, paths, etc.) remains untouched.

### UPDATED: `skills/implement/scripts/test-step-7a.sh`
Update assertions for all cases whose stub emits a default SKIP_REASON, so they assert the actual value instead of the literal placeholder. Only `generator-crash` retains the placeholder assertion (it tests the empty-SKIP_REASON fallback path).

Specific edits (Item A coupling — F1/F3/F8/F13/F17/F19/F20/F24/F25/F29/F31/F32/F33):

1. **`diagram-rejected` baseline** (current line 455): change the assertion from
   ```sh
   assert_file_equals "$(placeholder_expected_summary "Code flow diagram not available.")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected writes expected summary diagrams"
   ```
   to
   ```sh
   assert_file_equals "$(placeholder_expected_summary "pipe-in-node-label fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected writes expected summary diagrams with generator SKIP_REASON"
   ```
   (Stub default for rejected mode is `STEP7A_SANITIZER_TOKEN=${...:-pipe-in-node-label}` + the literal ` fence=mermaid line=7` suffix.)

2. **`diagram-rejected-<sanitizer_token>` loop** (current line 458-468): change the per-iteration assertion at line 467 from
   ```sh
   assert_file_equals "$(placeholder_expected_summary "Code flow diagram not available.")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected-$sanitizer_token writes expected summary diagrams"
   ```
   to
   ```sh
   assert_file_equals "$(placeholder_expected_summary "${sanitizer_token} fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected-$sanitizer_token writes expected summary diagrams with token SKIP_REASON"
   ```
   The env var name is `STEP7A_SANITIZER_TOKEN` (set in-loop at line 460), NOT `STEP7A_GEN_FORCE_SKIP_REASON` — per F31 confirmed by reading the stub at lines 130-135.

3. **`diagram-failure` baseline** (current lines 470-480): change the file-contains assertion at line 478 from
   ```sh
   assert_file_contains "Code flow diagram not available." "$CASE_DIR/tmp/summary-diagrams.md" "diagram-generation-failure writes unavailable placeholder"
   ```
   to
   ```sh
   assert_file_contains "helper-error" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-failure writes generator SKIP_REASON helper-error"
   ```
   (Stub default for failed mode is `${STEP7A_GEN_FORCE_SKIP_REASON:-helper-error}`.)

4. **`diagram-failure-sanitizer`** (current lines 481-490): the fixture sets `STEP7A_GEN_FORCE_SKIP_REASON='pipe-in-node-label fence=mermaid line=7'`. Change the assertion at line 490 from
   ```sh
   assert_file_equals "$(placeholder_expected_summary "Code flow diagram not available.")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-failure-sanitizer writes expected summary diagrams"
   ```
   to
   ```sh
   assert_file_equals "$(placeholder_expected_summary "pipe-in-node-label fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-failure-sanitizer writes expected summary diagrams with fixture SKIP_REASON"
   ```

5. **`generator-crash`** (around line 550): the stub exits 99 with no stdout (`STATUS=…` line absent). `kv_value SKIP_REASON` on an empty/missing file returns empty; Item A's fallback path sets `CODE_FLOW_SKIP_REASON="Code flow diagram not available."`. Keep the existing placeholder assertion — this case is now the ONLY exerciser of the empty-SKIP_REASON fallback after Item A.

6. The `green`, `diagram-skip*`, `diagram-generate-forked`, `upsert-failure`, `flush-failure*`, `no-logs-commit`, `forked-target`, `issue-empty`, `rebase-conflict`, `rebase-failed`, `rebase-unexpected-rc`, `quiet-rebase-contract`, `quiet-diagram-skip-contract`, `argv-error` cases do not exercise the rejected/failed branches with SKIP_REASON content and need no assertion changes.

7. Iterate the file, run `bash skills/implement/scripts/test-step-7a.sh`, and verify all cases pass.

### UPDATED: `scripts/test-lib-quiet.sh`
Add one harness case verifying `sanitize_diagnostic_line` strips C0 control bytes from one input line. Per Round 1 Decision 5 + the F15-driven narrowing, `larch_err` is unchanged, so no `larch_err` integration assertion is needed beyond the existing test-12 (line 132) that already covers `larch_err` end-to-end.

Specific edit (Item E coverage):

1. Add a new case at the end (numbered 13 after the existing 12 cases):

   ```sh
   # 13. sanitize_diagnostic_line strips C0 control bytes from one line.
   helper="$SCRATCH/sanitize.sh"
   write_helper "$helper" 'printf "before\x01\x02\x03after\x07.end\n" | sanitize_diagnostic_line'
   out=$("$helper" 2>/dev/null)
   [ "$out" = "beforeafter.end" ] || fail "sanitize_diagnostic_line did not strip controls: '$out'"
   ```

   Sources `lib-quiet.sh` via the existing `write_helper` machinery. ~6 lines.

### UPDATED: `scripts/test-ci-failed-jobs.sh`
Add one harness case verifying that an all-control-byte `job_name` from `gh` stdout is sanitized to empty AND skipped (not emitted as a blank TSV row, not counted).

Specific edit (Item D coverage, F2/F36):

1. Add a new case that injects a fake `gh` stub returning ONE line containing only control bytes (e.g. `\x01\x02\x03`) and ONE valid line (e.g. `lint`), runs `ci-failed-jobs.sh`, and asserts:
   - The TSV output contains exactly ONE row (the valid `lint` job), not two.
   - `FAILED_JOBS_COUNT=1` (the control-byte row was dropped before the count increment).
   - `FAILED_JOBS_FIXABLE=lint`.

   Implementation: ~15 lines. Follow the existing test-ci-failed-jobs.sh case style.

### UPDATED: `scripts/test-mermaid-fragments.sh`
Add one harness case verifying that the warnings-log aggregation in `sanitize-mermaid-fragment.sh` preserves embedded `=` in REASON_TOKEN values (Item C direct test, F23).

Specific edit:

1. Add a case that constructs a synthetic `$reasons` file (or equivalent fixture intercepting the aggregation point) with two lines:
   ```
   REASON_TOKEN=normal-token
   REASON_TOKEN=future=token fence=mermaid line=9
   ```
   Then invoke the rewritten awk line (extracted into a tiny shell helper in the test, OR by sourcing the relevant section of `sanitize-mermaid-fragment.sh`) and assert the output contains both `normal-token` and `future=token`. ~10-15 lines.

## Approach

The five items are tightly coupled around the diagnostic-sanitization + SKIP_REASON contract. After the post-review revisions, the ordered change is:

1. **Item E (narrow)**: extract `sanitize_diagnostic_line` into `lib-quiet.sh`. Do NOT modify `larch_err` / `larch_errf`. Existing multi-line callers stay safe (F15).
2. **Item D**: sanitize `raw_name` BEFORE the non-empty guard so all-control-byte rows are dropped cleanly (F2 cluster).
3. **Item C**: rewrite the parser to mirror `generate-code-flow-diagram.sh:109` and add an embedded-`=` regression test in `test-mermaid-fragments.sh` (F23).
4. **Item A**: wire `kv_value SKIP_REASON` into `CODE_FLOW_SKIP_REASON` with fallback. Update `step-7a.md` to document the new contract (F30).
5. **Item B**: reconcile md ledger (23 cases, matching harness identifiers, with rejected-mode descriptions corrected per F9/F18); update test-step-7a.sh assertions to match stub defaults (F1 cluster). Only `generator-crash` retains the placeholder assertion as the empty-SKIP_REASON fallback exerciser.

Hard constraints from Round 1 (unchanged):
- All 5 items, one PR (Round 1 Decision 1).
- `larch_err` audit is narrow: only `ci-failed-jobs.sh` (Round 1 Decision 5). Do not modify `larch_err` itself; do not touch `breadcrumb-monitor.sh`, `check-clean-tree.sh`, `agent-model-args.sh`, `git-force-push.sh`, etc.
- Item C is parser-hardening only — do not change any code that emits `REASON_TOKEN=` lines (Round 1 Decision 3).
- Item D sanitizes once at the parse boundary, BEFORE the non-empty guard, not at each emit site (Round 1 Decision 4 + F2 cluster).
- `larch_errf` is left untouched.
- The reconciliation direction in Item B is md→harness identifiers (Round 1 Decision 6); harness `new_case` labels are authoritative.
- Item A keeps the placeholder text as a fallback when SKIP_REASON is empty (Round 1 Decision 7); after F1 cluster fix, only `generator-crash` exercises that fallback.

The change touches widely-consumed surfaces (`lib-quiet.sh`, `step-7a.sh`) but each edit is scoped narrowly. Total source delta remains ~30 LOC; harness assertion updates and md reconciliation add the rest.

## Edge cases

1. **Empty SKIP_REASON via crash** (Item A + F25): the ONLY scenario producing an empty `kv_value SKIP_REASON` result is the `generator-crash` test case (stub exits 99 with no stdout). All other rejected/failed cases now have non-empty SKIP_REASON values per the stub defaults documented above. The `if [ -n "$_skip_reason" ]` guard falls back to the literal placeholder in this single case.

2. **All-control-byte `job_name`** (Item D + F2 cluster): `sanitize_diagnostic_line` strips every byte, leaving `raw_name` empty. The `[ -n "$raw_name" ] || continue` guard at the new ordering (immediately after sanitization, BEFORE `count=$((count + 1))`) skips the row entirely. No TSV entry, no count increment, no unfixable-list tuple.

3. **Embedded `=` in REASON_TOKEN** (Item C + F23): not currently emitted by `sanitize-mermaid-fragment.sh`, but the new parser tolerates it. The new `test-mermaid-fragments.sh` case fixtures `REASON_TOKEN=future=token fence=mermaid line=9` and asserts `future=token` is preserved.

4. **Multi-line `larch_err` callers** (F15): `git-force-push.sh:71` and similar pass `git status --porcelain` output. Since `larch_err` is NOT modified by this plan, those callers are unaffected. Any new caller forwarding multi-line external content should `printf '%s\n' "$content" | while IFS= read -r line; do larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"; done` (per-line sanitization preserving LF boundaries).

5. **Harness `STEP7A_SANITIZER_TOKEN` vs `STEP7A_GEN_FORCE_SKIP_REASON`** (F31): the rejected-mode stub default uses `STEP7A_SANITIZER_TOKEN` (set per iteration in the diagram-rejected-<token> loop at line 460); the failed-mode stub default uses `STEP7A_GEN_FORCE_SKIP_REASON`. The plan's assertion edits use the correct env var per case.

6. **`generator-crash` empty-SKIP_REASON path** (Item A + F25): kv_value on a non-existent or empty `$gen_out` returns empty (POSIX awk on `/dev/null` is a no-op). The fallback path triggers and `CODE_FLOW_SKIP_REASON` is set to the placeholder literal.

## Failure modes

1. **POSIX/BSD awk incompatibility on macOS**: the rewritten `awk` in Item C uses `sub(...)` and `[[:space:]]`, both POSIX-compatible. Risk: low. Earliest warning: `bash scripts/test-mermaid-fragments.sh` will exercise the new regression case. Mitigation: keep the awk one-liner identical to `generate-code-flow-diagram.sh:109` (already proven on macOS).

2. **Item D ordering regression**: if an implementer accidentally restores the OLD ordering (sanitize after guard), all-control-byte names emit blank TSV rows. Risk: medium. Earliest warning: the new test-ci-failed-jobs.sh case will fail. Mitigation: the test fixture is the chokepoint; if it passes, the ordering is correct.

3. **Test-step-7a.sh assertion drift after Item A**: if any assertion is missed (the F1 cluster lists 15 findings naming the same defect), the harness will fail loudly. Risk: now-mitigated by the explicit case-by-case mapping above (cases 1-7 in the test-step-7a.sh edit section).

4. **Item C parser misses embedded `=`**: if the awk substitution is mistyped, embedded `=` tokens still truncate. Risk: now-mitigated by the new test-mermaid-fragments.sh case (F23).

5. **`step-7a.md` doc drift** (F30): if the sibling doc is not updated, downstream consumers reading the contract see stale "placeholder-only" wording. Risk: low (the OOS framing makes this discoverable). Mitigation: included in the modified files list above.

## Testing strategy

Per-component:
- `scripts/test-lib-quiet.sh` — add one case asserting `sanitize_diagnostic_line` strips control bytes (Item E).
- `scripts/test-ci-failed-jobs.sh` — add one case asserting all-control-byte `job_name` from `gh` stdout is sanitized AND dropped (Item D + F2 cluster).
- `scripts/test-mermaid-fragments.sh` — add one case asserting the rewritten awk preserves embedded `=` in REASON_TOKEN aggregation (Item C + F23).
- `skills/implement/scripts/test-step-7a.sh` — update assertions for `diagram-rejected` baseline, `diagram-rejected-<token>` loop, `diagram-failure` baseline, and `diagram-failure-sanitizer` to match stub-default SKIP_REASON values; `generator-crash` keeps the placeholder assertion (Item A + F1 cluster + F31).
- `skills/implement/scripts/test-step-7a.md` — reconciled ledger is text-only.

Whole-suite:
- `bash scripts/test-lib-quiet.sh`
- `bash scripts/test-ci-failed-jobs.sh`
- `bash scripts/test-mermaid-fragments.sh`
- `bash skills/implement/scripts/test-step-7a.sh`
- `bash skills/implement/scripts/test-generate-code-flow-diagram.sh` (verifies the generator still emits SKIP_REASON cleanly; no source change but exercises the contract edge).
- `bash scripts/relevant-checks.sh` (the AGENTS.md-mandated full local lint; covers shellcheck, bash 3.2 portability lint, agent-lint, doc-link lint, etc.).

No new test files are created.

diff_lines: 130

## Acceptance

Acceptance criteria for this design:

- All five OOS items (A: step-7a SKIP_REASON wiring; B: test-step-7a ledger reconciliation + sh assertion updates; C: REASON_TOKEN parser embedded-`=` preservation; D: ci-failed-jobs parse-boundary sanitization with proper guard ordering; E: extract `sanitize_diagnostic_line` helper into `lib-quiet.sh` without modifying `larch_err`) implemented in a single PR.
- All 33 accepted plan-review findings applied (cluster F1 assertion strategy, cluster F2 guard ordering, F15 narrowing of Item E, F23 + F30 doc / test follow-ups).
- Harness suites pass: `bash scripts/test-lib-quiet.sh`, `bash scripts/test-ci-failed-jobs.sh`, `bash scripts/test-mermaid-fragments.sh`, `bash skills/implement/scripts/test-step-7a.sh`, `bash skills/implement/scripts/test-generate-code-flow-diagram.sh`.
- Repo-wide lint passes: `bash scripts/relevant-checks.sh`.
- `larch_err` / `larch_errf` byte-level behavior is preserved for all existing callers (verified by re-running `test-lib-quiet.sh` and grepping for new larch_err audit-flagged sites — none expected per Round 1 Decision 5).
- `kv_value SKIP_REASON` fallback path is exercised exclusively by the `generator-crash` harness case (per Edge case #1 / F25).
- All five lineage items #2893, #2862, #2875, #2876, #2874 cited in the issue body are addressed and the change is small enough that no decomposition is required (95-line source delta, 130-line plan diff).

diff_lines: 130

## Test plan
(no test plan section in plan-file)
