### FINDING_9: code-quality: CHANGELOG.md:.agnix.toml:scripts/github-remote-repo.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bundled agnix AS-014 disable, 29.3.11 changelog slice, and GitHub URL regex edits are outside the stated P+Q feature and the implementation plan’s file list. Reviewers must untangle unrelated policy/lint churn from run-log and hook behavior; bisecting a regression on hook or compose logic also blames unrelated commits. Split unrelated hygiene into its own PR or document an explicit dependency in the same issue if it cannot be decoupled.
- **Suggested revision**: Address the concern above.



