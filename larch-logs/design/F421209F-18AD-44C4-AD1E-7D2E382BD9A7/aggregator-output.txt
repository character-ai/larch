### FINDING_1: Missing freshness guard in Step 8 routing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Step 8 routing reference still lets `NEXT_ACTION=continue` reach ci-fix/reship without a `.ship-pre-fix-rebase-ok` freshness check, and the missing-sentinel path can end up in operator-bail instead of the intended post-driver stall handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the guard to post-driver stall only (Step 16 with STALL_TRACKING, then Step 18), matching existing NEXT_ACTION=stall handling; do not use operator-bail for this mechanical failure
  - From Codex-Arch: Add the same PRE_FIX_REBASE_REQUIRED plus .ship-pre-fix-rebase-ok fail-closed check to the reship and ci-fix branch semantics in ship-pr-exit-matrix.md, or make that reference defer explicitly to the SKILL.md guard before continuing.
  - From Codex-Innovation: Update ship-pr-exit-matrix.md reship and ci-fix branch semantics to require the same sentinel check when PRE_FIX_REBASE_REQUIRED=true before stale-handoff clear or loading ship-pr-ci-fix.md.
  - From Cursor-Pragmatic: A `### UPDATED:` `skills/implement/references/ship-pr-exit-matrix.md` entry: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require `.ship-pre-fix-rebase-ok` when `PRE_FIX_REBASE_REQUIRED=true` before stale-handoff clear or `ship-pr-ci-fix.md`; stall/operator-bail if absent. Mirror on `reship`.
  - From Codex-Pragmatic: Add the same no-checks REASON allowlist, conflict-metadata routing, and PRE_FIX_REBASE_REQUIRED plus sentinel guard to this reference, matching SKILL.md and dispatch_ship.

### FINDING_2: Guard-order regression tests incomplete
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The regression coverage does not pin the order between the allowlisted phase14 skip, the in-progress rebase probe, and the conflict-path state write, so a paused rebase could be skipped and the conflict branch may miss the `PHASE=rebase` assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a test with allowlisted REASON plus rebase_in_progress=True and no conflict metadata expecting PRE_FIX_REBASE_STATUS=stall; extend test_ship_pre_fix_rebase_routes_existing_conflict_handoff to assert PHASE=rebase in ship-pr-state.sh

### FINDING_3: Execution-issue loader drops committed rows
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The execution-issues resolver still treats non-empty tmpdir markdown as a replacement for run-dir NDJSON, but flushes can clear `execution-issues.md` after writing NDJSON, so later tmpdir-only failures can cause the final report to drop previously committed rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the helper plan to merge run-dir NDJSON groups with non-empty tmpdir markdown groups, or parse both and choose the richer combined result by event identity/count. Keep NDJSON-only and empty-tmpdir fallback.
  - From Codex-Innovation: Merge run-dir NDJSON and non-empty tmpdir markdown when both exist, with dedupe if needed. Keep the NDJSON fallback only when tmpdir markdown is absent or empty.
  - From Codex-Pragmatic: When both sources exist and tmpdir markdown is non-empty, parse both and merge/dedupe detail groups, with NDJSON-only fallback for empty markdown and degraded legacy rows preserved.
  - From Codex-Requirements: When both artifacts exist, parse both and merge or collapse by dedupe key; only fall back to one source when the other is absent or empty. Update the planned tests to assert the union.

### FINDING_4: Phase14 skip trusts stale metadata
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The allowlisted phase14 skip can still trust stale or incomplete handoff metadata, so a later `ci-fix` handoff can bypass the guarded rebase or a legitimate no-checks reship can stall because the freshness sentinel was not written on the valid skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require both RESUME_PHASE=config.SHIP_PR_RRR_RESUME_PHASE and an allowlisted REASON before skip. Treat missing or mismatched RESUME_PHASE the same as empty, bare, conflict-shaped, or disallowed flags.
  - From Cursor-Pragmatic: Unify contract language: write `.ship-pre-fix-rebase-ok` on physical rebase success, allowlisted phase14 skip (`PRE_FIX_REBASE_STATUS=skip`), and conflict-fix routing. Keep regression tests explicit for the skip branch.
  - From Codex-Requirements: Allow the phase14 skip only when the current `.ship-route-exit-handoff.env` proves `NEXT_ACTION=reship` for `DETAIL=no-ci-checks-observed` plus the allowlisted flag reason, or clear the phase14 flag on every non-no-checks handoff.

### FINDING_5: Exec-issue Python tests are not superset fixtures
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Python precedence tests use disjoint tmpdir and NDJSON fixtures, so they do not model a flushed-superset case and can encode dropping committed NDJSON rows instead of preserving post-flush appends.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Model superset fixtures: markdown contains flushed NDJSON content plus newer tmpdir-only rows. Assert combined counts/listings include both committed and post-flush entries; keep empty-markdown NDJSON fallback coverage separate.

### FINDING_6: Exec-issue shell harness expects wrong precedence
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The bash write-final-report harness still asserts a single-source dual-artifact precedence, so once the loader prefers non-empty tmpdir markdown the CI-facing summary check will fail or codify the wrong counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/scripts/test-write-final-report.sh`: revise the dual-artifact block to expect tmpdir markdown counts when both files exist; keep the existing NDJSON-only fallback case after removing markdown; add a second dual-artifact case if both sources must contribute to the summary
