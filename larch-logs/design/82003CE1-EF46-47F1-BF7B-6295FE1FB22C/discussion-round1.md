## Decision 1: Nested-retry callsites
- **Question**: Some listed gap callsites (rebase-push.sh:274, create-pr.sh:129) already have their own retry mechanism. Wrap them anyway?
- **Resolution**: Wrap every listed gap callsite verbatim, including inner pushes inside existing retry loops. Nested retries (up to 9 total) are acceptable for uniform transient handling.
- **Source**: user

## Decision 2: Tier 1 scope (git push / gh pr verbs)
- **Question**: Which Tier 1 callsites are in scope?
- **Resolution**: Wrap bare `git push` at design-log-publish.sh:610, rebase-push.sh:274, create-pr.sh:129+201, setup-forked-open-source-repo.sh:411; bare `gh pr create` at design-log-publish.sh:628, create-pr.sh:230; bare `gh pr merge` at design-log-publish.sh:657, merge-pr.sh:333/348/359; bare `gh pr edit` at gh-pr-body-update.sh:77, ship-pr.sh:1622/2761.
- **Source**: codebase (issue body audit)

## Decision 3: Tier 2 scope (gh issue verbs and gh api writes)
- **Question**: Which Tier 2 callsites are in scope?
- **Resolution**: Wrap every `gh issue create/edit/comment/close` and every `gh api -X PATCH/DELETE` write listed in the issue audit (tracking-issue-write.sh, clarify-label.sh, clarify-comment-post.sh, named-block-write.sh, tracking-issue-summary.sh, decompose-file-issues.sh, cleanup-failed-issue.sh, create-one.sh, apply-combination.sh, audit-close-priors.sh, upsert-diagrams-comment.sh, tracking-issue-summary.sh).
- **Source**: codebase (issue body audit)

## Decision 4: Tier 3 scope (git fetch / pull / ls-remote / clone / submodule)
- **Question**: Which Tier 3 callsites are in scope?
- **Resolution**: Wrap only the hard-fail callsites listed in the issue: merge-pr.sh:281/318, preflight.sh:72, create-branch.sh:109, local-cleanup.sh:74+108, check-remote-branch.sh:56, rebase-push.sh:155, setup-forked-open-source-repo.sh:125/403/497, audit-preflight.sh:54. Leave the 14 `git fetch ... --quiet 2>/dev/null || true` tolerant callsites alone.
- **Source**: codebase (issue body audit)

## Decision 5: Out-of-scope (rare local-only verbs)
- **Question**: Are there callsites that should be explicitly excluded?
- **Resolution**: `git remote add` / `git remote set-url` are rare and local-only after the initial add — leave them alone.
- **Source**: codebase (issue body audit)

## Decision 6: design-log-publish.sh remote cleanup
- **Question**: What must happen when all retries of `gh pr create` are exhausted but the push succeeded?
- **Resolution**: Unconditionally attempt `git push origin --delete $WT_BRANCH` (best-effort) on the gh-pr-create-failed branch so a caller-driven retry of the whole script can re-push cleanly. Replaces today's "remote branch may need manual cleanup" log-only behavior at design-log-publish.sh:648.
- **Source**: codebase (issue body acceptance)
