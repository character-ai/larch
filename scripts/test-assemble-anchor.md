# test-assemble-anchor.sh contract

## Purpose

Regression harness for `scripts/assemble-anchor.sh`. The exact assertion count is not inlined here per the drift-prone-prose-in-docs rule — count the `pass`/`fail` call sites in the harness or read its trailing summary line. The catalog below mirrors the `scripts/assemble-anchor.md` invariant set: empty sections directory (line-count, line-walk, placeholder presence, injected plugin-version row), partial fragments and whitespace-only fragments (placeholder gating), nonexistent `--sections-dir` (placeholder fires for missing dir), missing plugin root fallback, exact line-shape around a newline-terminated fragment, line-shape around a no-trailing-newline fragment, populated run-statistics injection, hydrated run-statistics dedup (resume idempotency), populated-but-normalized-to-empty seed-scaffold fallback, legacy `<!-- token-report-begin -->...<!-- token-report-end -->` block strip in `run-statistics` (matched pair, lone begin, lone end), full fragments, missing-helper failure, invalid-`--issue` usage error, first-line marker exactness, non-directory `--sections-dir` fail-closed, and unreadable-fragment fail-closed.

## Assertion catalog

- **(a)** Empty sections directory: output has exactly `2 + 2*N + 5` lines (anchor first-line marker + seed-only visible placeholder line + `N` marker pairs, where `N = |SECTION_MARKERS|`, plus the injected minimal run-statistics table interior). Marker pairs appear in `SECTION_MARKERS` order, starting at line 3. Pinned line-2 literal: `_/implement run in progress — sections below populate as the run proceeds._`.
- **(a2)** Empty sections directory: explicit regression guard that the seed-only visible placeholder literal is present in the output (issue #431).
- **(a3)** Partial fragments (one slug populated with non-whitespace content): the placeholder is suppressed — the gate fires only on the all-empty seed.
- **(a4)** All fragments populated with whitespace-only content (newlines, spaces, tabs): the placeholder still fires (lenient predicate per dialectic DECISION_1).
- **(a5)** Nonexistent `--sections-dir`: `ASSEMBLED=true` and the placeholder fires; the all-empty pre-pass treats a missing directory the same as an empty one.
- **(a6)** Missing `CLAUDE_PLUGIN_ROOT` target: the injected plugin-version row falls back to literal `unknown`.
- **(b)** Partial fragments: populated content appears only where fragment files exist; empty marker pairs elsewhere. Order preserves `SECTION_MARKERS` indexing (`diagrams` before `version-bump-reasoning`).
- **(b2)** Newline-terminated fragment → exactly one newline before the close marker (regression guard for the pre-fix `$(tail -c 1 ...)` command-substitution newline-stripping bug, which inserted an extra blank line for every populated fragment). Full output compared against a byte-exact expected fixture.
- **(b3)** Fragment without a trailing newline → helper inserts the missing newline so the close marker still appears on its own line; fragment content and close marker do not run together on the same line.
- **(b4)** Populated `run-statistics` fragment: trailing blank lines are stripped and the plugin-version row is appended immediately before the section close marker.
- **(b5)** Hydrated `run-statistics` fragment whose interior already ends with a stale `| larch plugin version | <X.Y.Z> |` row: the stale trailing version row is stripped before a freshly-captured row is appended, producing exactly one plugin-version row in the output. Regression guard against the resume / hydration duplicate-row case.
- **(b6)** Populated `run-statistics` fragment whose entire content is a single stale version row (no `## Run Statistics` heading, no table header) normalizes down to empty after the strip loop. The helper falls through to the seed-style scaffold so the assembled section is a well-formed table (heading + header + fresh version row) instead of an orphan row.
- **(b8)** Hydrated `run-statistics` fragment containing a legacy `<!-- token-report-begin -->...<!-- token-report-end -->` Token Report block: the legacy block (markers + interior) is stripped before assembly, surrounding non-legacy content is preserved, and exactly one fresh plugin-version row is appended. Closes #1466 sub-item B (was #1440); pre-#1429 anchors hydrated this block inside `run-statistics` — after the token-report split (#1429) the block lives in its own `token-report` section, so leaving the legacy markers in `run-statistics` would publish duplicate Token Report content on resumed runs.
- **(b9)** Lone `<!-- token-report-begin -->` marker (degraded-input case): the helper strips from the marker through EOF and preserves pre-marker content.
- **(b10)** Lone `<!-- token-report-end -->` marker (degraded-input case): the helper strips from BOF through the marker and preserves post-marker content.
- **(b11)** Multi-pair legacy token-report blocks: every begin/end pair is stripped (the awk strip loop iterates to a fixed point). Inter-block and pre/post content is preserved.
- **(b12)** Matched pair followed by an orphan `<!-- token-report-end -->` (no second begin): the matched pair is stripped on iteration 1; the orphan end on iteration 2 is dropped as marker-line-only. Content above the matched pair and between the pair and the orphan is preserved. Round-3 review FINDING_1 — without this, the orphan-end would route into the lone-end branch and strip BOF→end on iteration 2.
- **(b13)** Matched pair followed by an orphan `<!-- token-report-begin -->` (no following end): symmetric to (b12) — the orphan begin is dropped as marker-line-only and trailing content is preserved.
- **(c)** Full fragments: all SECTION_MARKERS slugs populated and emitted.
- **(d)** Missing `anchor-section-markers.sh` helper: running a copy of `assemble-anchor.sh` in a fake tree without the helper emits `FAILED=true` + `ERROR=missing helper: ...` on stdout and exits 1.
- **(e)** Invalid `--issue` value (non-integer): emits `FAILED=true` + `ERROR=usage: invalid value for --issue ...` on stdout and exits 1.
- **(f)** First-line marker exactness: output always begins with `<!-- larch:implement-anchor v1 issue=<N> -->` where `<N>` is the `--issue` value.
- **(g)** Non-directory `--sections-dir` (regular file passed where a directory is expected): fails closed with `FAILED=true` + `ERROR=sections-dir exists but is not a directory: …` on stdout and exits 2. Regression guard: pre-fix the helper silently produced an all-empty skeleton in this case, which could clobber populated remote anchor content on upsert.
- **(h)** Unreadable fragment file (chmod 000 on a listed slug): fails closed with `FAILED=true` + `ERROR=failed to read fragment: …` on stdout and exits 2. Skipped when the test runs as root (root bypasses POSIX file-read permission checks). Regression guard: pre-fix the helper silently emitted an empty section interior on fragment read failure, which could also clobber remote content.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/assemble-anchor.sh` | Under test — every behavioral change in that script must be mirrored here. |
| `scripts/anchor-section-markers.sh` | Sourced by the harness to resolve canonical slug order for ordering assertions. |
| `scripts/assemble-anchor.md` | Pins the assertion catalog above. |

## Makefile wiring

Wired into `make test-harnesses` (prerequisite of `make lint`). Standalone target: `make test-assemble-anchor`.
