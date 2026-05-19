# compose-review-findings.sh contract

`scripts/compose-review-findings.sh` converts plan-review and code-review
finding artifacts into a single `review-findings-full.jsonl` file (one JSON
object per line). Code-review artifacts are read from
`$IMPLEMENT_TMPDIR/round-*/accepted-findings.md` and
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
id            string  — the finding id (e.g. FINDING_10, REJ_C1)
issue_number  string  — the --issue arg, propagated verbatim
phase         string  — plan-review | code-review
outcome       string  — accepted | rejected
reviewer      string  — the reviewer label (redacted)
category      string  — best-effort extract from a leading "## <cat>: ..." body line; empty when absent
prose_body    string  — the full finding body (redacted; not HTML-escaped — consumers parse JSON)
```

Missing inputs are treated as "no findings"; the script still writes an empty
file and emits `FINDINGS_TOTAL=0`.

The helper redacts tmpdir paths and token-shaped secrets before writing each
record's `reviewer` and `prose_body`. JSON escaping is handled by `jq -nc`,
so inner `<`, `>`, `&`, newlines, and quotes are preserved literally inside
the JSON string and round-trip cleanly through any JSON parser. The old
inline/archive split was removed when review findings moved from issue
anchors to committed `larch-logs/` files. Rejected code-review blocks
preserve inner `### ...` subheadings as body content unless a new top-level
rejected block header is seen.

`MODE=jsonl` is emitted on stdout after a successful compose; `MODE=markdown`
is no longer produced by this script. On non-zero exit, `FAILURE_LOG=<path>`
may appear on stdout.

Harness: `scripts/test-compose-review-findings.sh`.
