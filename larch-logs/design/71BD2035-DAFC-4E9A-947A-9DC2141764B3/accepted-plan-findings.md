### FINDING_1: Wrong lifecycle location for final-bail-reason larch-log write
- **Concern**: Plan wires the new `final-bail-reason` batch publish into `scripts/refresh-run-logs.sh`. But `refresh-run-logs.sh` is invoked only from `ship-pr.sh` at pre-push checkpoints (bump/postbump ~908, CI-fix push ~1432, rebase ~1949). Terminal `exit 3` (bail) and `exit_stall` (exit 4) paths exit ship-pr.sh WITHOUT calling `refresh-run-logs.sh`. Additionally, `$IMPLEMENT_TMPDIR/final-bail-reason.txt` is NOT written by ship-pr on bail/stall — `write_finalize_state()` is invoked only from `run_postmerge_phase` (after merge success); the file is actually produced by `scripts/restore-finalize-state.sh` at `/implement` Step 18, AFTER ship-pr has exited. Net effect: on real bail/stall (the very paths the issue targets), the planned write never runs.
- **Proposed resolution**: Move the `larch-log.sh write --batch final-bail-reason --input-file "$IMPLEMENT_TMPDIR/final-bail-reason.txt"` call out of `refresh-run-logs.sh`. Best placement is **inside `scripts/restore-finalize-state.sh`** at the end of `write_finalize_state()` (right after `printf '%s' "$(read_state BAIL_REASON)" > "$BAIL_REASON_FILE"` at line 71), guarded by `[ -s "$BAIL_REASON_FILE" ]` so empty postmerge-restored files are no-ops. Alternative placement: `scripts/implement-finalize.sh teardown` BEFORE the cleanup branch — but restore-finalize-state.sh is the cleaner choice because it owns the bail-reason file lifecycle. Update the sibling `.md` accordingly. Drop the planned `refresh-run-logs.sh` change.
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-exit-contract, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-batch-registration, Codex-dyn-exit-contract (13 reviewers, unanimous)
- **Severity**: Critical (plan does not achieve its stated goal)


### FINDING_11: ci-wait stdout contract may need lockstep doc update
- **Concern**: `ci-decide.sh`'s emitted BAIL_REASON values are described in its sibling `.md` and in `scripts/ci-wait.md` (which forwards them). Adding the exact-match token `fix-attempts-exhausted` may need a doc-level mention so downstream consumers (e.g., implement Step 16 / Step 12d) know to recognize this token as terminal-and-user-input vs. a transient signal.
- **Proposed resolution**: Verify (and if missing, add) a one-line entry in `scripts/ci-decide.md` and/or `scripts/ci-wait.md` listing `fix-attempts-exhausted` as one of the exact-match terminal BAIL_REASON tokens, with a pointer to `ship-pr.sh:needs_user_bail_reason` and `/implement` Step 16 (SKILL.md:1595).
- **Reviewers**: Cursor-dyn-exit-contract (1 reviewer)
- **Severity**: Important risk-integration


### FINDING_12: refresh-run-logs.sh harness coverage
- **Concern**: Plan modifies `refresh-run-logs.sh` (the original plan; superseded by FINDING_1's relocation). If FINDING_1 is accepted and the write moves out of refresh-run-logs.sh, this finding becomes moot. If for some reason the write stays in refresh-run-logs.sh, then `scripts/test-refresh-run-logs.sh` needs a new assertion covering the `final-bail-reason` publish.
- **Proposed resolution**: Per FINDING_1, the write moves to `restore-finalize-state.sh`, which has its own harness `scripts/test-restore-finalize-state.sh`. Update that harness instead: assert that after `write_finalize_state` runs, the batch is published when the file is non-empty. Or update `scripts/test-implement-finalize.sh` if the move is to `implement-finalize.sh teardown`. Drop the `test-refresh-run-logs.sh` requirement entirely.
- **Reviewers**: Codex-Pragmatic, Codex-Requirements (2 reviewers)
- **Severity**: Important risk-integration (consequence of FINDING_1)

---

## OOS Items


### FINDING_4: Plan's failure-mode prose is inconsistent with `|| true` pattern
- **Concern**: Plan §"Failure modes" claim #3 says "on failure the bail-reason file remains in `$IMPLEMENT_TMPDIR` (until cleanup) and `execution-issues.md` records the write failure as a `Warnings` row." But the adjacent `token-report` / `timing-report` writes in `refresh-run-logs.sh` (lines 76, 79) use `2>/dev/null || true` — silent failure, no Warnings append. Net effect: the plan's stated mitigation does not match the prescribed code pattern.
- **Proposed resolution**: Choose one of two paths and update the plan to match:
  - (a) Match the silent pattern: drop the "Warnings row" claim; the failure is silent by design, consistent with adjacent batch writes. Update the failure-mode prose.
  - (b) Add an explicit `append-tool-failure.sh` call under a non-zero exit branch from the new `larch-log.sh write` call; document this divergence from the adjacent silent pattern.
  Recommend (a) — silent failure is the established pattern, and the BAIL_REASON content survives in `ship-pr-state.sh:BAIL_REASON` regardless of the batch publish outcome.
- **Reviewers**: Cursor-dyn-batch-registration, Cursor-Edge, Cursor-Pragmatic (3 reviewers)
- **Severity**: Nit-important boundary


### FINDING_5: Fragment-load path ambiguity (`$SCRIPT_DIR/..` OR `$PLUGIN_ROOT`)
- **Concern**: Plan §"Approach" specifies two alternative paths for loading the fragment: "`$SCRIPT_DIR/../skills/shared/ci-fix-failure-patterns.md` (or `$PLUGIN_ROOT/skills/...` where the launcher already resolves `PLUGIN_ROOT`)". This is ambiguous — three launchers may pick different conventions, the launcher-parity rule then catches the drift instead of preventing it. All three CI launchers already define `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"` near the top — pick one.
- **Proposed resolution**: Specify `${PLUGIN_ROOT}/skills/shared/ci-fix-failure-patterns.md` as THE canonical path. Update the plan and acceptance to require this exact form across all three launchers. Drop the `$SCRIPT_DIR/..` alternative from the plan.
- **Reviewers**: Cursor-dyn-launcher-parity, Codex-dyn-launcher-parity (2 reviewers)
- **Severity**: Important architecture


### FINDING_6: Sentinel-substring assertion under-specified
- **Concern**: Plan's launcher-test acceptance says "a sentinel substring from the fragment file (e.g. the literal phrase `topology.tsv` or `generate-topology-docs.sh`)". The "OR" means individual test files could pick different sentinels, weakening cross-launcher parity coverage. The launcher-parity rule wants identical assertion shape across the three test files.
- **Proposed resolution**: Pick ONE sentinel substring (recommend `topology.tsv`) and require all three test files (`test-launch-{cursor,codex,claude}-ci.sh`) to assert exactly that substring is in the rendered `$PROMPT_FILE` under `ROLE=fix`. Update the plan acceptance accordingly.
- **Reviewers**: Cursor-dyn-launcher-parity, Codex-dyn-launcher-parity (2 reviewers)
- **Severity**: Nit correctness


### FINDING_7: Edge-cases prose inverts `write_finalize_state` lifecycle
- **Concern**: Plan §"Edge cases" says: "`final-bail-reason.txt` not written: `write_finalize_state` only runs on bail paths; happy-path runs (`merged`) skip it." This is BACKWARDS. `write_finalize_state` runs ONLY on the postmerge happy path (`run_postmerge_phase` at ship-pr.sh:2317). Bail/stall paths exit without calling it; the file is produced LATER by `restore-finalize-state.sh` at Step 18.
- **Proposed resolution**: Correct the edge-case text. Restate as: "`final-bail-reason.txt` is written either (a) by `ship-pr.sh:write_finalize_state` on the postmerge happy path with `BAIL_REASON=''` (so the file is empty), or (b) by `restore-finalize-state.sh` at `/implement` Step 18 with the actual bail/stall BAIL_REASON from `ship-pr-state.sh`." Combined with FINDING_1's relocated write site, the new batch publish IS guaranteed to fire on bail/stall paths.
- **Reviewers**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic (3 reviewers)
- **Severity**: Nit-important


### FINDING_8: Test stub launcher exit-code protocol mismatch
- **Concern**: Plan §"Testing strategy" describes the new test as "stubs all three CI launchers to fail" — and §"Approach" says "stubs `launch-cursor-ci.sh` + `launch-codex-ci.sh` + `launch-claude-ci.sh` (all return non-zero)". But the production CI launchers actually exit 0 from the wrapper and signal failure via the `LAUNCHER_EXIT=N` KV line on stdout (parsed by `awk` in `run_ci_fix_vendor` line ~1364). Returning non-zero from the wrapper sets `wrapper_rc != 0`, which is also failure but a different path through the vendor loop.
- **Proposed resolution**: Update plan to specify stubs emit `LAUNCHER_EXIT=1\n` on stdout AND exit 0 from the wrapper (matching production protocol). Acceptance criterion #6 should require this exact protocol so the test exercises the same parser branch as a real launcher failure. Alternatively, stubs may use a mix to cover both `wrapper_rc != 0` and `LAUNCHER_EXIT != 0` paths.
- **Reviewers**: Codex-Innovation (1 reviewer)
- **Severity**: Latent


