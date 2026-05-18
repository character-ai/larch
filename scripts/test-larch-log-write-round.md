# test-larch-log-write-round.sh contract

Regression harness for `scripts/larch-log.sh write-round`.

The test builds a disposable review round directory, writes representative
reviewer outputs and sidecars, and asserts that:

- registered artifacts land under `larch-logs/implement/<run-id>/round-<N>/`
- unregistered files such as session env or arbitrary notes stay out
- `.meta` sidecars drop `CMD_JSON=...`
- Cursor JSON sidecars drop top-level `.result`
- the normal tmpdir and secrets redaction still runs
- repeated writes report `UNCHANGED=true`

Run with:

```bash
make test-larch-log-write-round
```

Update alongside `scripts/larch-log.sh`, `scripts/lib-redact.sh`, and
`scripts/larch-log.md` when the `write-round` artifact contract changes.
