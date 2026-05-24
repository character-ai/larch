### FINDING_1: REBASE_ERROR and PHANTOM_APPEND_WARN_ERROR sourced from stderr instead of lib-quiet contract stream
**Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements (all 10)
**Severity**: important / correctness
**Concern**: The plan says the wrapper parses `REBASE_ERROR` from captured stderr on rc=3, and lib-phantom-probe parses `PHANTOM_APPEND_WARN_ERROR` from captured stderr of `append-execution-issue.sh`. But both helpers initialize `lib-quiet.sh` (`larch_quiet_init`) and emit their error KVs via `emit_kv` on the contract stream (stdout/FD3), not on stderr. Under normal redirects, `REBASE_ERROR` lands on the same captured stream as `SKIPPED_ALREADY_PUSHED` / `CONFLICT_FILES`. The plan's stderr-based parsing will yield empty or wrong `REBASE_ERROR`; similarly `PHANTOM_APPEND_WARN_ERROR` will often be empty when append fails. Test case 6 stubs would also encode the wrong contract.
**Proposed resolution**: Parse `REBASE_ERROR` from the rebase-push.sh captured stdout/contract stream (same file used for skip markers); parse append-execution-issue.sh `ERROR=` from its captured stdout/contract (or 2>&1 merge) with stderr fallback only when no `ERROR=` key is present. Update plan text and test stubs accordingly; document the parsing contract in `lib-phantom-probe.md` and `rebase-checkpoint-probe.md`.


### FINDING_10: chmod +x not specified for new .sh files
**Reviewers**: Codex-Requirements (1)
**Severity**: important / risk-integration
**Concern**: SKILL.md invokes wrappers directly via `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` (not `bash scripts/...`). If the new files land as 0644, Makefile bash invocations in test harnesses still pass, but `/implement` direct invocations fail with permission denied. The plan has no chmod step.
**Proposed resolution**: Add a plan step: chmod +x for all new executable `.sh` files (`rebase-checkpoint-probe.sh`, `phantom-probe-with-warn.sh` — the lib- and test- siblings stay 0644). Add a harness assertion in `test-implement-rebase-macro.sh` or one of the new harnesses that the two runtime wrappers are executable.


### FINDING_12: SKILL fences omit export LARCH_QUIET_BREADCRUMBS=1
**Reviewers**: Cursor-Arch (1)
**Severity**: important / architecture
**Concern**: The wrapper's `emit_breadcrumb` call relies on `LARCH_QUIET_BREADCRUMBS` / `LARCH_QUIET_BREADCRUMB_FD` behavior (`lib-quiet.sh` lines 114-125). Step 8+ in `/implement` already exports `LARCH_QUIET_BREADCRUMBS=1` at its call sites (skills/implement/SKILL.md:1570-1576). The six new wrapper fences proposed by the plan don't include that export, so under quiet redirect the breadcrumb may go to the quiet log rather than the visible transcript — operators see no `→ rebase-probe: …` line.
**Proposed resolution**: Mirror the ship-pr pattern: add `export LARCH_QUIET_BREADCRUMBS=1` to each of the 6 new wrapper fences in SKILL.md, OR document that the harness sets this env and adjust the breadcrumb-count test cases (14 in test-rebase-checkpoint-probe.sh, 7 in test-phantom-probe-with-warn.sh) to set it themselves.


### FINDING_16: SKILL.md phantom probe pointer says "5 sites total" but with 1.r-post-rebase added the actual count is 6
**Reviewers**: Codex-Pragmatic (1)
**Severity**: nit / correctness
**Concern**: The plan's Region 2 thin pointer prose says "The probe runs at **5 sites total**". After the 1.r-post-rebase addition (discussion-round1 Decision 1), the count is 6 (4 combined + 2 standalone). The wrong count in the pointer prose contradicts the new 1.r-post-rebase behavior described elsewhere in the plan and can confuse future call-site count tests.
**Proposed resolution**: Change the count to 6 (4 combined absorbed sites + 2 standalone) — or explicitly distinguish "5 pre-existing sites + 1 new 1.r-post-rebase site for uniformity" in the SKILL.md pointer prose.


### FINDING_2: Test invariant (E) wrongly marked "unchanged" — 7.r anchor must retarget to wrapper invocation
**Reviewers**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements (4)
**Severity**: important / correctness
**Concern**: `scripts/test-implement-rebase-macro.sh` invariant (E) currently locates the Step 7.r macro line via `grep -nF` on `Apply the Rebase Checkpoint Macro with <step-prefix>=7.r`. After SKILL.md edits replace the Apply line with the new `rebase-checkpoint-probe.sh 7.r 'commit (review)'` fence, the grep returns nothing and (E) fails — even when `FILES_CHANGED=true` guard prose is correct. The plan's UPDATED section for `test-implement-rebase-macro.sh` marks (E) "unchanged" but it must retarget.
**Proposed resolution**: Update (E) to anchor on the new `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh" 7.r 'commit (review)'` invocation line; revise the plan bullet to state (E) is retargeted, not unchanged.


### FINDING_3: Region 2 doesn't explicitly remove post-macro phantom prose at Steps 4.r/7.r/7a.r
**Reviewers**: Cursor-Arch, Cursor-Pragmatic (2)
**Severity**: important / architecture
**Concern**: The plan's Region 2 edits to SKILL.md call out only Steps 2 (post-dispatch) and 8 (pre-bump) as standalone probe sites. But existing "After the macro returns, run the Phantom Untracked Probe" paragraphs follow the macro invocations at Steps 4.r, 7.r, and 7a.r (skills/implement/SKILL.md:1178-1179, 1370-1373, 1464-1465). Since `rebase-checkpoint-probe.sh` already runs the post-rebase phantom probe internally, leaving those paragraphs would double-invoke `check-phantom-dirty.sh` and duplicate Warnings entries.
**Proposed resolution**: Add explicit SKILL.md edit bullets to delete the post-macro phantom probe paragraphs (and any inline fenced probe blocks) after Steps 4.r, 7.r, and 7a.r once `rebase-checkpoint-probe.sh` owns those probes.


### FINDING_4: Forked-target argv should be conditional at ALL 4 rebase checkpoint fences, not just 1.r
**Reviewers**: Codex-Innovation (1)
**Severity**: important / correctness
**Concern**: The plan example shows `[--base-remote upstream --base-ref main when forked_target=true]` only at the 1.r fence, but the existing macro M1 prose passed those args at all 4 sites conditionally on `forked_target=true`. Forked runs after implementation/review/diagrams must rebase against `upstream/main` too — restricting the argv to 1.r would silently change fork-mode behavior at 4.r/7.r/7a.r and delay upstream conflicts until later gates.
**Proposed resolution**: Pass `--base-remote upstream --base-ref main` conditionally at all four rebase checkpoint fences (1.r, 4.r, 7.r, 7a.r) — same `forked_target=true` guard at each. Pin this in `test-implement-rebase-macro.sh` (new sub-assertion under invariant (C)) so future edits cannot drop the argv at any site.


### FINDING_5: Literal `[--base-remote upstream --base-ref main when forked_target=true]` inside bash fence is invalid shell
**Reviewers**: Codex-Edge, Codex-Pragmatic (2)
**Severity**: important / correctness
**Concern**: The plan's SKILL.md call-site fence example contains the literal token `[--base-remote upstream --base-ref main when forked_target=true]` inside a runnable bash invocation. If an implementer copies it verbatim, the wrapper receives `[--base-remote` as an unknown flag and the 1.r checkpoint fails on argv parsing. If they delete the bracket without replacing it, forked runs lose the upstream/main argv.
**Proposed resolution**: Replace the bracket placeholder with real conditional shell — e.g., `if [ "${forked_target:-false}" = "true" ]; then BASE_ARGS=(--base-remote upstream --base-ref main); else BASE_ARGS=(); fi` then `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh" 1.r 'plan materialization' "${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"` — or show two concrete one-line examples (non-forked + forked) and mark the bracket as prose annotation only.


### FINDING_6: Makefile targets need .PHONY + test-harnesses-N shard assignment, not "make test" aggregate
**Reviewers**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Edge, Codex-Requirements (5)
**Severity**: important / risk-integration
**Concern**: The plan says "wire both into the aggregate `test` (or equivalent meta-target) so `make lint` / `make test` exercises them" — but the repo has no top-level `make test`. The repo's lint gate uses `make lint` → `test-harnesses` aggregate → `test-harnesses-1` … `test-harnesses-20` shards (Makefile:12-40). `scripts/test-harness-shards-coverage.sh` verifies every test target is wired into exactly one shard AND listed in `.PHONY`. Without explicit shard assignment, `make lint` will either fail the shard-coverage guard or never run the new harnesses.
**Proposed resolution**: Add explicit plan steps: (a) add both `test-rebase-checkpoint-probe` and `test-phantom-probe-with-warn` to the giant `.PHONY` list, (b) append each as a prerequisite of exactly one `test-harnesses-N` shard alongside peer test scripts, (c) run `make test-harness-shards-coverage` to verify, (d) drop the inaccurate "make test" wording from plan testing strategy.


### FINDING_7: agent-lint.toml allowlist needed for new sourced and Makefile-only files
**Reviewers**: Codex-Arch, Codex-Innovation, Codex-Requirements, Cursor-Requirements (4)
**Severity**: important / risk-integration
**Concern**: `make lint` runs agent-lint G004 / S030 / dead-script checks. These don't follow `source` directives or Makefile-only test harness invocations. The new `scripts/lib-phantom-probe.sh` (sourced-only) + `scripts/lib-phantom-probe.md` + the two test harness pairs (`test-rebase-checkpoint-probe.{sh,md}`, `test-phantom-probe-with-warn.{sh,md}`) will all be flagged as dead/orphaned unless added to the agent-lint allowlist following the existing peer pattern (lib-dirty-tree-sidecar, test-implement-rebase-macro).
**Proposed resolution**: Extend the plan with an explicit UPDATED section for `agent-lint.toml`: add allowlist entries (with comments) for `scripts/lib-phantom-probe.sh`, `scripts/lib-phantom-probe.md`, `scripts/test-rebase-checkpoint-probe.sh`, `scripts/test-rebase-checkpoint-probe.md`, `scripts/test-phantom-probe-with-warn.sh`, and `scripts/test-phantom-probe-with-warn.md`. Mirror the comment style from the existing `lib-dirty-tree-sidecar` / `test-implement-rebase-macro` allowlist rows.


### FINDING_8: PATH-injection stubbing strategy conflicts with SCRIPT_DIR helper resolution (security)
**Reviewers**: Codex-Edge, Codex-Pragmatic, Codex-Requirements (3)
**Severity**: important / security
**Concern**: The test harness plan stubs `rebase-push.sh`, `check-phantom-dirty.sh`, and `append-execution-issue.sh` via PATH injection. But the repo pattern (used by `check-phantom-dirty.sh:6-9`, `rebase-push.sh:78-81`, peer launchers) resolves sibling scripts via `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`. Two failure modes: (a) if production wrappers use bare command names to make the PATH stubs work, a polluted PATH in consumer repos can hijack runtime helper calls; (b) if wrappers correctly use SCRIPT_DIR, the harness's PATH injection never intercepts the helpers and tests hit real git/rebase code instead of stubs.
**Proposed resolution**: Production wrappers MUST call helpers via `"$SCRIPT_DIR/helper.sh"`. The harness either (a) copies the wrapper + library into a temp scripts directory with sibling stub helpers in the same directory, or (b) accepts an explicit test-only `--helper-dir <path>` override (validated to a temp directory) — not PATH injection. Document the chosen approach in both `.md` sibling docs.


### FINDING_9: REBASE_OUTCOME=failed conflates exit 3 (non-conflict bail) with other-rc (unexpected exit)
**Reviewers**: Cursor-Requirements (1)
**Severity**: important / correctness
**Concern**: The plan's orchestrator-side M2 routing prose (in the new SKILL.md thin pointer) lists one `REBASE_OUTCOME=failed` template. But today's macro M2 prose has two distinct user-visible messages: (a) exit 3 → `**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**`; (b) other non-zero → `**⚠ Rebase onto main failed unexpectedly (exit $rc). Bailing to cleanup.**`. The single failed template degrades the operator-visible contract.
**Proposed resolution**: Distinguish the two branches via the `REBASE_ERROR` token. Wrapper emits `REBASE_ERROR=<actual-message>` on rc=3 and `REBASE_ERROR=unexpected-rc-<n>` on other-rc (as the plan already does). Orchestrator-side M2 routing branches on whether `REBASE_ERROR` starts with the literal `unexpected-rc-` prefix and selects the corresponding user-visible string. Keep both messages in the SKILL.md thin pointer.


