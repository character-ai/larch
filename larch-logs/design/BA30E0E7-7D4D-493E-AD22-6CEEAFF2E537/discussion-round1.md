## Decision 1: Bump-type classifier scope
- **Question**: Does "no PR diffs" for version-bump-decision info also mean reworking `classify_bump`'s structural skill/agent file diffing to use titles, or only Step 3's release-notes composition?
- **Resolution**: Leave `classify_bump` (MAJOR/MINOR/PATCH structural file-diff classifier) untouched. Only Step 3's release-notes composition switches from reading PR diffs to companion-issue titles.
- **Source**: assistant recommendation (no operator response within 60s to AskUserQuestion)

## Decision 2: Companion-issue title priority
- **Question**: Should companion-issue title always replace the PR title in notes, or only replace generic "Fixes #N: Implement issue #N" boilerplate titles?
- **Resolution**: Always prefer the companion issue's title when a companion issue is resolvable; PR title is used only as a fallback (no companion issue found, or issue fetch fails).
- **Source**: assistant recommendation (no operator response within 60s to AskUserQuestion)

## Decision 3: --approve and the empty-window safety net
- **Question**: Should `--approve`/`-a` override the existing default-to-Cancel behavior when PR_COUNT=0?
- **Resolution**: Keep the empty-window safety net. `--approve` skips the AskUserQuestion prompt only when PR_COUNT>0; with zero merged PRs, /release still stops rather than auto-cutting a no-op release.
- **Source**: assistant recommendation (no operator response within 60s to AskUserQuestion)
