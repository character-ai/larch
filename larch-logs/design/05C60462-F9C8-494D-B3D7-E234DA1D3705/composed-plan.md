## Plan

## Approach

Implement the smallest shared predicate change and gate title filtering on whether `--search` was explicitly passed, not on whether the query string equals the default.

- Hoist the current `/analyze-bugs` title matcher into `python/larch/issue/title_match.py`.
- Keep semantics unchanged:
  - left-strip the title
  - strip known lifecycle prefixes case-insensitively in a loop
  - require `[BUG]` as the remaining case-insensitive prefix
- Import that predicate from both `analyze_bugs.py` and `learn_from_bugs.py`.
- Add `search_explicit: bool` to `PrepareRequest`. Set it in `prepare_main` from argv presence (`--search` or `--search=...`), not from query text.
- In `run_prepare`, filter only when `not request.search_explicit` (implicit default search path).
- Do not backfill. Fetch with the existing `--limit`, filter, and digest what remains.
- Add `ISSUES_FILTERED_NON_BUG` to the returned stats. Keep `ISSUES_SELECTED` as the post-filter count.
- Update the skill prompt to parse the new key.

## Files to modify/create

### NEW: python/larch/issue/title_match.py

Add the shared bug-title matcher.

- Define `BUG_PREFIX: Final = "[BUG]"`.
- Define `BUG_TITLE_LIFECYCLE_PREFIXES: Final` using `config.TRACKING_ISSUE_PREFIX_BY_STATE` entries for `done`, `designed`, `implementing`, and `stalled`.
- Define `bug_title_match(title: str) -> bool`.
- Move the exact normalization loop from `analyze_bugs._bug_title`.
- Keep this module narrow. Do not add CLI or GitHub behavior.

### UPDATED: python/larch/issue/analyze_bugs.py

Repoint `/analyze-bugs` to the shared predicate.

- Import `bug_title_match` from `larch.issue.title_match`.
- Remove local `BUG_PREFIX`, `BUG_TITLE_LIFECYCLE_PREFIXES`, and `_bug_title`.
- Change `fetch_bug_issues` to call `bug_title_match(issue.title)`.
- Do not add compatibility shims or re-export the removed private helper.

### UPDATED: python/larch/issue/learn_from_bugs.py

Apply the shared predicate to implicit default-search prepare runs only.

- Import `bug_title_match`.
- Extend `PrepareRequest` with `search_explicit: bool`.
- In `prepare_main`, detect explicit `--search` on `argv` before building the request:
  - `search_explicit=True` when any token is `--search` or starts with `--search=`
  - otherwise `search_explicit=False` (argparse default path)
- In `run_prepare`, keep the raw `list_issues` result in a local.
- If `not request.search_explicit`, filter rows where `bug_title_match(str(issue.get("title") or ""))` is true.
- Compute `filtered_non_bug` as raw count minus post-filter count.
- If `request.search_explicit`, skip filtering and report `filtered_non_bug` as `0`.
- Build digests from the filtered list (or the full list when explicit).
- Return `ISSUES_FILTERED_NON_BUG` next to `ISSUES_SELECTED`.
- Do not compare `request.search` to `DEFAULT_SEARCH` for filter gating.

### UPDATED: python/tests/issue/test_learn_from_bugs.py

Extend offline prepare coverage.

- Add an implicit-default prepare test (`search_explicit=False`, `search=DEFAULT_SEARCH`) with mixed titles:
  - keep `[DONE] [BUG] x`
  - keep `[Bug] x`
  - drop a `[FEATURE]` title that mentions bugs
- Assert:
  - `ISSUES_SELECTED` is post-filter
  - `ISSUES_FILTERED_NON_BUG` equals the drop count
  - `digest.jsonl` contains only kept issue numbers
- Add an explicit-search prepare test with the same mixed titles and `search_explicit=True`, including `search=DEFAULT_SEARCH` (same string as the default query):
  - assert no filtering
  - `ISSUES_FILTERED_NON_BUG=0`
  - digest retains the `[FEATURE]` row
- Add a `prepare_main` argv test that `--search "[BUG] in:title"` sets `search_explicit=True` and does not filter a non-bug title.
- Keep tests behind `RecordingRunner`; do not call `gh`.

### UPDATED: skills/learn-from-bugs/SKILL.md

Update Step 2 stdout parsing prose.

- Add `ISSUES_FILTERED_NON_BUG` to the list of whole-line `KEY=value` records.
- Keep this as an additive key. Do not change the prepare command shape.

## Edge cases

- Titles with lowercase or mixed-case `[Bug]` still match.
- Titles with lifecycle prefixes like `[DONE]`, `[DESIGNED]`, `[IMPLEMENTING]`, and `[STALLED]` still match after prefix stripping.
- Titles that mention `[BUG]` later in the text do not match.
- Explicit `--search` queries are unfiltered, even when the query string equals `DEFAULT_SEARCH` (for example `prepare --search "[BUG] in:title"`).
- Verbal descriptions translated to `--search` by the skill are explicit and unfiltered.
- A default implicit search that filters all rows should produce an empty digest, `ISSUES_SELECTED=0`, and the filtered count.

## Failure modes

- If `analyze_bugs.py` keeps a local duplicate predicate, the sibling surfaces can drift again.
- If filtering is gated on `request.search == DEFAULT_SEARCH`, an explicit `--search "[BUG] in:title"` wrongly drops non-bug rows.
- If filtering runs for explicit searches, topical mining can lose valid issues.
- If `ISSUES_SELECTED` stays pre-filter, the operator sees the wrong digest size.
- If the skill prompt does not mention the new key, prompt-side parsing may ignore useful diagnostics.

## Testing strategy

Run focused checks only.

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py python/tests/issue/test_analyze_bugs.py`
- `make py-lint` only if the touched Python files trigger local lint concerns or repo convention requires the Python lint target for changed Python.

Acceptance checks:

- Implicit default-search prepare drops non-matching titles.
- Explicit `--search` prepare does not filter, including when the query string matches `DEFAULT_SEARCH`.
- `ISSUES_FILTERED_NON_BUG` appears in prepare stats.
- Existing `/analyze-bugs` title normalization tests still pass.

## Acceptance

Run focused checks only.

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py python/tests/issue/test_analyze_bugs.py`
- `make py-lint` only if the touched Python files trigger local lint concerns or repo convention requires the Python lint target for changed Python.

Acceptance checks:

- Implicit default-search prepare drops non-matching titles.
- Explicit `--search` prepare does not filter, including when the query string matches `DEFAULT_SEARCH`.
- `ISSUES_FILTERED_NON_BUG` appears in prepare stats.
- Existing `/analyze-bugs` title normalization tests still pass.

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 135
