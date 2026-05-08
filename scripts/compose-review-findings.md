# compose-review-findings.sh — sibling contract

## Purpose

Compose the `review-findings-full` anchor fragment from the existing
finding-source artifacts produced by `/design` (plan-review accepted and
plan-review rejected) and by `/implement` Step 5 (code-review rejected).
When the inline payload exceeds a configurable byte threshold (default
30 000 bytes, set per issue #1402's design clarification), switch to
**archive-pointer mode**: write a `docs/review-archive/issue-<N>.jsonl`
file with one JSON object per finding and replace the inline section body
with a small pointer + count summary. Archive files are staged as
same-directory tempfiles and then published with `mv -f` so readers never
observe a partially copied final `issue-<N>.jsonl`.

This is the load-bearing helper for issue #1402's `review-findings-full`
section. The existing `plan-review-tally` and `code-review-tally`
sections are unchanged — this section is **purely additive** and carries
the per-finding payload that miners can cluster on without NLP.

## Primary callers

- `skills/implement/SKILL.md` Step 5 — after `/review` returns (normal
  mode) or the quick-mode review loop completes, the orchestrator
  composes the `review-findings-full` fragment and writes it to
  `$IMPLEMENT_TMPDIR/anchor-sections/review-findings-full.md`. If
  `$ISSUE_NUMBER` is set, the next progressive `refresh-anchor.sh` call
  upserts the freshly composed fragment into the tracking-issue anchor.

## Inputs

| Flag | Required | Default | Purpose |
|---|---|---|---|
| `--design-artifacts-dir DIR` | no | empty | Directory holding `accepted-plan-findings.md` and the plan-review entries of `rejected-findings.md`. Typically `$IMPLEMENT_TMPDIR/design-export/` (the `/design` manifest copies these artifacts there). When absent or empty, no plan-review payload is emitted. |
| `--implement-tmpdir DIR` | no | empty | Directory holding `rejected-findings.md` with `[Code Review]` headers — the file accumulated by `/implement` Step 5. When absent or empty, no code-review payload is emitted. |
| `--issue N` | yes | — | Tracking issue number; used as the archive filename (`issue-<N>.jsonl`). |
| `--output PATH` | yes | — | Where to write the composed anchor fragment. |
| `--archive-dir DIR` | no | `docs/review-archive` | Where to write the JSONL archive when the inline payload exceeds `--archive-threshold`. |
| `--archive-threshold N` | no | `30000` | Byte threshold for inline → archive switchover (per issue #1402's clarification). |

The script is **fail-open** on missing inputs: a missing artifact directory
or file means "no findings of that kind". The composed fragment is always
non-empty (worst case: a one-line "No review findings captured in this
run." note) so the anchor slot is always populated.

`jq` is a required runtime dependency. Per issue #1425, JSONL emission goes
exclusively through `jq -nc --arg` for every string field, and the script
fails closed when `jq` is unavailable.

## Output (KV on stdout)

```
COMPOSED=true
OUTPUT=<path>
FINDINGS_TOTAL=<N>
MODE=inline|archive
ARCHIVE_PATH=<path>     # only when MODE=archive
ARCHIVE_BYTES=<N>       # only when MODE=archive
```

On invocation / I/O failure:

```
FAILED=true
ERROR=<single-line message>
```

with non-zero exit (1 for usage / 2 for I/O).

## Schema — per-finding record

Inline mode: rendered as markdown bullets per finding, with the verbatim
source-artifact prose blockquoted so it cannot accidentally re-parse as a
new top-level finding heading. Markdown shape:

```markdown
### <id> — <category>
- **Phase**: plan-review | code-review
- **Outcome**: accepted | rejected
- **Reviewer**: <name>
- **Category**: <category>
- **Prose body** (verbatim from source artifact):

> <body line 1>
> <body line 2>
> ...
```

Archive mode: one JSON object per line (`docs/review-archive/issue-<N>.jsonl`):

```json
{"id":"...","phase":"plan-review|code-review","outcome":"accepted|rejected","reviewer":"...","category":"...","prose_body":"..."}
```

JSONL emission goes exclusively through `jq -nc --arg` for every string
field, including bounded enums. Free-form fields (`prose_body`, `reviewer`,
embedded title) are redacted via the canonical
`redact-tmpdir-paths.sh | redact-secrets.sh` chain before JSON encoding so
secrets cannot reach the committed `docs/review-archive/` JSONL. The same
redacted values feed the inline markdown branch, so inline mode and
archive-pointer mode share one pre-publication boundary. Redactor stderr is
preserved so PEM-truncation WARN diagnostics surface, mirroring
`tracking-issue-write.sh`'s `redact()` posture. Bounded enums (`id`, `phase`,
`outcome`, `category`) are not redacted because they are script-derived; they
still pass through `jq --arg` for JSON safety. A non-zero redactor exit
triggers the documented `FAILED=true` / `ERROR=...` envelope. See
`SECURITY.md` for the corresponding public-archive trust-model note. The
on-disk source files preserve `file:line` citations and
`suggested_diff_excerpt` snippets inside the prose body — that prose carries
the load-bearing miner content verbatim after redaction. Future iterations
may extract those into separate JSON keys.

## Category derivation

The `category` tag is mechanical, derived from the reviewer name (and, for
accepted plan-review findings, augmented with the finding title). The tag
enum:

- `architecture` — Architecture / Standards reviewer name fragments
- `correctness` — Correctness specialist
- `structure` — Structure specialist
- `edge-cases` — Edge-cases / Failure-modes reviewers
- `innovation` — Innovation / Exploration reviewers
- `pragmatism` — Pragmatism / Safety reviewers
- `security` — Security specialist
- `testing` — Testing specialist
- `docs` — Documentation specialist
- `generic` — Generic Cursor / Codex / Claude reviewer slot
- `other` — none of the above

This is a superset of the issue #1402 acceptance enum (`correctness |
structure | edge-cases | security | testing | docs`); the union covers
both the plan-review personalities and the code-review specialists so
both phases produce useful tags.

## Source-artifact byte formats

Read from these byte-preserved templates:

- `accepted-plan-findings.md` (per `skills/design/references/plan-review.md`):
  ```
  ### FINDING_N: <title>
  - **Concern**: <what was raised>
  - **Resolution**: <how the plan was revised>
  ```
  The reviewer name is not directly captured in this template — accepted
  findings emerge from the voting panel, so the helper records
  `reviewer=panel` unless a `Reviewer:` or `surfaced by` line is present
  in the body.

- `rejected-findings.md` (per `skills/design/references/plan-review.md` for
  the plan-review side and per `skills/implement/SKILL.md` Step 5 for the
  code-review side):
  ```
  ### [Plan Review] <Reviewer Name>
  **Finding**: <thorough description>
  **Reason not implemented**: <complete justification>
  ```
  with `### [Code Review] ...` for the code-review entries. The helper
  separates the two phases by header prefix.

The script **does not** modify the source files; it reads them, rewraps
the prose into the new section, and emits the structured tags.

## Edit-in-sync

| File | Relationship |
|---|---|
| `scripts/anchor-section-markers.sh` | Carries the `review-findings-full` slug in `SECTION_MARKERS`. |
| `scripts/tracking-issue-write.sh` | Carries the slug in `COLLAPSE_PRIORITY` (priority position 2 — second-most-ephemeral). |
| `skills/implement/references/anchor-comment-template.md` | Documents the section in the canonical 11-slug template; carries the body-level collapse priority and the edit-in-sync table. |
| `skills/implement/SKILL.md` Step 5 | Owns the runtime invocation of this helper after `/review` returns or the quick-mode loop completes. |
| `skills/design/references/plan-review.md` | Owns the byte-preserved formats this helper parses (accepted plan-review + rejected plan-review entries). |
| `${CLAUDE_PLUGIN_ROOT}/scripts/test-compose-review-findings.sh` | Regression harness; wired into `make lint` via the `test-compose-review-findings` target. |

## Known limitations

- **Accepted code-review findings are not currently captured.** The
  `/review` skill and `/implement` Step 5 quick-mode loop accept findings
  by voting / by main-agent unilateral decision but do not write a
  byte-preserved `accepted-code-review-findings.md` artifact. This helper
  silently emits no records for that phase + outcome pair. Wiring up
  the missing artifact is a documented follow-up.
- **Reviewer name extraction for accepted plan-review** is best-effort
  (greps the body for a `Reviewer` or `surfaced by` line). Most accepted
  findings will record `reviewer=panel`. The category tag is still
  derivable from the title and any reviewer prose.
- **Cycle-safety**: the parsers identify entries by `### FINDING_` /
  `### [Plan Review]` / `### [Code Review]` headings; an embedded `###`
  heading line inside a finding body would split the entry. The blockquote-rendering
  pass mitigates the risk in the *output* fragment, but the *input*
  byte-preserved templates from `/design` / `/implement` already follow a
  flat structure so this is not a regression source.
