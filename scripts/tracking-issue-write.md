# tracking-issue-write.sh contract

## Purpose

Phase 1 (umbrella #348) foundation layer: helper for the tracking-issue lifecycle. Six narrow subcommands — five writes (`create-issue`, `append-comment`, `upsert-anchor`, `rename`, `mark-false-positive`) plus one read-only lookup (`find-anchor`) — sharing a KEY=value stdout envelope and fail-closed redaction posture modelled on `skills/issue/scripts/create-one.sh`. The first three writes were added in Phase 1; `rename` was added alongside the tracking-issue title-prefix lifecycle (see "Title-prefix lifecycle" below); `find-anchor` was added in #654 to give SKILL.md callers a paginated, multi-anchor-fail-closed marker probe that reuses the same `list_anchor_comments` + `filter_anchor_ids` helpers as `upsert-anchor`'s marker-search-fallback (without the body-write side effects). `mark-false-positive` adds the `[FALSE-POSITIVE]` signal marker without disturbing lifecycle prefixes or sibling signal markers.

## Subcommands

```
tracking-issue-write.sh create-issue   --title T --body-file F [--repo OWNER/REPO]
tracking-issue-write.sh append-comment --issue N --body-file F [--lifecycle-marker ID] [--repo OWNER/REPO]
tracking-issue-write.sh upsert-anchor  --issue N [--anchor-id ID] --body-file F [--repo OWNER/REPO]
tracking-issue-write.sh rename         --issue N --state in-progress|done|stalled [--round-trip BOOL] [--repo OWNER/REPO]
tracking-issue-write.sh mark-false-positive --issue N [--repo OWNER/REPO]
tracking-issue-write.sh find-anchor    --issue N [--repo OWNER/REPO]                (read-only)
```

## Output contract (KEY=value on stdout)

### Namespace note

This script emits `FAILED=true` / `ERROR=<msg>` on failure — NOT the `ISSUE_FAILED=true` / `ISSUE_ERROR=<msg>` prefix used by `skills/issue/scripts/create-one.sh`. The divergence is intentional: this script is not an `/issue` layer component. Parsers MUST use the `FAILED=` / `ERROR=` prefix exactly. Parsers MUST also use the `ERROR=` field (not exit code alone) to distinguish error kinds — exit 1 covers both invocation-usage errors and validated-content rejections (see exit-code table below).

### Success keys

| Subcommand | Keys |
|---|---|
| `create-issue` | `ISSUE_NUMBER=<N>`, `ISSUE_URL=<url>` |
| `append-comment` | `COMMENT_ID=<id>`, `COMMENT_URL=<url>` |
| `upsert-anchor` | `ANCHOR_COMMENT_ID=<id>`, `ANCHOR_COMMENT_URL=<url>`, `UPDATED=true\|false` (`true` when an existing anchor was PATCHed; `false` when a new anchor comment was created) |
| `rename` | `RENAMED=true\|false`, `NEW_TITLE=<title>` (`false` when the composed canonical title already equals the current canonical title — no `gh issue edit` call was made). `ROUND_TRIP_APPLIED=true\|false` is emitted only when the caller passed `--round-trip BOOL`. |
| `mark-false-positive` | `MARKED=true\|false`, `NEW_TITLE=<title>` (`false` when `[FALSE-POSITIVE]` is already present in the leading bracket-block sequence — no `gh issue edit` call was made) |
| `find-anchor` | `ANCHOR_COMMENT_ID=<id-or-empty>` — exactly one anchor → `ANCHOR_COMMENT_ID=<id>` (exit 0); zero anchors → `ANCHOR_COMMENT_ID=` empty value (exit 0); multiple anchors → `FAILED=true ERROR=multiple anchor comments found (ids: <comma-list>)` (exit 2). Stdout contains ONLY KEY=value lines (no progress text); diagnostics route to stderr — same posture as the four write subcommands. |

### Failure keys

`FAILED=true` followed by `ERROR=<single-line message>`. The `ERROR=` value is flattened to one line and length-capped at 500 bytes (matches create-one.sh convention).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Invocation-usage error OR validated-content rejection (e.g. missing body file, empty body). Disambiguate via `ERROR=`. |
| 2 | `gh` failure OR fail-closed content-state error — e.g. `upsert-anchor`'s and `find-anchor`'s "multiple anchor comments found (ids: …)" branch. `FAILED=true` / `ERROR=` already emitted on stdout; consumers must branch on `FAILED=` before checking other keys. |
| 3 | Redaction helper failure (`FAILED=true` / `ERROR=redaction:…`) |

## Invariants

### Structural choke point: compose → redact → truncate

Every subcommand composes the full logical body in memory, pipes it through `scripts/redact-secrets.sh`, and only then applies truncation. Order is non-negotiable: reversing it could slice token-shaped byte sequences and let secrets past the scrubber. The placement mirrors the `create-one.sh:202-208` "Single structural choke point" comment. Any refactor that reorders these steps must first update the test harness to prove the invariant still holds.

### gh-failure redaction

Every `gh` invocation captures stdout and stderr separately. On non-success paths, captured stderr is piped through `scripts/redact-secrets.sh` before emission in `ERROR=`. This mirrors `create-one.sh:247-280`'s outbound posture. Covers 4xx API response bodies that may echo token-bearing request material.

### Anchor skeleton preservation

Truncation operates on section interiors only — never on the HTML first-line anchor marker (`<!-- larch:implement-anchor v1 issue=<N> -->`) or on any `<!-- section:<id> -->` / `<!-- section-end:<id> -->` pair. Phase 3 consumers parse by these markers; corrupting them breaks downstream parsers silently.

### Anchor version policy (strict v1)

Upsert-anchor matches and emits only `<!-- larch:implement-anchor v1` prefixed comments. Future versions (v2, …) introduce a new marker handled by a new tool version. Mixed-version state on one issue fails closed via the multiple-anchor-comments branch (exit 2 with `FAILED=true ERROR=multiple anchor comments found (ids: <list>)`).

### find-anchor read-only contract

`find-anchor` is the only read-only subcommand. It reuses the same `list_anchor_comments` (paginated `gh api --paginate`) + `filter_anchor_ids` (strict v1 first-line + UTF-8 BOM strip) helpers as `upsert-anchor`'s marker-search-fallback, plus a small cardinality block (count + 0/1/many envelope decision). Behavior is byte-aligned with the write-side fallback: zero anchors → `ANCHOR_COMMENT_ID=` empty + exit 0; one anchor → `ANCHOR_COMMENT_ID=<id>` + exit 0; ≥2 anchors → `FAILED=true ERROR=multiple anchor comments found (ids: <comma-list>)` + exit 2; gh listing failure → `FAILED=true ERROR=<redacted gh stderr>` + exit 2 (via the shared `emit_gh_failure` path). Stdout is exclusively KEY=value lines on every path; no progress text leaks. **Marker semantic alignment with reads**: the strict-v1 first-line + BOM-strip match is intentionally aligned with `tracking-issue-read.sh`'s anchor-marker filter and `upsert-anchor`'s marker-search-fallback — `find-anchor` does NOT preserve the older inline `jq startswith("<!-- larch:implement-anchor v1")` whole-body semantics; for typical anchors (marker IS the first line, no BOM) classification is identical, but pathological comments (BOM not stripped by jq, or marker not on the true first line) classify per the first-line+BOM-strip policy.

## Truncation algorithm

Two-pass, applied AFTER redaction:

1. **Per-section cap** (`PER_SECTION_CAP=8000`): for each of the 8 canonical section slugs (`plan-goals-test`, `plan-review-tally`, `code-review-tally`, `diagrams`, `version-bump-reasoning`, `oos-issues`, `execution-issues`, `run-statistics`), if the interior between the section-open marker and section-end marker exceeds 8000 chars, replace the interior with a single inline `[TRUNCATED — <slug> exceeded 8000 chars]` line. The cut offset is **snapped to the next newline boundary** at or before 8000 so the marker always begins on its own line — this prevents open code fences from consuming the marker or subsequent section markers during GitHub rendering.

2. **Body-level cap** (`BODY_CAP=60000`): if total body length still exceeds 60000 chars after pass 1, walk the collapse priority list in order:

   `execution-issues` → `plan-review-tally` → `code-review-tally` → `oos-issues` → `run-statistics` → `version-bump-reasoning` → `diagrams` → `plan-goals-test`

   For each slug, replace the interior with `[section '<slug>' truncated — see execution-issues.md locally]`. Stop once total length fits the cap. The priority order encodes user-value: most-ephemeral sections collapse first (execution-issues are reproducible from local tmpdir); diagrams and plan-goals-test collapse last (highest user value).

### UTF-8 policy

Truncation is byte-length based. Multibyte UTF-8 splitting is tolerated because section interiors are machine-composed by `/implement` — no human-authored multibyte content is expected between section markers. Line-boundary snapping (above) prevents the more visible fence-cut corruption.

## Lifecycle markers

`append-comment` accepts `--lifecycle-marker <id>`, which prepends `<!-- larch:lifecycle-marker:<id> -->\n` to the body before redaction+truncation. Three canonical markers for Phase 2+ callers: `pr-opened`, `pr-closed`, `in-progress`. These machine-owned markers replace the prose-prefix filters (`PR opened:`, `Closed by PR #`) from the original design — prose prefixes were too loose (matched ordinary English comments).

## Title-prefix lifecycle (rename subcommand)

Tracking issues carry a machine-owned title-prefix lifecycle: `[IN PROGRESS]` during active work, `[DONE]` after the tracking run completes, `[STALLED]` when a run fails without closing. Each prefix is followed by a single space before the rest of the title (e.g., `[IN PROGRESS] Fix login bug`). `rename` is the single mutator for these prefixes; every consumer MUST use this subcommand rather than inlining `gh issue edit --title`.

The optional round-trip marker is a second managed prefix that appears after the lifecycle prefix: `[IN PROGRESS] [ROUND-TRIP] Fix login bug`. The token grammar is strict ASCII: exactly `[ROUND-TRIP] `, uppercase, ASCII hyphen, and one trailing space. Lowercase variants, Unicode homoglyphs, or `[ROUND-TRIP]foo` without the trailing separator are user content, not managed markers.

### Algorithm

1. Fetch the current title via `gh issue view --json title`.
2. Strip **exactly one** leading lifecycle prefix using `strip_lifecycle_prefix` (anchored at start; one of `[IN PROGRESS]`, `[DONE]`, or `[STALLED]` followed by a single space). Stacked lifecycle prefixes beyond the first are preserved — the helper does not "heal" corrupted titles because the healing policy is ambiguous.
3. Check whether the lifecycle-stripped title begins with the exact `[ROUND-TRIP] ` token using `has_round_trip_prefix`.
4. Strip at most one exact round-trip token using `strip_round_trip_prefix`; the remainder is the user tail.
5. Compose the new title as target lifecycle prefix + (`[ROUND-TRIP] ` if an existing exact marker was present or `--round-trip true` was passed) + user tail. Passing `--round-trip false` does not remove an existing marker; preservation is sticky-add-only. Omitting `--round-trip` behaves like false for adding, but still preserves an existing marker if one is already present.
6. Pipe the prospective new title through `scripts/redact-secrets.sh` (same posture as `create-issue`).
7. Truncate to 256 chars if the result exceeds GitHub's title limit. Truncation uses bash string semantics (`${#var}` + slicing), which matches GitHub's character-based 256 limit under UTF-8 locales. Both managed prefixes are preserved at the head; only the user tail is sliced. The round-trip token is 13 ASCII characters including the trailing space.
8. If the resulting title equals the current canonical title, emit `RENAMED=false` and skip the `gh` call.
9. Otherwise call `gh issue edit --title` and emit `RENAMED=true`.

When `--round-trip` was passed, emit `ROUND_TRIP_APPLIED=true` iff the final title, after one lifecycle prefix strip, begins with the exact `[ROUND-TRIP] ` token. Do not emit this key on omit-flag call paths; `find-lock-issue.sh` depends on the older stdout shape.

### Idempotency

Re-calling `rename --state X --round-trip Y` on an issue already at state X is a no-op (`RENAMED=false`) when the leading round-trip marker state already matches the desired sticky-add result. Existing `[ROUND-TRIP] ` markers are preserved even when `--round-trip false` is passed. This matters for resumed `/implement` sessions and for the bash drivers' EXIT-trap paths (the trap may fire after a successful explicit rename-to-done; the re-rename to `[STALLED]` is a no-op because the guard flag prevents it, but even without that the helper would emit `RENAMED=false` for an already-stalled title with matching marker state).

Adversarial cases are intentional: `[IN PROGRESS] [round-trip] foo` remains lowercase user content and `ROUND_TRIP_APPLIED=false` unless a canonical marker is added; `[IN PROGRESS] [ROUND-TRIP]foo` is missing the managed marker's trailing space, so `--round-trip true` produces `[STATE] [ROUND-TRIP] [ROUND-TRIP]foo`; a redactable token in the user tail is redacted before comparison and truncation; a mid-string `[ROUND-TRIP]` occurrence does not count for `ROUND_TRIP_APPLIED`.

### Distinction from `/fix-issue`'s "IN PROGRESS" comment lock

The title prefix `[IN PROGRESS]` (followed by a space) is the **tracking-issue lifecycle state** — whose job is to signal human triage and filter `/fix-issue` auto-pick. It is orthogonal to `/fix-issue`'s existing **comment-based** lock (last comment equal to the bare text `IN PROGRESS`), which is the **concurrency lock** preventing two concurrent `/fix-issue` runners from picking the same subject issue. Both mechanisms coexist:
- Comment lock: applies to any `/fix-issue` subject issue; set at step 1 of `/fix-issue`; cleared when work completes.
- Title prefix: applied to `/implement`-managed tracking issues for the duration of the active run — both fresh-created (Step 0.5 Branch 4) and adopted (Branch 2/3/Branch 1 resume safety net, e.g. via `/fix-issue` forwarding `--issue <N>`). Step 12a/12b flips `[IN PROGRESS]` → `[DONE]` on merge; Step 18 Branch A flips it to `[STALLED]` on failure; Step 18 Branch B flips it to `[DONE]` on clean non-merge or draft completion (PR opened without auto-merge). The `rename` subcommand strips exactly one leading managed prefix before prepending the new one, so user-authored title text is preserved across transitions.

## Mark-false-positive Semantics

`mark-false-positive` is the canonical mutator for the additive `[FALSE-POSITIVE]` signal marker. It fetches the current title, redacts it, inserts `[FALSE-POSITIVE]` via `scripts/lib-title-markers.sh`, compares the redacted-but-not-truncated result for idempotency, truncates the outbound title to 256 characters, and calls `gh issue edit --title` only when the title changed. The idempotency comparator intentionally uses the redacted but not truncated current title because this subcommand only inserts a prefix; truncation-induced collisions are not a meaningful no-op signal here.

The leading bracket-block sequence is zero or more bracket tokens like `[...]` followed by a space at the start of the title. If `[FALSE-POSITIVE]` is already present anywhere in that leading sequence, the helper is idempotent and returns the title unchanged. If the title begins with exactly one managed lifecycle prefix (`[IN PROGRESS]`, `[DONE]`, or `[STALLED]`, each followed by a space), the marker is inserted immediately after that prefix. Otherwise it is prepended at the start. Sibling markers such as `[OOS]` and `[ROUND-TRIP]` are preserved verbatim and never reordered.

Locked edge cases:

- Empty input title emits `[FALSE-POSITIVE]`.
- `[OOS]Foo` has no space after `]`, so it is not part of the leading bracket-block grammar and becomes `[FALSE-POSITIVE] [OOS]Foo`.
- A marker present later in the title, outside the leading bracket-block sequence, is not idempotent. Example: `[DONE] Foo [FALSE-POSITIVE] bar` becomes `[DONE] [FALSE-POSITIVE] Foo [FALSE-POSITIVE] bar`.
- Redaction precedes truncation, matching the title-write posture of `rename`; gh stderr is redacted through the shared `emit_gh_failure` path.

## Conventions

Uses Bash 3.2-compatible constructs (indexed arrays only; no associative arrays, no `mapfile`) so macOS-default bash runs match Ubuntu CI. Precedent: `scripts/dialectic-smoke-test.sh`.

## Makefile wiring

The regression harness `scripts/test-tracking-issue-write.sh` is wired into `make test-harnesses` (which is a prerequisite of `make lint`). Standalone target: `make test-tracking-issue-write`.

## Test harness

`scripts/test-tracking-issue-write.sh` covers sixteen assertion categories (a-p):

- **(a)** `create-issue` redacts title + body (`sk-ant-*` secret → `<REDACTED-TOKEN>`).
- **(b)** `create-issue` exits 3 with `FAILED=true` / `ERROR=redaction:…` when the redactor is missing. Pins exact key literals `FAILED=true` (not `ISSUE_FAILED`).
- **(c)** `upsert-anchor` preserves the HTML anchor marker + all 8 section markers after a >60000-char body-level collapse.
- **(d)** `upsert-anchor` per-section 8000 truncation inserts `[TRUNCATED — <id> exceeded 8000 chars]` on its own line (line-boundary-snapped).
- **(e)** `append-comment` does NOT touch the anchor comment (stub-gh asserts the anchor comment is untouched).
- **(f1) Idempotency**: `upsert-anchor` with exactly one existing anchor comment PATCHes it, emits `UPDATED=true`, creates no new comment on double-call.
- **(f2) Multiple-anchor fail-closed**: `upsert-anchor` with 2+ marker comments exits 2 with `FAILED=true ERROR=multiple anchor comments found (ids: <list>)`.
- **(g) gh-failure redaction**: stub-gh emits a token-bearing stderr on failure → the `FAILED=true ERROR=…` line contains `<REDACTED-TOKEN>` and not the raw token.
- **(h) Missing `anchor-section-markers.sh` helper**: when the script's sourced helper is missing from the script's `$SCRIPT_DIR`, it fails closed with `FAILED=true` / `ERROR=missing helper: …` on stdout and exits 1 — preserving the stdout contract invariant.
- **(i) `SECTION_MARKERS` ⊆ `COLLAPSE_PRIORITY` invariant**: every slug defined in `scripts/anchor-section-markers.sh` appears in `COLLAPSE_PRIORITY`, so the body-level truncation pass has a collapse target for every section.
- **(j) `rename` subcommand**: base rename (no existing prefix → prepend), transition rename (`[IN PROGRESS]` → `[DONE]`), idempotent no-op (already at target state → `RENAMED=false`, no `gh` call), strip-exactly-one (stacked-prefix residue preserved), redact pipeline applied (token in title → `<REDACTED-TOKEN>` in outbound), invalid `--state` → `FAILED=true ERROR=invalid --state: ...`.
- **(k) Seed-only visible placeholder survival** in `upsert-anchor` publish path (issue #431).
- **(l) `find-anchor` zero anchors**: empty comment list → `ANCHOR_COMMENT_ID=` (empty value) on stdout, exit 0.
- **(m) `find-anchor` one anchor**: stub returns one v1-marker comment → `ANCHOR_COMMENT_ID=<id>` on stdout, exit 0.
- **(n) `find-anchor` multi-anchor fail-closed**: stub returns two v1-marker comments → exit 2, `FAILED=true ERROR=multiple anchor comments found (ids: 5001,5002)`, no `ANCHOR_COMMENT_ID=` line on stdout.
- **(o) `find-anchor` pagination across >100 comments** (regression guard for #654): stub is sensitive to whether `--paginate` is in the `gh api` argv. WITHOUT `--paginate`, returns only the first 100 rows (no anchor); WITH `--paginate`, returns all 150 rows with the anchor on row 125. Asserts `find-anchor` returns `ANCHOR_COMMENT_ID=5125` (the late-page anchor) — a future edit dropping `--paginate` from `list_anchor_comments` would fail this assertion.
- **(p) `mark-false-positive` subcommand**: additive marker ordering with lifecycle prefixes, `[OOS]` co-existence, sibling `[ROUND-TRIP]` preservation, leading-sequence-only idempotency, empty-title and no-space edge cases, redaction, 256-character truncation, and gh-failure envelope parity.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/anchor-section-markers.sh` | Single source of truth for `SECTION_MARKERS`; sourced by this script at startup. Missing helper is fail-closed (test harness case (h)). |
| `scripts/lib-title-markers.sh` | Sourced helper for additive signal marker insertion; full grammar is documented in this file. |
| `scripts/false-positive-keywords.md` | Keyword matcher contract for `/fix-issue`'s optional close-time false-positive marker trigger. |
| `scripts/redact-secrets.sh` | Sole outbound scrubber — do NOT bypass or add a parallel redactor. |
| `scripts/tracking-issue-read.sh` | Delegates `append-comment` when invoked with `--issue + --prompt`. |
| `scripts/test-tracking-issue-write.sh` | Regression harness for this script — every behavioral change here must be mirrored in the harness. |
| `skills/fix-issue/scripts/issue-lifecycle.md` | Documents the `/fix-issue` close-time consumer that calls `mark-false-positive` on keyword matches. |
| `scripts/assemble-anchor.sh` | Companion helper that assembles anchor bodies from `$IMPLEMENT_TMPDIR/anchor-sections/`. Shares `SECTION_MARKERS` ordering via the same sourced helper. |
| `skills/implement/references/anchor-comment-template.md` | Human-readable template describing the same 8 section slugs + anchor first-line marker; the executable source of truth is `scripts/anchor-section-markers.sh`. |
| `SECURITY.md` | Documents the outbound-redaction invariant, gh-failure redaction, anchor-skeleton preservation. |

## Security

See `SECURITY.md` "tracking-issue-write.sh outbound path" subsection.
