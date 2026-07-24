# Run-log layout migration: 2026-07-24

This is the operational record for `character-ai/larch#7966`. The migration
used larch `v56.0.0` and operator tooling at commit
`909518cb40d90e9be2fdbcf0cd2ed6ad484346b1`.

## Final mapping

| Client | Source retained | Tool-first target |
|---|---|---|
| `larch` | `s3://zhupanov/larch/run-logs/` | `s3://zhupanov/larch/larch/run-logs/` |
| `agent-lint` | `s3://zhupanov/agent-lint/run-logs/` | `s3://zhupanov/larch/agent-lint/run-logs/` |

The repeated `larch/larch` is intentional. The first segment is the tool name.
The second is the Git-origin-derived client repository.

## Frozen plan and report

The final plan was created at `2026-07-24T06:26:48.937602Z`.

```text
plan_sha256=77fc8d719b4b3d2b55cb5bdddd5b1b5b897daa80cfa0aa9efee5e9ac1b819c5f
planned_archives=2672
```

Apply completed at `2026-07-24T07:27:00.548984Z`. Independent verification
completed at `2026-07-24T07:59:39.095797Z`.

```text
report_uri=s3://zhupanov/larch/larch/migration-reports/20260724T072700Z-run-log-layout-v1.json
report_sha256=33906c3093421d628b4d6d51727e5b43fbd064c2b057fe9f7bf2a65a5cf04fdc
verified_archives=2672
target_manifestless_archives=0
source_objects_retained=true
target_writes_create_only=true
```

| Client or kind | Archives | Source bytes | Target bytes |
|---|---:|---:|---:|
| `larch` | 2,667 | 90,728,193 | 100,127,278 |
| `agent-lint` | 5 | 5,024 | 5,024 |
| Legacy larch | 2,628 | 90,687,425 | 100,086,510 |
| Modern, both clients | 44 | 45,792 | 45,792 |

Every modern archive was copied byte for byte. Each legacy larch archive was
validated against the pinned inventory, rebuilt with the current canonical
root manifest, and checked for source-member equivalence. Every downloaded
target passed the normal manifest-based materializer.

## Freeze drift and reconciliation

The first frozen plan covered 2,669 archives and had SHA-256
`083372c4597b0c7e19ca50abe091a18c114a29f2de80530e6024ed8b8b14901c`.
Three valid larch runs were published to the new target while its apply phase
was running. Strict verification rejected the extra keys before downloading
the corpus.

The operator validated those three modern archives, copied their exact bytes
create-only to the retained source, and generated the final plan above. The
first plan and apply report remain private operator evidence. No source or
target object was overwritten or deleted.

Before the first plan, the operator also reconciled one valid pending release
publication and one post-release target-only archive into the retained source.
Stale test-fixture pending state was not published or deleted.

## Reader and cache validation

Validation used isolated cache and state roots.

| Client | Cold listed/downloaded | Warm present/downloaded | Storage-origin ID |
|---|---:|---:|---|
| `larch` | 2,667 / 2,667 | 2,667 / 0 | `562c7e27af5a311f8cc0cc3b9a9cb730da86b31f3777891547296733c76f22f9` |
| `agent-lint` | 5 / 5 | 5 / 0 | `bb85112595c03e760c340d688d07e10f3b77d7f0ddb9ddb25b9438aa46858ebd` |

One disposable agent-lint cache run was corrupted. The next sync reported four
present runs, one download, and one repair, then restored the original file.
A differently named clone with the same Git origin selected the same
`agent-lint` corpus and storage-origin ID. A fixture with another base URI
selected a different storage-origin ID. Missing `tools-config.toml` and a file
without `[larch]` both failed before object-store access.

The returned larch corpus was consumed successfully by:

- fluff analysis;
- difficulty calibration;
- voter calibration;
- design and implement token reports with issue creation and plotting disabled.

The analyze-issues, rejected-analysis, audit-runs, difficulty, token-scan, and
voting integration suites passed 397 tests.

## Config cutover and writer smoke tests

The larch repository config contains only:

```toml
[larch]
storage_base_uri = "s3://zhupanov"
```

`zhupanov/agent-lint#660` was completed by
`zhupanov/agent-lint#661`, merged at `2026-07-24T08:59:35Z` as
`3ae566ba443abce27a0c41cef2248da68173f507`.
The agent-lint config has the same two lines and no other table.

After the immutable migration report was published, one `status` smoke run
from each client created:

```text
s3://zhupanov/larch/larch/run-logs/status/7966-larch-smoke.tar.gz
s3://zhupanov/larch/agent-lint/run-logs/status/7966-agent-lint-smoke.tar.gz
```

Neither smoke key exists under an old source prefix. Both were promoted to the
expected v2 storage-origin cache.

## Rollback and retention

The old run-log prefixes and the pinned migration inventory remain unchanged
for rollback. If a rollback becomes necessary, freeze writers, validate each
post-report target-only archive, copy it create-only to the corresponding old
root, verify exact bytes and normal materialization, then restore the previous
release and config.

Issue `character-ai/larch#7967` owns any later source deletion. It must honor
its retention period and account for the post-report smoke archives before
deleting an old prefix.
