# skills/implement/scripts/oos-issue-cap.sh — contract

`oos-issue-cap.sh` is a deterministic batch-shaping helper for `/implement`
Step 9a.1 accepted-OOS issue filing. Its primary caller is the OOS pipeline
between the combine pass that writes `$IMPLEMENT_TMPDIR/oos-combined.md` and
the file-conflict pre-pass that consumes that same path.

## Invariants

- **Parser delegation**. The helper invokes
  `skills/issue/scripts/parse-input.sh` once against the exact merged OOS batch
  file that `/issue` would receive. It uses `ITEMS_TOTAL`,
  `ITEM_<i>_TITLE`, `ITEM_<i>_BODY_FILE`, and `ITEM_<i>_MALFORMED=true` as the
  source of item order and body truth; it does not implement a second OOS
  parser.
- **Input shape**. The helper accepts only OOS-shaped batches whose items begin
  with `### OOS_<digits>:`. Generic fallback input is rejected with exit 1.
- **Parser/heading parity**. `ITEMS_TOTAL` from `parse-input.sh` must equal the
  raw `^### OOS_<digits>:` heading count. A mismatch exits 1 because
  `parse-input.sh`'s pending-heading split path can otherwise make the parser
  and raw markdown disagree about item boundaries.
- **In-place default**. `--input-file FILE` without `--output` rewrites `FILE`
  in place via `FILE.tmp` plus `mv`. `--output PATH` writes a separate stable
  output path and opts in to cleanup of that stable path on failure. Callers
  should not pass aliasing input/output paths; in-place mode is the safe
  default.
- **Atomic write**. Successful runs write `<out>.tmp` and then `mv` into place.
  Fatal runs remove the tmp file and any intermediate renumber temp. The
  renumber temp lives under the helper work directory, not beside the stable
  output path.
- **Pass-through**. When `ITEMS_TOTAL <= OOS_ISSUES_PER_RUN_CAP`, output is
  byte-equivalent to input.
- **Compaction**. When `ITEMS_TOTAL > OOS_ISSUES_PER_RUN_CAP`, the helper keeps
  the first `(cap - 1)` blocks verbatim, appends one synthetic
  `### OOS_<cap>:` aggregate, and renumbers headings to `OOS_1..OOS_<cap>`.
  `OOS_ISSUES_PER_RUN_CAP=1` keeps zero original entries and rolls the whole
  batch into a single `OOS_1` aggregate.
- **Env validation**. `OOS_ISSUES_PER_RUN_CAP` defaults to `5` and
  `OOS_ISSUE_CAP_EXCERPT_MAX` defaults to `200`. Both are validated as positive
  integers with explicit empty strings treated as invalid. Invalid values exit
  2.
- **Excerpt truncation**. Each rolled-up entry excerpt is bounded by
  `OOS_ISSUE_CAP_EXCERPT_MAX` UTF-8 characters via
  `oos-issue-cap-excerpt.py`; `python3` is a hard dependency. Whitespace runs
  collapse to one space and truncated excerpts receive a trailing `…`.
- **File-reference preservation**. Each aggregate bullet appends a
  `[Files: <paths>]` suffix when the full rolled-up body contains repo-relative
  file or file:line references matched by `scripts/file-line-regex-lib.sh`.
  The file list is extracted from the full body, not the truncated excerpt, so
  the downstream file-conflict pre-pass can still serialize aggregate entries
  with path hints.
- **Markdown normalization**. Titles strip control characters, leading
  markdown heading/bullet markers, backticks, and bold markers; excerpts strip
  control characters and collapse whitespace so aggregate bullets remain
  single-line markdown.
- **Malformed items**. A malformed item with a non-empty `BODY_FILE` still
  contributes a bounded diagnostic excerpt. The `(malformed item — body
  unavailable)` placeholder is used only when `BODY_FILE` is missing or empty.
- **Fail-closed caller contract**. On non-zero exit, callers MUST NOT silently
  proceed to file the OOS batch. `/implement` skips step 3.5 and step 4 for the
  OOS batch and surfaces:
  `**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**`.
  This differs intentionally from `oos-file-conflict-deps.sh`, whose TSV edges
  are best-effort hints; the issue cap is a hard policy guard against issue
  spam.
- **Aggregate size**. At the defaults, aggregate bodies stay small. Operators
  tuning `cap * OOS_ISSUE_CAP_EXCERPT_MAX` substantially upward should confirm
  the resulting `$IMPLEMENT_TMPDIR/oos-combined.md` body stays under GitHub's
  issue body limit before `/issue` posts.

## Exit-Code Contract

- `0`: success.
- `1`: usage error, missing input, parser failure, parser/heading parity
  mismatch, non-OOS input, or other I/O failure.
- `2`: invalid `OOS_ISSUES_PER_RUN_CAP` or `OOS_ISSUE_CAP_EXCERPT_MAX`.

## Makefile and Lint Wiring

`make test-oos-issue-cap` runs
`skills/implement/scripts/test-oos-issue-cap.sh`. The target is listed in
`.PHONY` and exactly one `test-harnesses-N` shard. `agent-lint.toml` excludes
the harness script, its sibling `.md`, and the Python excerpt helper under the
existing Makefile-only test-harness pattern.

## Edit-in-Sync

When behavior changes, update these files together:

- `skills/implement/SKILL.md` Step 9a.1 narrative and file-conflict subsection.
- `skills/implement/SKILL.md` Step 9a.1 procedure.
- `docs/configuration-and-permissions.md` environment variable entries.
- `skills/issue/scripts/parse-input.sh` if parser stdout changes.
- `scripts/file-line-regex-lib.sh` if path grammar changes.
- `scripts/test-implement-structure.sh` assertion 9g.
- `skills/implement/scripts/test-oos-issue-cap.sh` fixtures.
