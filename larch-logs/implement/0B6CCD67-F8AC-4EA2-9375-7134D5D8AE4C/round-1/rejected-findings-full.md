### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated block-aware awk nit counters across review loops
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.sh` (~206–220) and `skills/review-and-fix/scripts/review-and-fix.sh` (~130–144) duplicate block-aware awk nit-count logic. A future severity-marker or block-format change must be patched in both places or the loops diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helper or add explicit keep-in-sync comment between copies.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Prior-round Important no longer blocks Part A convergence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` Part A convergence (~1372–1430) now calls `important_findings_present` only on the current round’s `findings.md`; the prior non-degraded round is no longer scanned. Because matching hits Important title/concern patterns anywhere in the file (not only accepted blocks), a round-1 Important security finding left in `round-1/findings.md` after rejection may no longer block round-2 `converged-small-changes` if round-2’s file is clean. Tests do not pin this behavior after removal of `previous-round important_scan_files`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add round-3 clean stub with Important only in round-2 `findings.md`; expect `converged-small-changes`.
  - From cursor-specialist-security-output.txt: If the intent is “no open Important-class concerns across recent rounds,” keep scanning the previous non-degraded round’s `findings.md` (or derive Important checks from accepted population only, consistently). If rejection is meant to clear the gate, document that explicitly in `review-and-fix.md` / Step 5 prose so operators know prior-round Important markers are ignored.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: No harness guard for removed `--convergence-threshold` flag
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removed invalid `--convergence-threshold` test was not replaced with an unknown-option guard. External callers still passing the flag get exit 2 at runtime; CI lacks an automated fail-closed pin beyond SKILL absence checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expect exit 2 from `review-and-fix.sh` and `plan-review-loop.sh` when passed `--convergence-threshold`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Single-round convergence allows unlimited accepted nits / latent security items
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` and `review-and-fix.sh` can terminate after one non-degraded round with ≤5 non-nit accepted and zero important accepted while unlimited nit-severity accepted findings (and latent or mis-tagged items) remain on the accepted list. Only the `important` gate and round cap bound exposure; operators expecting multi-round security depth may underestimate early exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: No code change required if this is the accepted product tradeoff; operators relying on multi-round review for security depth should treat `LARCH_DESIGN_ROUND_CAP` / implement round cap as the real backstop and ensure reviewers use `important` for material security issues, not `nit`/`latent`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `/cleanup` retention uses `find -maxdepth 5` for activity gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh` (~18–31) deletes stale top-level session directories when `find "$entry" -maxdepth 5 -mtime -"$RETENTION_DAYS"` finds nothing recent; activity deeper than five levels does not protect the tree, which may hold session-scoped secrets per `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document the depth-5 limit for operators (already in `SECURITY.md`); if long-lived nested layouts are common, raise `maxdepth` or add an explicit keepalive marker check before delete.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

