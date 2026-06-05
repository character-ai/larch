# test-larch-log-write-round.sh contract

Regression harness for `scripts/larch-log.sh write-round`.

The test builds a disposable review round directory, writes representative
reviewer outputs and sidecars, and asserts that:

- registered artifacts land under `larch-logs/implement/<run-id>/round-<N>/`
- unregistered files such as session env or arbitrary notes stay out
- `.meta` sidecars drop `CMD_JSON=...`
- unphased static `codex-specialist-*-output.txt` raw transcripts and sidecars
  are excluded, while phased static Codex fallback outputs are included
- dynamic Codex twin raw outputs (`dyn-*-codex-output.txt` and
  `dyn-*-codex-output-phase*.txt`) are included with their `.meta`, `.json`, and
  `.cap-hit` sidecars
- included `*-output*.json` sidecars drop top-level `.result`
- the normal tmpdir and secrets redaction still runs
- excluded prompt/sidecar/sentinel/dirty-tree artifacts never land in
  `round-<N>/`
- dynamic Codex `.prompt`, dynamic-shaped `*-vote-prompt.txt`, and unphased
  `.events.jsonl` sidecars stay excluded; phased Dynamic Codex does not produce
  `.events.jsonl` in real runs
- repeated writes report `UNCHANGED=true`

Run with:

```bash
make test-larch-log-write-round
```

Update alongside `scripts/larch-log.sh`, `scripts/lib-redact.sh`, and
`scripts/larch-log.md` when the `write-round` artifact contract changes.
