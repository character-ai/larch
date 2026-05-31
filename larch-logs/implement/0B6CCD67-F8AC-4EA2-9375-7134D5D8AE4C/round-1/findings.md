### FINDING_1: Stale “convergence streak” prose in env docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-caller-sweep-completeness-output.txt
- **Severity**: important
- **Concern**: `docs/configuration-and-permissions.md` (~line 250) still describes plan-review convergence with a “streak” / two-round streak semantics after `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and streak machinery were removed. Operators and doc grep can believe streak-based stopping still applies, conflicting with the single-round hardcoded rule (≤5 non-nit accepted, 0 important accepted, nits excluded) documented elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-sweep-completeness-output.txt: Reword line 250 to match `skills/design/references/flags.md` and `plan-review.md` — e.g. “Plan-review convergence (≤5 non-nit accepted, 0 important; nits excluded) is hardcoded in `plan-review-loop.sh`” — with no mention of streak.

### FINDING_2: Duplicated block-aware awk nit counters across review loops
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.sh` (~206–220) and `skills/review-and-fix/scripts/review-and-fix.sh` (~130–144) duplicate block-aware awk nit-count logic. A future severity-marker or block-format change must be patched in both places or the loops diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helper or add explicit keep-in-sync comment between copies.

### FINDING_3: Misleading harness banner still references convergence streak
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` (~1631) test section title/echo still refers to “convergence streak” / “resets convergence streak” after single-round convergence; misleading for maintainers debugging harness behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update echo string to reflect single-round converged reason.
  - From cursor-specialist-testing-output.txt: Rename echo to degraded-then-converged or similar.

### FINDING_4: Missing test for converged termination when snapshot fails
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness asserts converged termination when `_snapshot_round_dir` fails after a qualifying round. A regression could yield `panel-failed` or wrong `REASON` instead of preserving `converged` / `converged,snapshot-failed` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add integration case forcing snapshot failure after `NON_NIT_ACCEPTED_COUNT<=5` and assert `LOOP_STATUS=converged` and `REASON=converged,snapshot-failed`.

### FINDING_5: Plan-required nit-heavy convergence case not exercised (`many_nits_three_latent`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `many_nits_three_latent` collect mode exists in `skills/design/scripts/test-plan-review-loop.sh` (~349–366) but is not wired into any `run_loop` case. Plan acceptance for many nits + ≤5 non-nit convergence is only partially covered by separate cases; combined tally path and nit-heavy boundary could regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Wire `many_nits_three_latent` into a converging `run_loop` and assert `NIT_ACCEPTED_COUNT` and `NON_NIT_ACCEPTED_COUNT=3`.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test invoking `write_collect many_nits_three_latent` asserting converged `REASON=converged` `NIT_ACCEPTED_COUNT=10` `NON_NIT_ACCEPTED_COUNT=3` `ROUNDS_COMPLETED=1`.

### FINDING_6: Prior-round Important no longer blocks Part A convergence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` Part A convergence (~1372–1430) now calls `important_findings_present` only on the current round’s `findings.md`; the prior non-degraded round is no longer scanned. Because matching hits Important title/concern patterns anywhere in the file (not only accepted blocks), a round-1 Important security finding left in `round-1/findings.md` after rejection may no longer block round-2 `converged-small-changes` if round-2’s file is clean. Tests do not pin this behavior after removal of `previous-round important_scan_files`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add round-3 clean stub with Important only in round-2 `findings.md`; expect `converged-small-changes`.
  - From cursor-specialist-security-output.txt: If the intent is “no open Important-class concerns across recent rounds,” keep scanning the previous non-degraded round’s `findings.md` (or derive Important checks from accepted population only, consistently). If rejection is meant to clear the gate, document that explicitly in `review-and-fix.md` / Step 5 prose so operators know prior-round Important markers are ignored.

### FINDING_7: No harness guard for removed `--convergence-threshold` flag
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removed invalid `--convergence-threshold` test was not replaced with an unknown-option guard. External callers still passing the flag get exit 2 at runtime; CI lacks an automated fail-closed pin beyond SKILL absence checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expect exit 2 from `review-and-fix.sh` and `plan-review-loop.sh` when passed `--convergence-threshold`.

### FINDING_8: Single-round convergence allows unlimited accepted nits / latent security items
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` and `review-and-fix.sh` can terminate after one non-degraded round with ≤5 non-nit accepted and zero important accepted while unlimited nit-severity accepted findings (and latent or mis-tagged items) remain on the accepted list. Only the `important` gate and round cap bound exposure; operators expecting multi-round security depth may underestimate early exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: No code change required if this is the accepted product tradeoff; operators relying on multi-round review for security depth should treat `LARCH_DESIGN_ROUND_CAP` / implement round cap as the real backstop and ensure reviewers use `important` for material security issues, not `nit`/`latent`.

### FINDING_9: `/cleanup` retention uses `find -maxdepth 5` for activity gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh` (~18–31) deletes stale top-level session directories when `find "$entry" -maxdepth 5 -mtime -"$RETENTION_DAYS"` finds nothing recent; activity deeper than five levels does not protect the tree, which may hold session-scoped secrets per `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document the depth-5 limit for operators (already in `SECURITY.md`); if long-lived nested layouts are common, raise `maxdepth` or add an explicit keepalive marker check before delete.

### FINDING_10: Missing convergence narrative in `plan-review-loop.md`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan asked for updated convergence prose in `skills/design/scripts/plan-review-loop.md`; only KV/argv tables changed. Consumers of the driver `.md` sibling without `plan-review.md` may miss nit-exclusion and single-round semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a short Convergence (multi-round) subsection aligned with `plan-review.md`.

### OOS_1: [OUT_OF_SCOPE] PR bundles convergence with unrelated cleanup and logs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Branch/PR combines convergence changes with Step 2b.5 override cleanup retention, cleanup skill work, and `larch-logs`, making bisection, rollback, and CI signal attribution harder than a focused convergence PR; unrelated harness or flake failures could obscure convergence regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split or document intentional merge batch in PR description.
  - From cursor-specialist-testing-output.txt: Split PR or isolate commits for reviewability.

### OOS_2: [OUT_OF_SCOPE] Top-level cache `find` fail-open in `SECURITY.md` predates this branch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` (~176–177) documents that top-level cache enumeration `find` failures are fail-open (exit 0, no warning, no deletions), extending retention of session tmpdirs that may contain secrets. This predates the branch’s nested-scan fail-safe; not introduced by convergence work.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — reviewer noted as documented, pre-existing; no actionable fix beyond awareness)
