# test-design-pause-resume.sh contract

Offline regression harness for `/design` pause/resume helpers. It stubs `gh`,
`git fetch`, `git archive`, and `design-log-publish.sh` so the round-trip runs
without network access.

Primary contracts live in:

- `scripts/named-block-write.md`
- `scripts/design-pause-save.md`
- `scripts/design-pause-load.md`
