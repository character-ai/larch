# scripts/git-amend-add.sh — contract

`scripts/git-amend-add.sh` wraps `git add <files>` followed by `git commit --amend --no-edit`. Folds the staged delta into the preceding commit without prompting for a message edit. It does not flush `/implement` larch logs; log commits are owned by the explicit pre-bump, external-implementer, and pre-push refresh points. It currently has no primary callers and is retained for future amend use cases; Step 8a CHANGELOG updates now use `scripts/commit-changelog.sh` so the bump commit remains bump-file-only.
