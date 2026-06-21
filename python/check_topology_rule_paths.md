# python/check_topology_rule_paths.py contract

`python3 python/cli.py lint topology-rule-paths` verifies that every distinct runtime authority in `skills/shared/topology.tsv` is present in `.claude/rules/topology-generation.md` frontmatter `paths:`.

## Caller surface

Primary callers are the `agent-sync` job, the local `check-topology-rule-paths` pre-commit hook, `make test-check-topology-rule-paths`, and manual local runs.

`--root PATH` overrides the checkout root. The default is the repository parent of this module. Harness fixtures pass `--root "$dir"` so TSV and rule files are resolved inside isolated temp trees. Production callers omit `--root`.

## Frontmatter parser

The module is stdlib-only. It intentionally implements only the `paths:` shapes used by larch rules.

Supported forms:

```yaml
paths:
  - "skills/shared/topology.tsv"
  - skills/shared/topology.tsv
```

```yaml
paths: ["skills/shared/topology.tsv", "docs/topology.md"]
```

Inline flow lists split on commas outside double quotes. Every flow-list item must be a double-quoted string. Block-list entries may be double-quoted strings or bare path tokens.

Rejected forms keep the legacy diagnostics:

- Missing `paths:` fails with `frontmatter must define paths`.
- Scalar `paths: skills/foo.md` fails with `paths must be a list`.
- Flow-list items such as `3`, `null`, or `true` fail on the first bad item with `must be a string`.
- CRLF in the rule frontmatter fails before parsing.
- Missing frontmatter fails with `no YAML frontmatter found`.

## Edit-in-sync

Update this contract with parser or CLI changes. Keep `scripts/test-check-topology-rule-paths.sh` as the black-box regression authority.
