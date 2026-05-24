# CI-fix failure patterns (larch-specific)

Use this when CI logs mention topology documentation or `skills/shared/topology.tsv`.

## `topology.tsv` rows

- **`composition` field** must match `[A-Za-z0-9 ./+-]` only. Rewrite prose to drop punctuation such as `;`, `*`, `(`, `)`, commas, underscores, etc., while keeping meaning.
- **`value` field** must appear verbatim in the cited runtime authority file for that row (the generator checks anchors). If the value is new, add it to the authority doc first, then keep `topology.tsv` aligned.

## Regenerate `docs/topology.md`

After editing `skills/shared/topology.tsv` (or related anchors), run:

```bash
bash scripts/generate-topology-docs.sh
```

Use `bash scripts/generate-topology-docs.sh --check` to validate without writing when debugging.
