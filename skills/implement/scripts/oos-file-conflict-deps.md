# skills/implement/scripts/oos-file-conflict-deps.sh — contract

`oos-file-conflict-deps.sh` emits deterministic intra-batch dependency TSV
rows for `/implement` Step 9a.1 accepted-OOS issue filing. Its primary caller
is the Step 9a.1 pre-pass immediately before `/issue --input-file`.

## Invariants

- **Parser delegation**. The helper invokes `skills/issue/scripts/parse-input.sh`
  once against the exact merged OOS batch file that `/issue` receives. It uses
  `ITEMS_TOTAL`, `ITEM_<i>_BODY_FILE`, and `ITEM_<i>_MALFORMED=true` from that
  stdout as the sole source of item order and body truth; it does not implement
  a second OOS parser.
- **Path extraction delegation**. File mentions are extracted with
  `scripts/file-line-regex-lib.sh`. The helper normalizes `./foo` to `foo`,
  splits comma- and semicolon-separated path lists onto their own lines so
  `grep -Eoh`'s consumed left/right boundaries do not swallow the neighbor's
  anchor, rejects absolute paths and `..` traversal, and otherwise stays inside
  the shared path grammar.
- **Numeric-only output**. The TSV contains only `<blocker>\t<blocked>` rows,
  where each value is a 1-based batch item index. Reviewer prose never crosses
  into the dependency artifact.
- **Tie-break**. Lower 1-based batch index blocks higher index.
- **Conflict rule**. Two items sharing a path are serialized unless both sides
  expose explicit valid ranges for that path and every pairing is disjoint.
  Ranges are inclusive: `[a,b]` and `[c,d]` overlap when `max(a,c) <= min(b,d)`.
  Invalid ranges and range-less mentions are treated as whole-file mentions.
- **Malformed items**. Items marked `ITEM_<i>_MALFORMED=true` preserve their
  index slot but contribute no paths and therefore no edges.
- **Edge shape**. Same-file conflict clusters emit all-pairs rows. If a cluster
  would exceed `CLUSTER_CAP=200` rows, it emits a stable lower-index chain
  instead and prints one basename-only warning. If total output would still
  exceed `/issue`'s 500-row TSV cap, the helper exits non-zero without
  publishing the stable output path. The regression harness may lower these
  caps with `OOS_FILE_CONFLICT_CLUSTER_CAP` and
  `OOS_FILE_CONFLICT_GLOBAL_CAP`; production callers rely on the defaults.
- **Atomic write**. Successful runs write `<out>.tmp` and then `mv` into place.
  Fatal runs remove the tmp file and the stable output path so no observable
  TSV survives the failure.
- **Exit-code contract**. `0` on success (TSV written, may be empty if no
  conflicts found); `1` on missing required arguments / unknown flags / parser
  failure / global-cap exceeded; `2` on invalid env caps
  (`OOS_FILE_CONFLICT_CLUSTER_CAP`, `OOS_FILE_CONFLICT_GLOBAL_CAP` non-positive
  or non-numeric). Callers treat any non-zero exit as a no-TSV outcome and
  proceed without `--intra-batch-deps-file`.

## /issue merge and SCC behavior

Caller TSV edges are merged with `/issue` Phase 2 LLM output before validation;
neither source has precedence. `skills/issue/SKILL.md` documents the SCC pass:
"For any SCC with more than one node, drop the lowest-priority outbound edge to
break the cycle: among the SCC's nodes, pick the one with the lowest input
index, and within its `BLOCKED_BY` list pick the lexically-earliest entry;
remove that single entry, then re-run SCC detection." It also documents union
semantics: "Caller-supplied intra-batch deps merge" appends TSV rows to the LLM
lists before the shared validation pipeline.

Known degraded-path limitation: `/issue` Step-5-skip paths can silently drop
`--intra-batch-deps-file` rows when `LIST_STATUS=failed`, allocator failure, or
empty-CANDIDATES + `N<2` prevents Step 5 from running. The fix is deferred to a
follow-up issue; Step 9a.1 documents the limitation where the helper is invoked.

## Makefile and lint wiring

`make test-oos-file-conflict-deps` runs
`skills/implement/scripts/test-oos-file-conflict-deps.sh`. The target is listed
in `.PHONY` and exactly one `test-harnesses-N` shard. `agent-lint.toml`
excludes the harness script and this harness' sibling `.md` under the existing
Makefile-only test-harness pattern.

## Edit-in-sync

When behavior changes, update these files together:

- `skills/implement/SKILL.md` Step 9a.1 narrative.
- `skills/implement/references/anchor-template-oos-pipeline.md` Step 9a.1
  procedure.
- `scripts/file-line-regex-lib.sh` and its contract when the path grammar
  changes.
- `skills/issue/scripts/parse-input.sh` and its contract when parser stdout
  changes.
- `skills/implement/scripts/test-oos-file-conflict-deps.sh` fixtures.
