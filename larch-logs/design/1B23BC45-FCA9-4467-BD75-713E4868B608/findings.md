### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-path-grant-audit
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:12,37-40; skills/review-and-fix/scripts/test-review-and-fix.sh (proposed assertion)
- **Concern**: Plan claims relocated snapshots sit outside Codex --add-dir "$PWD" without stating the IMPLEMENT_TMPDIR-not-under-PWD precondition. Scenario: Codex grants are -C "$PWD", --add-dir "$round_dir" ($IMPLEMENT_TMPDIR/round-N), --add-dir "$PWD" (repo root). Snapshot path is $IMPLEMENT_TMPDIR/.pre-coder-snapshots/round-N. That is outside --add-dir round_dir, but still inside --add-dir "$PWD" whenever IMPLEMENT_TMPDIR is under the repo (harness uses $work/implement; API allows it). A hostile coder could still tamper with snapshots in that layout. Proposed test only asserts snap_dir is not under round_dir/, not outside PWD.
- **Proposed resolution**: Qualify plan.txt:12 and Approach bullet 40: unreachable vs Codex requires IMPLEMENT_TMPDIR outside $PWD (production: session-setup cache via run-step5-review.sh:144). Document the invariant in review-and-fix.md. Do not claim unconditional --add-dir PWD exclusion unless adding enforcement (out of scope for SIMPLE).
