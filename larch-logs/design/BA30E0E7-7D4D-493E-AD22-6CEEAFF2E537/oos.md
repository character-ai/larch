### FINDING_3: Bump decision still sourced from diff-based `classify_bump`, not resolved titles
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan keeps aggregate bump classification on `version_bump.classify_bump` even though the feature requires the version bump decision to use resolved companion issue titles or PR titles. After the PR lands, release notes would use issue titles, but `BUMP_TYPE` and `NEW_VERSION` would still come from the existing git-diff-based public-surface classifier, so `/release` would not have moved the bump decision to the requested title source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise release_prepare so the aggregate bump calculation consumes the same resolved title source written to pr-list.tsv, or update the classifier path accordingly; do not leave the existing diff-based classify_bump call as the release bump source.

Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

