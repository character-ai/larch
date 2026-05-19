### FINDING_2: [OUT_OF_SCOPE] code-quality: larch-logs/implement/*/code-review-tally.json (committed snapshots)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Snapshotted tally bodies may show older column/token labels than post-rename scripts. Readers of historical logs could see mixed vocabulary vs current `tally-code-votes.sh` output. Out of scope: intentional frozen run logs; update only if regenerating snapshots.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] risk-integration: Branch diff vs #2373 Phase 1
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Commits/diffs bundle #2381 voting-doc/test changes, version/changelog touches, and larch-logs flush with the scout allow-list work. Reviewers may treat PR as single-issue while rebasing/splitting/conflict surface spans unrelated areas. Split PRs or narrow PR description to list all issue IDs and change classes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] risk-integration: Branch vs main (git log merge-base..HEAD)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Three-commit stack: larch-logs flush, scout raw, NEUTRAL to JUDGE_ERROR rename. Review scope blur when triaging regressions to a single issue. Partition review by commit or by issue when bisecting.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] risk-integration: CHANGELOG.md:14-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] 29.8.16 section only records `Closed: #2376` without per-feature bullets for stacked commits. Readers auditing what 29.8.16 shipped may not tie the tag to scout `.raw` logging or voter vocabulary unless #2376 is the umbrella issue. If desired, expand changelog bullets or cross-link issues; not a functional bug in scout or larch-log.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh (check_voter_parse_rate awk)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Parallel awk vote logic remains duplicated vs `lib-vote-tally.sh` `vote_for_id`. Future threshold edits could drift between copies. Out of scope: pre-existing; optional follow-up refactor to source shared helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

