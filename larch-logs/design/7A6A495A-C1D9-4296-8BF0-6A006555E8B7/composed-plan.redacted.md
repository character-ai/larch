## Plan

### Files to modify

- **`skills/design/scripts/decompose-file-issues.sh`** — replace the single-match `re.search` block at lines 97–104 of the embedded Python in the `prepare` action with a segment-based parse:
  - Anchor on `blocked-by\b`, split the remainder on `,` or `\s+and\b`.
  - Require each non-empty segment to match exactly `^Piece\s+(\d+)$` (case-insensitive). Any non-matching segment → `DECOMPOSE_PARTITION_STATUS=bad-dependency-ref` exit 2.
  - If the anchor matched but the segment list yields zero blockers (e.g., the deferred plural shape `Pieces 1, 2, 3`), abort with the same `bad-dependency-ref` exit 2 — silent zero-edges from an intended `blocked-by` line is exactly the silent-corruption class the original bug exposed.
  - Dedupe blockers within a single dependency line via a `seen` set.
  - Preserve the existing strict-reference rule across **all** blockers: any unknown blocker number still aborts with `bad-dependency-ref` exit 2.
  - Preserve the existing `edges.append((blocker_index, current_index))` shape so downstream cycle detection / `indeg` accounting / TSV serialization are untouched.

- **`skills/design/scripts/decompose-prompts/_common-tail.txt`** (line 27) — change the dependency grammar bullet from `- Dependencies: none | blocked-by Piece N` to `- Dependencies: none | blocked-by Piece N[, Piece M ...]` so producer prompts are end-to-end consistent with the parser.

- **`skills/design/scripts/decompose-aggregator.sh`** (line 95) — same one-line grammar update as `_common-tail.txt` for parity with the aggregator-side schema.

- **`skills/design/scripts/test-decompose-file-issues.sh`** — add four new test sections immediately after the `=== prepare cycle ===` section, following the existing harness style (`echo "=== <name> ==="`, `D="$TMP/p<N>"`, here-doc partition fixture, `"$DFI" prepare`, assertions via `grep -Fq` / `wc -l`):
  1. **`=== prepare multi-blocker comma list ===`** (`p2c`) — 5-piece partition with `blocked-by Piece 1, Piece 2, Piece 3, Piece 4`; assert 4 edges (`1\t5`, `2\t5`, `3\t5`, `4\t5`) plus `wc -l == 4`.
  2. **`=== prepare bad-ref inside multi list ===`** (`p2d`) — `blocked-by Piece 1, Piece 99`; capture exit via `set +e; _rc2d=$?; set -e`; assert `_rc2d -eq 2`, `DECOMPOSE_PARTITION_STATUS=bad-dependency-ref`, and absence of `partition-input.txt` / `partition-deps.tsv`.
  3. **`=== prepare and-separator multi-blocker ===`** (`p2e`) — 3-piece partition with `blocked-by Piece 1 and Piece 2`; assert 2 edges plus `wc -l == 2`.
  4. **`=== prepare duplicate-blocker idempotency ===`** (`p2f`) — `blocked-by Piece 1, Piece 1`; assert 1 deduped edge plus `wc -l == 1`.

- **`skills/design/scripts/decompose-file-issues.md`** — insert one `**Edge-extraction rules**` paragraph immediately after the existing `**Purpose**` paragraph and before `**Primary caller**`, documenting: one edge per comma- or `and`-separated `Piece N` token; duplicate blocker numbers deduped; any non-`Piece N` segment / unknown blocker / empty parse aborts with `DECOMPOSE_PARTITION_STATUS=bad-dependency-ref` exit 2 and emits no batch artifacts.

### Approach summary

Two-step parse: anchor on `blocked-by`, split on comma/`and`, require strict `^Piece\s+(\d+)$` per segment. Failure modes converge on the same `bad-dependency-ref` exit 2 contract — unknown blocker number, non-`Piece N` segment (prose, plural shape), or empty blocker list after parsing. Producer prompts updated in parallel so the contract is end-to-end consistent. The plural-shape `Pieces 1, 2, 3` remains explicitly deferred (Round 1 Decision 5; if observed in the wild, a follow-on issue can broaden the regex AND update producer schemas).

### Failure modes covered by new fixtures

| Regression class | Caught by |
|---|---|
| Silent under-counting (original bug) | `p2c` — `wc -l == 4` plus per-edge `grep -Fq` |
| Dedupe broken (one edge per duplicate) | `p2f` — `wc -l == 1` for `Piece 1, Piece 1` |
| `and` separator broken | `p2e` — both `1\t3` and `2\t3` present |
| Strict-reference weakened (status printed, exit 0) | `p2d` — explicit `_rc2d -eq 2` |

## Acceptance

- `skills/design/scripts/decompose-file-issues.sh` parses multi-blocker comma/and-separated lists; the existing `(bi, i)` edge-append shape is preserved (one edge per blocker, post-dedupe).
- Duplicate blocker entries in the same line (e.g., `blocked-by Piece 1, Piece 1`) are idempotent (single edge, no error).
- Bad-blocker references (`blocked-by Piece 99` when no Piece 99 exists) still fail closed with `DECOMPOSE_PARTITION_STATUS=bad-dependency-ref` exit 2 — across ALL blockers in the list, not just the first.
- Non-`Piece N` segments (incidental prose, the deferred plural shape `Pieces 1, 2, 3`) fail closed with the same `bad-dependency-ref` exit 2 — no silent zero-edges from an intended `blocked-by` line.
- Producer prompt schemas in `decompose-prompts/_common-tail.txt:27` and `decompose-aggregator.sh:95` advertise the multi-blocker grammar `none | blocked-by Piece N[, Piece M ...]` so the contract is end-to-end consistent.
- `skills/design/scripts/test-decompose-file-issues.sh` gains exactly four new test sections (`p2c`, `p2d`, `p2e`, `p2f`) per the Plan above. The `p2d` fixture explicitly captures the prepare exit code (`set +e; _rc=$?; set -e; [[ "$_rc" -eq 2 ]]`) so a regression that prints the status string but exits 0 still fails the harness.
- `skills/design/scripts/decompose-file-issues.md` documents the multi-blocker contract under a new `**Edge-extraction rules**` paragraph between `**Purpose**` and `**Primary caller**`.
- `make test-decompose-file-issues` and `make lint` both pass.

diff_lines: 145
