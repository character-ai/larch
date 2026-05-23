## Dialectic Resolutions

### DECISION_1: Claude tier delivery mechanism for the ship-pr.sh recovery waterfall

**Resolution**: Add a NEW narrow `scripts/launch-claude-ci.sh` next to existing `scripts/launch-cursor-ci.sh` and `scripts/launch-codex-ci.sh`.
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: Ship the Claude recovery tier as a new narrow scripts/launch-claude-ci.sh alongside scripts/launch-cursor-ci.sh and scripts/launch-codex-ci.sh, leaving scripts/launch-claude-subprocess.sh strictly on the read-only reviewer path. The subprocess script is explicitly documented and implemented as read-only at the header and in the injected reviewer instruction, while CI-fix already uses sibling launchers that ship-pr.sh already invokes in the fix flow.
**Antithesis summary**: Proportionality favors extending scripts/launch-claude-subprocess.sh with an explicit opt-in writer/recover mode that skips the read-only preamble and adjusts sidecar reason strings, instead of adding a parallel launch-claude-ci.sh that must re-derive the subprocess's path canonicalization, meta/dirty-tree contract, and timing-ledger hook. The read-only constraint is already prompt-level only per launch-claude-subprocess.md:17.
**Why thesis prevails**: All three judges (Cursor, Codex, Claude) concurred unanimously that the subprocess script's entire architecture (read-only header, hard preamble at line 135, the always-emitted `.dirty-tree` REASON=claude-subprocess-prompt-read-only at line 182, the dedicated test harness) is built around the reviewer persona, so adding a `--mode writer` flag would collapse two trust zones into one executable whose name and every diagnostic signal still advertise read-only. The established sibling CI launcher pattern (launch-cursor-ci.sh, launch-codex-ci.sh) is the correct model — they are already the launchers ship-pr.sh invokes for `--role fix` work at scripts/ship-pr.sh:1227-1234 and 1715-1726. The antithesis's strongest concession (avoiding ~200 lines of duplicated validation) is bounded by sourcing shared library helpers rather than full reimplementation, so the duplication cost is not load-bearing.

### DECISION_2: Local-reproduction verification mechanism

**Resolution**: Script-level mandatory post-tier verification — run `scripts/run-relevant-checks-captured.sh` after each waterfall tier for checks-class phases; for pr-create 9b where no failed-CI log exists locally, use dry-run probes (`git push --dry-run` + `gh pr view --json state`). Vendor prompts carry text-level guidance but enforcement is script-side.
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: ship-pr.sh already owns the enforceable acceptance boundary at scripts/ship-pr.sh:727 (`run-relevant-checks-captured.sh` re-run after each lint-fix application) and 1254 (`run_checks_with_lint_fix_loop` post-success gate). Script-side verification is independently executed, phase-specific, and already handles asymmetric sites such as PR-create where no failed-CI log exists.
**Antithesis summary**: The proportional choice is a machine-readable KV proof envelope (REPRO_CMD/REPRO_FAILED_BEFORE/VERIFY_CMD/VERIFY_PASSED_AFTER) emitted by the vendor and parsed by ship-pr.sh, because the repo already has envelope parsing and current vendor prompts only ask agents to inspect logs with no machine-readable proof fields.
**Why thesis prevails**: All three judges concurred. The antithesis's own risk_if_wrong concedes that KV proof can be spoofed by a vendor while the final independent verification still passes — which makes the KV envelope vendor-authored self-attestation, weaker than independently-executed verification. A uniform KV schema across phases also creates failure modes where valid fixes bail because the attestation shape is wrong on a non-uniform site (pr-create 9b has no failed-CI log to reproduce against). The existing post-launch verify already enforces the invariant at the acceptance boundary that matters. The machine-readable proof KV is recorded as a follow-up consideration but not part of the chosen path.

### DECISION_3: Apply local-reproduction invariant to EXISTING run_ci_fix_vendor

**Resolution**: Yes — the local-reproduction invariant (constraint A) applies to ALL CI fix paths, including the existing run_ci_fix_vendor 3-vendor cycle; implementation is prompt-text additions to existing launcher prompts plus reuse of the existing run_checks_with_lint_fix_loop post-launch verify (additive, not restructure).
**Disposition**: fallback-to-synthesis
**Thesis summary**: (no debate — quorum failed)
**Antithesis summary**: (no debate — quorum failed)
**Why fallback**: missing_tag — the thesis side (debate-3-cursor-thesis.txt) emitted opening tags `<claim>` / `<evidence>` / `<strongest_concession>` / `<counter_to_opposition>` / `<risk_if_wrong>` with substantive content but omitted the corresponding closing tags `</claim>` etc. The strict tag-pair regex used by the quorum gate did not match. Synthesis decision stands: the CI-fix local-reproduction invariant applies to the existing run_ci_fix_vendor via prompt + existing post-launch verify additions, not a structural change.

### DECISION_4: Per-tier rollback mechanism

**Resolution**: Dirty-tree-baseline + revert-on-tier-fail. Before each waterfall tier, capture `git rev-parse HEAD` baseline plus tracked/untracked dirty-paths via the existing `capture_tracked_dirty_paths` / `capture_untracked_dirty_paths` helpers. After tier completes (success or failure), run `run-relevant-checks-captured.sh` (or phase-appropriate verify). On tier-verify failure, revert via `git checkout -- <tracked_delta>` + `rm <untracked_delta>` mirroring `lint-fix-loop.sh`'s post_dispatch_forbidden_revert pattern. Assert `git rev-parse HEAD == baseline_head` post-tier; if the tier committed, hard-fail with `head-changed-after-dispatch`.
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: ship-pr.sh already owns mutation centrally and the launchers expose role-based execution (`--role fix`, `--role resolve-conflict`) rather than patch-emission APIs. Existing capture helpers at scripts/ship-pr.sh:50,54 and the rollback pattern in lint-fix-loop.sh:99-125 are already in place, making dirty-tree baseline locally incremental.
**Antithesis summary**: Tier produces a patch file (`$IMPLEMENT_TMPDIR/recovery-waterfall/<phase>/<tier>.patch`); ship-pr.sh applies, verifies, commits, and pushes. Tier launchers stay read-only by design; no half-fixes can leak into the working tree.
**Why thesis prevails**: All three judges concurred that the patch-file approach is cleaner conceptually but requires broader launcher semantics churn — changing the vendor `--role fix` / `--role resolve-conflict` contract from direct worktree mutation toward patch-emission APIs. The dirty-tree baseline + revert pattern matches existing conventions (lint-fix-loop.sh:99-125), reuses already-tested helpers (capture_tracked_dirty_paths at ship-pr.sh:50, capture_untracked_dirty_paths at ship-pr.sh:54), and has smaller semantic blast radius across Step 6-13 state transitions. The antithesis's own appendix noted that the patch-file approach is "probably too much for this issue".

### DECISION_5: Mid-waterfall crash-recovery state

**Resolution**: NO new state keys. If ship-pr.sh crashes mid-waterfall (host crash, signal, etc.), the resumed run restarts the recovery from the Cursor tier. Wall-time cost of one extra Cursor attempt is acceptable.
**Disposition**: fallback-to-synthesis
**Thesis summary**: (no debate — quorum failed)
**Antithesis summary**: Antithesis output was substantive but did not include a canonical `file:line` citation in the `<evidence>` block (the cited line ranges used en-dash form rather than `path.ext:NN`). The argument was: new RECOVERY_TIER/RECOVERY_PHASE/RECOVERY_ATTEMPT_COUNT keys would satisfy the existing validator regex and extend the require_key discipline already enforced, while resume routing for `--resume-phase` exists at scripts/ship-pr.sh:1988-2011.
**Why fallback**: missing_citation — the antithesis (debate-5-cursor-antithesis.txt) did not include a canonical `file.ext:line` citation pattern in the `<evidence>` block (it used "(lines 175–184)" prose form). Synthesis decision stands: keep state schema focused on phase-progression, not recovery-progression; mid-waterfall crashes are rare; restart cost is acceptable.

**Disposition counts**: 3 voted, 2 fallback.
