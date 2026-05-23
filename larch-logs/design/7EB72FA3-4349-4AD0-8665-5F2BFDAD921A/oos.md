### OOS_1: `is_security_block` `probe_rc` capture in skipped-finding security split
- **Description**: `review-and-fix.sh:1104-1136` — the skipped-finding security classifier uses `probe_rc=$?` in the `else` branch after `if is_security_block ...; then ... else probe_rc=$?; fi`. Classifier exit `2` can be misclassified as non-security skips. Affected file: `skills/review-and-fix/scripts/review-and-fix.sh:1104-1136`.
- **Reviewer**: Cursor-Arch, Cursor-Pragmatic


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: `.review-boundary-passed` sentinel ownership at Step 6 entry
- **Description**: `skills/implement/SKILL.md:1302-1305` — `.review-boundary-passed` is still owned by Step 6 entry. Ensure no reviewer assumes collapsing Step 5 moves that sentinel (plan does not claim it, but cross-skill regressions are easy). Affected file: `skills/implement/SKILL.md:1302-1305`.
- **Reviewer**: Cursor-Pragmatic


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_3: numstat path/extension filtering for substantiality
- **Description**: Plan defers comment-filtering and file-path filtering for the substantiality 100-LOC proxy. Worth a follow-up to filter `*.md`, vendored `*.json`, generated assets, etc. Affected files: `skills/review-and-fix/scripts/review-and-fix.sh` (substantiality logic), `scripts/run-step5-review.md` (document threshold and filters).
- **Reviewer**: Cursor-Edge, Cursor-Requirements, Codex-Arch (all flagged as deferred)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: SECURITY.md re-evaluation for bash-driven substantiality
- **Description**: If bash-driven substantiality changes trust boundaries (e.g., the gate becomes shell-injectable via finding text in some future extension), `SECURITY.md` may need an update. Plan does not mention SECURITY.md touch. Affected file: `SECURITY.md`.
- **Reviewer**: Cursor-Requirements


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_5: `compose-review-findings.sh --issue 0` documented behavior
- **Description**: If the team decides to keep `--issue 0` as the contract (per FINDING_13 EXONERATE path), document in `scripts/larch-log-batches.md` how `review-findings-full` records join back to issues via RUN_ID. Affected file: `scripts/larch-log-batches.md`.
- **Reviewer**: Cursor-Arch (item 6 context)

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

