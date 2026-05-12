# test-tracking-issue-write.sh contract

Regression harness for `scripts/tracking-issue-write.sh`. It uses a stub `gh`
binary and covers create, append, lifecycle-marker validation, rename title
updates, redaction, and rejection of removed anchor subcommands.
