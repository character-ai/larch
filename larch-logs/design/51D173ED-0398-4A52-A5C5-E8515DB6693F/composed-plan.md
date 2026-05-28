## Plan

This SIMPLE-tier plan implements all 12 OOS items in one combined PR. Round-1 scope (Decisions 1-3 in `discussion-round1.md`): all 12 items, breadcrumb-helper failure → `PUBLISH_OK=false` hard abort, breadcrumb-monitor surfaces redacted via `redact-tmpdir-paths.sh`. Plan review accepted FINDING_1 through FINDING_7; this plan incorporates each.

### Files to modify/create

#### UPDATED: `scripts/run-step5-review.sh`
Item 1A: Drop the existing `unset LARCH_PAIRED_PID_FILE` (line 189). Immediately before the nested `"$REVIEW_AND_FIX_SH" "${REVIEW_AND_FIX_ARGS[@]}"` invocation (after `REVIEW_AND_FIX_ARGS` is fully composed), launch the child via `env -u LARCH_DONE_SENTINEL -u LARCH_STATUS_FILE -u LARCH_BREADCRUMBS_SURFACED_FILE -u LARCH_PAIRED_PID_FILE "$REVIEW_AND_FIX_SH" "${REVIEW_AND_FIX_ARGS[@]}"`. Using `env -u` (child-environment sanitization) preserves the parent's vars for its own EXIT trap (`larch_quiet__exit_write_done` in `lib-quiet.sh` reads `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` at parent exit). Placement: within 5 nonblank noncomment lines of the nested call so the linter look-back window covers it (FINDING_7).

#### UPDATED: `scripts/dispatch-code-voters.sh`
Item 1A symmetry: replace the existing `unset LARCH_PAIRED_PID_FILE` (line 171) with `env -u LARCH_DONE_SENTINEL -u LARCH_STATUS_FILE -u LARCH_BREADCRUMBS_SURFACED_FILE -u LARCH_PAIRED_PID_FILE "$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" …`, placed within 5 nonblank noncomment lines of the nested call.

#### UPDATED: `scripts/dispatch-plan-voters.sh`
Item 1A symmetry: replace the existing `unset LARCH_PAIRED_PID_FILE` (line 142) with the same `env -u …` invocation form, placed within 5 nonblank noncomment lines of the nested `"$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh" …` call.

#### UPDATED: `scripts/ship-pr.sh`
- Item 1A symmetry: replace the existing `unset LARCH_PAIRED_PID_FILE` (line 3042) with the same `env -u …` form for the nested `with_transient_retry … "$SCRIPT_DIR/ci-wait.sh" "${ci_args[@]}"` call (line 3043). Place within 5 nonblank noncomment lines.
- Item 3.2: in `append_tool_failure_local` fallback relay (`scripts/ship-pr.sh:872-875`), pipe each line of the captured `output_file` through `sanitize_diagnostic_line` before the per-line `larch_err` invocation. The retargeted location is the `while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$output_file"` loop and the matching loop in the redact-secrets fallback above it. Pattern: `while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"; done < …`. Preserves LF boundaries (per the `lib-quiet.sh` contract comment at lines 96-100).

#### UPDATED: `skills/implement/scripts/run-step2-dispatch.sh`
Item 1A symmetry (per FINDING_2 Cursor-Requirements): replace the existing `unset LARCH_PAIRED_PID_FILE` (line 99) with the same `env -u LARCH_DONE_SENTINEL -u LARCH_STATUS_FILE -u LARCH_BREADCRUMBS_SURFACED_FILE -u LARCH_PAIRED_PID_FILE "$DISPATCHER_SH" …` invocation for the nested `step2-implement.sh` call. Place within 5 nonblank noncomment lines.

#### UPDATED: `scripts/breadcrumb-monitor.sh`
Item 1B: in `larch_bm_emit_line` (around line 149), after the existing `lib-redact-streaming.sh` pipe and before the FD-3 `printf` at line 156, route the line through `redact-tmpdir-paths.sh`. Mirror the existing drop-on-fail pattern: on non-zero redactor exit, call `larch_err "WARN redact-tmpdir-drop-line"` and `return 0`. Pipeline order: `lib-redact-streaming.sh` → `redact-tmpdir-paths.sh` (secret redaction first, then tmpdir paths).

#### UPDATED: `scripts/design-log-publish.sh`
- Item 1C: leave the current fail-closed call site (`if ! design_publish_breadcrumbs ...; then emit_publish_result false; exit 0; fi` at line 493) intact. Tighten the `design_publish_breadcrumbs_error` callback (lines 293-295) so each `on_error` invocation appends a structured line into `$DESIGN_TMPDIR/design-publish-breadcrumb-helper.stderr.log` for operator forensic in addition to the existing `larch_err`. Update `scripts/design-log-publish.md` to document this contract (Cluster 1 Item C + Item D cross-ref).
- Items 2A + 2D (TOCTOU race narrowing per FINDING_3, NOT "fully closed"): after each existing `find -type f` enumeration loop (plan-review at lines 348-373; render-cache at lines 408-431), add a final tree-wide `find -type l -print -quit` rescan of the resolved root immediately before the loop exits. On non-empty rescan output, fail-closed with `emit_publish_result false; exit 0`. This **narrows** the parent-directory replacement race relative to the current pre-scan window; it does **not** close concurrent same-UID writes that swap a parent or leaf after the rescan and restore before final commit. Keep the existing per-leaf `-L` recheck (lines 369, 427) as defense-in-depth.

#### UPDATED: `scripts/design-log-publish.md`
- Item 1C: document the breadcrumb-helper callback contract: failure of any per-file redactor invocation inside `larch_log_publish_breadcrumbs_shared` returns 1 to `design_publish_breadcrumbs`, which propagates to `emit_publish_result false; exit 0`. Symmetric with `larch-log.sh` `larch_log_fail 3` semantics — the difference is the exit-code convention (`exit 0` for parseable `PUBLISH_OK=false` vs `exit 3` for CI fast-fail), not the fail-closed behavior. Add `design-publish-breadcrumb-helper.stderr.log` to the operator-forensic listing.
- Item 1D: add a 2-3 sentence cross-reference pointing at `SECURITY.md § Breadcrumb stream redaction` (anchor: the `## Breadcrumb stream redaction` section at line 248).
- Items 2A + 2D: document the new post-enumeration tree-wide rescan as a **narrowing** measure (not full closure) and retain residual-risk wording.

#### UPDATED: `SECURITY.md`
- Item 1D: in the early "Security Findings in OOS Workflows" summary (around line 28), add a one-sentence cross-reference linking the breadcrumb publication paragraph to the canonical `## Breadcrumb stream redaction` section at line 248.
- Item 2C (per FINDING_3): tighten the existing render-cache paragraph at line 186. Replace "Parent-directory replacement races between enumeration and stage are not fully closed in either subtree" with "Parent-directory replacement races are narrowed by a post-enumeration tree-wide symlink rescan but not fully closed; concurrent same-UID writers can still swap a parent or leaf after the rescan and restore it before final commit. The per-file recheck closes the leaf slot for the brief window before rescan." Line 139 stays untouched — line 186 is the canonical location.

#### UPDATED: `scripts/breadcrumb-monitor.md`
Item 1B sibling: document the new `redact-tmpdir-paths.sh` pipeline stage and the `WARN redact-tmpdir-drop-line` diagnostic for drop-on-fail.

#### UPDATED: `scripts/run-step5-review.md`, `scripts/dispatch-code-voters.md`, `scripts/dispatch-plan-voters.md`, `scripts/ship-pr.md`, `skills/implement/scripts/run-step2-dispatch.md`
Item 1A symmetry siblings: document the `env -u` child-environment-sanitization pattern (vs plain parent unset) and its rationale: preserve the parent EXIT trap (FINDING_5).

#### UPDATED: `scripts/lib-quiet.sh`
Item 3.1 audit: review every `larch_err` / `larch_errf` call site that consumes external-tool stderr (CI stderr from `gh`, vendor stderr from `cursor` / `codex`, untrusted file content). The lib-quiet contract at lines 96-100 is opt-in; the audit must add `sanitize_diagnostic_line` invocations at any high-risk passthrough site not already covered (the new ship-pr.sh:872-875 call site is one). No public API change. Update the contract comment at lines 96-100 if the audit identifies additional shapes.

#### UPDATED: `scripts/lib-quiet.md`
Item 3.1 sibling: document the audited call sites and the pattern operators should follow when adding new external-stderr passthrough.

#### UPDATED: `scripts/lint-foreground-markers.sh`
Items 1A + FINDING_1 + FINDING_2 + FINDING_5 + FINDING_7 enforcement:
- Extend `PARENT_UNSET_REQUIRED_CHILDREN` (currently only `dispatch-with-waterfall.sh`) to also include `review-and-fix.sh`, `ci-wait.sh`, and `step2-implement.sh`.
- Remove the `LC_ALL=C grep -Fq 'dispatch-with-waterfall.sh' "$path"` gate at `scan_shell_file_for_unset_before_nested_child:496` so any path containing any listed child is scanned.
- Recognize `env -u LARCH_DONE_SENTINEL -u LARCH_STATUS_FILE -u LARCH_BREADCRUMBS_SURFACED_FILE -u LARCH_PAIRED_PID_FILE <child-invocation>` on a single line as the sanitization marker. Variable order does not matter; all four `-u <var>` flags must be present.
- For backward compatibility, accept the legacy `unset LARCH_PAIRED_PID_FILE` line as a sufficient marker only for nested `dispatch-with-waterfall.sh` and `step2-implement.sh` callsites that have not yet migrated; reject all other anchors lacking the full four-var `env -u` form. (`run-step5-review.sh`, `dispatch-code-voters.sh`, `dispatch-plan-voters.sh`, `ship-pr.sh`, `run-step2-dispatch.sh` migrate in this PR — the legacy form is rejected once their migration lands.)
- Linter look-back window remains 5 nonblank noncomment lines; the sanitization line must sit within that window immediately before the nested call.
- Keep `# lint-foreground-markers: ok <reason>` line-level overrides for legacy exemptions.

#### UPDATED: `scripts/lint-foreground-markers.md`
Items 1A + 1A symmetry sibling: document the broadened parent-unset / `env -u` rule, the rationale (early-exit cascade prevention + parent EXIT trap preservation), and the migration path.

#### UPDATED: `scripts/test-breadcrumb-monitor.sh`
- Item 1A regression test: launch a synthetic top-level Family-B writer that invokes a nested child via `env -u LARCH_DONE_SENTINEL -u LARCH_STATUS_FILE -u LARCH_BREADCRUMBS_SURFACED_FILE -u LARCH_PAIRED_PID_FILE`. The child writes its own internal sentinel quickly. Assert the parent monitor does **not** exit early (parent's `surfaced` sentinel remains the gate, child cannot bump it).
- Item 1B test: assert that surfaced lines containing tmpdir paths come out redacted by `redact-tmpdir-paths.sh` and that drop-on-fail produces the expected `WARN redact-tmpdir-drop-line` diagnostic.
- Parent EXIT trap regression (FINDING_5): assert that after the `env -u` invocation, the parent's own EXIT trap still writes the parent's done sentinel.

#### UPDATED: `scripts/test-breadcrumb-monitor.md`
Items 1A + 1B sibling: document the new harness cases.

#### UPDATED: `scripts/test-design-log-publish.sh`
- Item 2B: add a "render-cache path escape" case mirroring the plan-review path-escape coverage at line 779. Set up a render-cache subtree, inject an absolute path that escapes the resolved root, assert `PUBLISH_OK=false` and that no staged file is published.
- Items 2A + 2D coverage: add a "post-enumeration tree-wide symlink rescan" case for both plan-review and render-cache. Inject a symlink under the resolved root after the initial `-type l` scan but before the `-type f` loop completes (controlled race fixture), assert fail-closed and no leak.

#### UPDATED: `scripts/test-lint-foreground-markers.sh`
Item 1A + FINDING_1 + FINDING_7 coverage: extend the existing literal / variable / default-expansion fixture subcases to assert the lint:
- Recognizes the new `env -u` form (all four `-u <var>` flags present, any order) as sufficient when placed within 5 nonblank noncomment lines of the nested call.
- Rejects when the `env -u` form is missing flags or placed outside the 5-line look-back window.
- Adds anchor coverage for each new child basename: `review-and-fix.sh`, `ci-wait.sh`, `step2-implement.sh`.
- Retains coverage for legacy `unset LARCH_PAIRED_PID_FILE` acceptance only for the migration-pending children listed above.

#### UPDATED: `scripts/test-mermaid-fragments.sh`
Item 3.4: add the embedded-`=` `REASON_TOKEN` regression case. Aggregation site is `sanitize-mermaid-fragment.sh:283`. Assert that a `REASON_TOKEN` value containing an embedded `=` is preserved in warnings token aggregation.

#### UPDATED: `scripts/test-mermaid-fragments.md`
Item 3.4 sibling: document the new test case.

#### UPDATED: `scripts/test-lib-quiet.sh`
Item 3.1 coverage: if the lib-quiet audit identifies any new internal pipe-through site, add coverage demonstrating C0-control stripping at that site.

### Approach

Three workstreams that share surfaces but address distinct concerns:

- **Cluster 1 (breadcrumb pipeline)**: a single root cause (nested env inheritance) drives Item 1A; Items 1B/1C/1D are independent. Tackle 1A first because the linter changes enforce the new `env -u` pattern for subsequent edits.
- **Cluster 2 (render-cache + plan-review TOCTOU)**: Items A and D share one fix (post-enumeration tree-wide rescan — **narrowing**, not full closure per FINDING_3); Item B is a missing harness; Item C is a small SECURITY.md tightening.
- **Cluster 3 (`sanitize_diagnostic_line` adoption)**: Item 1 is the audit; Item 2 retargeted to ship-pr.sh:872-875 fallback relay (FINDING_6); Item 3 dropped per FINDING_4 (`CODE_FLOW_SKIP_REASON` does not exist on `skills/implement/scripts/step-7a.sh` today); Item 4 is an orthogonal harness add.

Order: Cluster 1 → Cluster 2 → Cluster 3. Linter changes first so subsequent edits get checked automatically.

### Edge cases

- **Parent EXIT trap preservation (FINDING_5)**: `env -u` sanitizes only the child environment. The parent keeps `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_BREADCRUMBS_SURFACED_FILE` / `LARCH_PAIRED_PID_FILE` so its own EXIT trap can write the parent's done sentinel correctly.
- **Tests that intentionally inherit `LARCH_DONE_SENTINEL`**: harnesses that set inherited sentinels for fixture purposes (`scripts/test-breadcrumb-monitor.sh:199, 239`) are nested test fixtures, not orchestrator-paired Family-B calls.
- **`redact-tmpdir-paths.sh` returning non-zero on legitimate input**: drop-on-fail. `WARN redact-tmpdir-drop-line` provides visibility.
- **Concurrent same-UID writers** (FINDING_3): the new rescan **narrows** the race window but does not eliminate it. Documented as residual risk.
- **`/design` runs without `breadcrumbs/` directory**: empty-source path remains a no-op success (per `SECURITY.md:248`); Item 1C does NOT convert this to fail-closed.
- **Embedded `=` in `REASON_TOKEN`**: harness asserts the full value (everything after the first `=`) is preserved.
- **`run-step5-review.sh` PAIRED_PID_FILE timing**: parent writes its PID at line 169 (once); `env -u` at the nested call afterward; parent retains its `LARCH_PAIRED_PID_FILE` for any later use.

### Failure modes

1. **`env -u` migration misses an existing call site**. Warning: `make lint-foreground-markers` after Cluster 1 lands. Mitigation: enable the broadened linter rule before changing any call site; CI flags un-migrated sites.
2. **`redact-tmpdir-paths.sh` integration drops legitimate breadcrumbs**. Warning: missing breadcrumb lines during `/implement` Step 5 smoke test. Mitigation: drop-on-fail emits `WARN redact-tmpdir-drop-line`.
3. **Tree-wide rescan rejects a legitimate publish in race-free state**. Warning: `test-design-log-publish.sh` failing on the happy-path case. Mitigation: both pre- and post-scans must return empty for publish to proceed.

### Testing strategy

- New tests in `scripts/test-breadcrumb-monitor.sh`: early-exit cascade with `env -u` (Item 1A); tmpdir-path redaction + drop-on-fail (Item 1B); parent EXIT trap still writes done after `env -u` invocation (FINDING_5).
- New tests in `scripts/test-design-log-publish.sh`: render-cache path escape (Item 2B); post-enumeration tree-wide rescan for both subtrees (Items 2A + 2D).
- New tests in `scripts/test-lint-foreground-markers.sh`: `env -u` recognition + missing-flag rejection + look-back window enforcement, for each new child (`review-and-fix.sh`, `ci-wait.sh`, `step2-implement.sh`).
- New test in `scripts/test-mermaid-fragments.sh`: embedded-`=` `REASON_TOKEN` preservation (Item 3.4).
- Optional new test in `scripts/test-lib-quiet.sh`: any new sanitize_diagnostic_line call site introduced by the audit.
- Run `make lint` (including `lint-bash32`, `lint-foreground-markers`, `lint-foreground` aliases) after each cluster.
- Smoke-test `/implement` Step 5 on a small issue to verify the early-exit cascade no longer fires and breadcrumb output is redacted.
- Smoke-test `/design` finalize publish to verify `design-log-publish.sh` still emits `PUBLISH_OK=true` on a clean run.

## Acceptance

This design is accepted when:

1. The 12 OOS items in the linked tracking issue body are each addressed by code, doc, or harness changes per the per-file sections above, with Item 3.3 explicitly dropped (per FINDING_4) and Item 3.2 retargeted to `scripts/ship-pr.sh:872-875` (per FINDING_6).
2. Plan-review FINDING_1 through FINDING_7 are reflected in the plan and in the implementation:
   - Linter `PARENT_UNSET_REQUIRED_CHILDREN` includes `review-and-fix.sh`, `ci-wait.sh`, `step2-implement.sh`, and the scan-gate widening allows any of them to be scanned.
   - All five existing nested Family-B call sites use the four-variable `env -u` form, placed within 5 nonblank noncomment lines of the nested invocation.
   - SECURITY.md `# render-cache` paragraph reflects narrowing-not-closing language (per FINDING_3).
3. Test harness changes pass:
   - `scripts/test-lint-foreground-markers.sh` covers the new `env -u` form (with literal, variable, and default-expansion shapes) and new child anchors.
   - `scripts/test-breadcrumb-monitor.sh` covers the early-exit cascade fix, the tmpdir redaction integration, drop-on-fail, and the parent EXIT trap preservation regression.
   - `scripts/test-design-log-publish.sh` covers the render-cache path-escape gap (Item 2B) and the post-enumeration tree-wide rescan for both plan-review and render-cache.
   - `scripts/test-mermaid-fragments.sh` covers the embedded-`=` `REASON_TOKEN` regression (Item 3.4).
4. `make lint` (including `lint-bash32`, `lint-foreground-markers`) passes after each cluster lands.
5. Operator-visible breadcrumb output redacts tmpdir paths during `/implement` Step 5 smoke tests; `/design` finalize publish still emits `PUBLISH_OK=true` on a clean run.

diff_lines: 320
