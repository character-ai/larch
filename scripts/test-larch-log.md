# test-larch-log.sh contract

Regression harness for `scripts/larch-log.sh`. It runs with `LARCH_LOG_ROOT`
pointing at a temporary directory so it does not leave runtime artifacts in the
repository.

Coverage includes manifest creation, replace-mode redaction, idempotent retry,
append-mode newline handling, json-lines rejection for raw markdown records,
`exists`, mutable manifest updates, the `commit` staging path (`LARCH_LOG_ROOT`
unset, `--log-root` set) that copies logs from an explicit temp staging dir into
the repo before committing, committed breadcrumb publication with tmpdir-path
and PEM redaction, fail-closed rejection of unsafe breadcrumb source entries,
the `larch-log-flush.sh` post-merge sentinel no-op
path, commit refusal on the default branch/main, and `write-round` coverage for
scout artifacts (`scout-round*-status.env`, `scout-round*-manifest.json`) and
dynamic-archetype files (`reviewer-dyn-*.md`, `dyn-*-prompt.md` flattened from
`dynamic-archetypes/` to the round root), inclusion of `cursor-vote-output-first-pass.txt`
when present (parse-retry observability sidecar), plus regression assertions that denied
files (`cursor-specialist-*-output.txt`, `*-vote-prompt.txt`) remain excluded.
