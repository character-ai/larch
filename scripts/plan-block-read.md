# plan-block-read.sh contract

## Purpose

Reads the GitHub issue body for a `<!-- larch:plan:start -->` … `<!-- larch:plan:end -->` block and writes the inner markdown to `--output`. See `docs/issue-anchored-plan.md` for the wire format.

## Interface

```
plan-block-read.sh --issue <N> --output <path> [--repo OWNER/REPO]
```

## Output Contract

- Well-formed unique pair: `BLOCK_PRESENT=true`, `OUTPUT=<path>`, exit 0.
- No markers: `BLOCK_PRESENT=false`, empty output file, exit 0.
- Malformed: `MALFORMED=<token>` (`start-without-end`, `end-without-start`, `multiple-start`, `multiple-end`, `end-before-start`), exit 1. On every malformed exit the script truncates `--output` to an empty file first so callers cannot read stale inner markdown from a prior successful extraction.
- `gh` / JSON failure: `FAILED=true`, `ERROR=<single line>`, exit 2.

## Primary Callers

Future `/design` ↔ `/implement` integration (not yet wired).

## Test Harness

```
bash scripts/test-plan-block.sh
```

`make test-plan-block` runs this harness (shard `test-harnesses-15`).

## Edit-in-sync

When stdout keys or marker regex change, update `scripts/plan-block-write.sh`, `scripts/test-plan-block.sh`, and this file together.
