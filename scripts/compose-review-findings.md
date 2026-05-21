# compose-review-findings.sh contract

`scripts/compose-review-findings.sh` converts plan-review and code-review
finding artifacts into a single `review-findings-full.jsonl` file (one JSON
object per line). Code-review artifacts are read from
`$IMPLEMENT_TMPDIR/round-*/accepted-findings.md` and
`$IMPLEMENT_TMPDIR/round-*/oos.md`,
`$IMPLEMENT_TMPDIR/round-*/rejected-findings-full.md` when present, otherwise
`$IMPLEMENT_TMPDIR/round-*/rejected-findings.md`; the parent
`$IMPLEMENT_TMPDIR/rejected-findings-full.md` and
`$IMPLEMENT_TMPDIR/rejected-findings.md` remain fallbacks for older runs.

Inputs:

```text
--design-artifacts-dir DIR
--implement-tmpdir DIR
--issue N
--output PATH
```

Each output line is a JSON object with these fields:

```text
id               string  — the finding id (e.g. FINDING_10, REJ_C1, REJ_CR2_1)
issue_number     string  — the --issue arg, propagated verbatim
phase            string  — plan-review | code-review
outcome          string  — accepted | rejected | out_of_scope
schema_version   string  — literal "2" for records emitted by this script
reviewer_slots   array of strings — reviewer labels split from the finding body
                 (comma-separated `- **Reviewer(s)**:` / `- **Reviewer**:` / `- **Reviewers**:` / unbolded `Reviewer(s):` / `Reviewer:` / `Reviewers:`; each element redacted); defaults to `["panel"]` when no attribution line is present
round_num        string  — review round number for code-review round artifacts; empty for plan-review and legacy fallback artifacts
category         string  — best-effort focus-area label (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`). Leading `##` lines (`## <cat>: …` or `## **<cat>** — …`) are parsed first; only `outcome=out_of_scope` uses strict canonical filtering (unknown `##` tokens become `""`). Accepted/rejected bodies still record any non-empty `##`-derived label even when it is not one of the five tags. Rejected-only inner lines `### FINDING_<id>: …` are stricter: a lone canonical tag or `<canonical>: <location>` populates `category`; a single colon with a non-canonical remainder (e.g. a title-only inner line) yields `""` even when not OOS.
prose_body       string  — the full finding body (redacted; not HTML-escaped — consumers parse JSON)
```

Missing inputs are treated as "no findings"; the script still writes an empty
file and emits `FINDINGS_TOTAL=0`.

The helper redacts tmpdir paths and token-shaped secrets before writing each
record's `reviewer_slots` entries and `prose_body`. JSON escaping is handled by `jq -nc`,
so inner `<`, `>`, `&`, newlines, and quotes are preserved literally inside
the JSON string and round-trip cleanly through any JSON parser. The old
inline/archive split was removed when review findings moved from issue
anchors to committed `larch-logs/` files. Rejected code-review blocks
preserve inner `### ...` subheadings as body content unless a new top-level
rejected block header is seen. Synthetic code-review ids generated during
compose (`REJ_C...`, `OOS_C...`) include the round number for `round-N/`
artifacts so the JSONL stream does not reuse ids across review rounds.

For accepted and `[rejected]` code-review findings, `reviewer_slots` is derived from the
canonical reviewer line inside the finding body when available.
Legacy `[Code Review]` rejected headers still use the reviewer label embedded
in the header. OOS review findings are emitted from per-round `oos.md` files
with `OOS_C...` ids and `outcome=out_of_scope`. Security-tagged OOS blocks
(`focus-area = security` outside inline/triple-backtick code fencing) are
held back from the JSONL output to preserve the same public-boundary rule used
by the review tally.

`MODE=jsonl` is emitted on stdout after a successful compose; `MODE=markdown`
is no longer produced by this script. On non-zero exit, `FAILURE_LOG=<path>`
may appear on stdout.

Harness: `scripts/test-compose-review-findings.sh`.
