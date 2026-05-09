# test-list-issues.sh contract

**Purpose**: regression coverage for `list-issues.sh` issue snapshot filtering. The harness pins the `DEDUP_SKIP_PREFIX_FILTER` symbol and both `JQ_FILTER` assignments: the open-only branch used when `--closed-window-days 0`, and the closed-window branch used when `--closed-window-days` is greater than zero.

**Coverage**:

1. Open-only mode emits only open, non-PR issues whose titles do not match the dedup skip prefixes.
2. Closed-window mode emits the same open rows plus closed issues whose `closed_at[:10] >= $cutoff`; the boundary date is included and the prior date is excluded.
3. Title TSV shaping replaces tabs, newlines, and carriage returns via the production chain `gsub("\t"; " ") | gsub("\n"; " ") | gsub("\r"; " ")`.
4. `select(.pull_request == null)` excludes pull requests in both jq branches.
5. Prefix filtering is case-insensitive and trims leading whitespace with `sub("^[[:space:]]+"; "")`.

**Pinned production filter**:

```jq
select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)
```

The pinned skip prefixes are <code>research </code>, <code>[research] </code>, <code>investigate </code>, <code>[investigate] </code>, and any `[* report]` pattern followed by a space (e.g. `[research report]`, `[analysis report]`, `[perf report]`) — each requires an ASCII space immediately following the closing bracket (closes #1063). The last clause uses a jq `test` regex rather than a fixed `startswith` so that any bracketed title ending in "report" is excluded without listing each variant. Substring-prefix collisions like `Researcher settings` (no space after `research`) and the exact token `[research]` (no space after `]`) are intentionally NOT archival and pass through Phase 1 dedup. `Research Report no brackets` is still filtered because the lowercased title starts with <code>research </code> (research + space).

**Fixture shape**: `fixtures/list-issues/page1.json` and `fixtures/list-issues/page2.json` are JSON arrays matching the GitHub REST `repos/.../issues` response shape. The harness concatenates them with no separator to exercise jq's multi-document input behavior used with `gh api --paginate`.

**Mock shape**:

- Fake `gh` lives in a per-test `fake-bin` directory prepended to `PATH`. It supports `gh repo view --json nameWithOwner --jq .nameWithOwner` and `gh api --paginate repos/owner/repo/issues?state=all&per_page=100`; every `gh api` fixture read appends to `$MARKER_GH`.
- Fake `python3` intercepts `python3 -c <body>` only when `<body>` contains `datetime.timedelta(days=`. It emits `$MOCK_CUTOFF`, appends to `$MARKER_PYTHON3`, and fails closed for any other `-c` body. Non-`-c` invocations exec `$REAL_PYTHON3`, captured before fake-bin is prepended to `PATH`.
- The fake env contract is `FIXTURE_RAW`, `MOCK_CUTOFF`, `MARKER_GH`, `MARKER_PYTHON3`, and `REAL_PYTHON3`; the fake binaries fail loudly if any required value is unset.

**Fail-open contract**: `list-issues.sh` always exits 0. The meaningful success gate is stdout's leading `LIST_STATUS=ok` line; future harness edits should not assert non-zero rc for helper failure paths.

**Edit-in-sync rules**:

- Any change to `DEDUP_SKIP_PREFIX_FILTER` in `list-issues.sh` must update the fixture matrix and expected TSV rows here.
- Any change to either `JQ_FILTER` assignment in `list-issues.sh` must update this harness if emitted fields, state filtering, PR filtering, closed-window filtering, or TSV shaping changes.
- Any change to the prefix skip list must update production and the fixture rows together.
- Any change to the `gsub` set must update the production line, the escaped-control-character fixture row, and the expected TSV value.

**Execution**: `bash skills/issue/scripts/test-list-issues.sh` exits 0 on success and 1 on any failure. Wired into `make lint` via `test-list-issues`, which is included in the `test-harnesses` aggregate through `test-harnesses-2`.

**Channel discipline**: stdout is the assertion log; helper-under-test stdout/stderr is captured per invocation and printed only on assertion failure.
