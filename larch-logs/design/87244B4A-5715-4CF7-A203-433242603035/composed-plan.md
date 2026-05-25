## Plan


## Approach

Add a sourced bash library `scripts/lib-title-eligibility.sh` exposing three predicates plus shared grammar constants. Two callers consume it:

1. **/design Step 0b** — after sub-step 2 (`gh issue view ... --json body,labels,number,title`) and BEFORE sub-step 3 (clarify-loop router), call the lifecycle-reject and brainstorm-prefix predicates on the fetched title. On reject match: export `SUMMARY_OUTCOME=cancelled-title-filter`, run the `### Final summary block` fenced bash block, print a one-line `**⚠ /design: ...**` error to stderr citing the matched prefix family, preserve `$DESIGN_TMPDIR` (skip Step 6 cleanup), and exit 1. On brainstorm match: print a bold info banner and set `brainstorm_requested=true` for the run.
2. **skills/issue/scripts/list-issues.sh:148** — source the library and read the archival-prefix jq-snippet constant from it instead of inlining `DEDUP_SKIP_PREFIX_FILTER`. Functionally identical filter; the regex literal now lives in one place.

The new library only exports **grammar** (regex strings + token lists) and small predicate functions. It does NOT take ownership of the bash↔jq impedance — list-issues.sh continues to use jq with a string snippet sourced from the library, /design uses bash `=~` / `case` against the same library constants. Both sides are kept consistent because the library's regression harness asserts the jq snippet and the bash regex match the same set of fixture titles.

**Predicate ordering inside the new Step 0b sub-step is mandatory**: (a) `title_has_lifecycle_reject_prefix` (exit on match), (b) `title_has_archival_report_prefix` (exit on match), (c) `title_starts_with_brainstorm` (set flag and continue on match). Earlier matches short-circuit; only the brainstorm predicate is non-exiting. This ordering is pinned in `scripts/test-design-structure.sh` so a future edit cannot silently reorder the checks and produce incoherent behavior on `[DESIGNING] Brainstorm: foo`-style titles.

Bash 3.2 portability: use POSIX character classes inside ERE (`[[:upper:]]`, no `${var^^}`), explicit case folding via tr where needed.

The brainstorm match requires "Brainstorm" as a leading word — i.e., followed by a non-letter or end of string — so titles like `Brainstorming a feature` do NOT match. Match regex: `^[Bb][Rr][Aa][Ii][Nn][Ss][Tt][Oo][Rr][Mm]([^A-Za-z]|$)`.

State-token rejection matches `^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]` case-insensitively, with or without a trailing space (defensive against operator-edited titles).

Report-prefix rejection mirrors the surviving `list-issues.sh` grammar exactly: `^\[.*[Rr][Ee][Pp][Oo][Rr][Tt]\] ` (bash ERE) and `^\\[.*report\\] ` (jq, after `ascii_downcase`). The trailing space inside the bracket-block is required (matches `[X Report] foo`, does NOT match `[Report]<EOL>`, does NOT match `[Reporting] foo`).

The migration cleanup also removes one stale orphan comment at `skills/issue/scripts/add-blocked-by.sh:13` referencing the deleted `skills/fix-issue/scripts/find-lock-issue.sh` path.

## Files to modify/create

### NEW: `scripts/lib-title-eligibility.sh`

Sourced library (no shebang, `shellcheck shell=bash` directive). Bash 3.2-compatible. Exports:

- `LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH` — bash ERE: `^\[.*[Rr][Ee][Pp][Oo][Rr][Tt]\] `
- `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` — jq filter snippet identical to current `DEDUP_SKIP_PREFIX_FILTER` content (research / [research] / investigate / [investigate] / report-prefix)
- `LARCH_TITLE_LIFECYCLE_REJECT_REGEX` — bash ERE: `^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]` with case-insensitive matching done by the caller via `shopt -s nocasematch` or `tr` pre-pass
- `LARCH_TITLE_BRAINSTORM_REGEX` — bash ERE: `^[Bb][Rr][Aa][Ii][Nn][Ss][Tt][Oo][Rr][Mm]([^A-Za-z]|$)`

Predicate functions (each returns 0 on match, 1 otherwise; takes title as `$1`):
- `title_has_archival_report_prefix` — for the report-only check (subset of the jq filter, used by /design)
- `title_has_lifecycle_reject_prefix` — emits the matched bracket-token on stdout when matched (so caller can include it in the error message)
- `title_starts_with_brainstorm`

All predicates default to "no match" (return 1) on empty input to avoid false positives.

### NEW: `scripts/lib-title-eligibility.md`

Sibling contract (per `.claude/rules/script-md-siblings.md`). Sections: Purpose, Exported grammar, Predicate functions (including the mandatory ordering rule used by /design), Bash 3.2 portability, Primary callers (list-issues.sh, design SKILL.md Step 0b), Test harness pointer, Edit-in-sync rules.

### NEW: `scripts/test-lib-title-eligibility.sh`

Regression harness. Self-contained (no real `gh` calls). Fixture matrix:
- Lifecycle-reject hits: `[IMPLEMENTING] foo`, `[DONE] bar`, `[DESIGNING] baz`, `[DESIGNED] qux`, plus case-insensitive variants `[implementing] x`, `[Done]Y`
- Lifecycle-reject misses: `[STALLED] z` (not in reject list per user spec), `[PLANNED] z`, `[IN PROGRESS] z`, `foo [DESIGNING] bar` (prefix only, no inner match), `IMPLEMENTING foo` (no bracket)
- Report-prefix hits: `[Analysis Report] foo`, `[Research Report] bar`, `[Run Logs Audit Report 2026-05-25T...] baz`, `[Report] foo` (matches because the trailing-space-inside-bracket form `[Report] ` is present per the surviving list-issues.sh semantics)
- Report-prefix misses: `[Reporting] foo` (no trailing space inside bracket), `Report foo` (no leading bracket), `[X Report]foo` (no space after `]`)
- Brainstorm hits: `Brainstorm: foo`, `Brainstorm foo`, `BRAINSTORM bar`, `brainstorm`, `Brainstorm-mode`, `Brainstorm: <empty>`
- Brainstorm misses: `Brainstorming a feature`, `Pre-brainstorm session`, `foo Brainstorm bar`
- jq/bash equivalence: for a fixed list of 12 fixture titles, run both the bash predicate and the jq snippet through `jq` and assert identical pass/reject set

### NEW: `scripts/test-lib-title-eligibility.md`

Sibling stub per `.claude/rules/script-md-siblings.md`. Points at `lib-title-eligibility.md` as the primary contract.

### UPDATED: `skills/issue/scripts/list-issues.sh`

Replace the inline `DEDUP_SKIP_PREFIX_FILTER='select((.title // "" ...'` definition with a `source` + var-export pattern. **Source-path resolution is gated on precedent verification at implementation time**: run `grep -rn 'source.*scripts/lib-\|\\. "[^"]*scripts/lib-' skills/*/scripts/*.sh` to enumerate existing cross-tree sourcing forms; adopt the dominant pattern verbatim. If no clear precedent exists, prefer `CLAUDE_PLUGIN_ROOT`-based resolution (consistent with SKILL.md Bash blocks). Pin the chosen form in `lib-title-eligibility.md`'s "Primary callers" section. Functional behavior unchanged.

### UPDATED: `skills/design/SKILL.md`

Insert a new sub-step **2.5** (immediately after current sub-step 2 "Fetch issue", BEFORE sub-step 3 "Clarify loop") titled **"Title-eligibility filter"**. The sub-step:

1. Sources `${CLAUDE_PLUGIN_ROOT}/scripts/lib-title-eligibility.sh`.
2. Calls `title_has_lifecycle_reject_prefix "$ISSUE_TITLE"` — on match, exports `SUMMARY_OUTCOME=cancelled-title-filter`, runs the `### Final summary block` fenced bash block, then prints `**⚠ /design: issue title starts with managed lifecycle marker <token> — refusing to design. Rename the title (drop the bracket prefix) and re-invoke /design.**` to stderr and exits 1. `$DESIGN_TMPDIR` is preserved (Step 6 cleanup gates on `PLAN_WRITE_OK=true` and outcome, both absent on this exit path).
3. Calls `title_has_archival_report_prefix "$ISSUE_TITLE"` — on match, same exit pattern as (2): export `SUMMARY_OUTCOME=cancelled-title-filter`, run Final summary block, print `**⚠ /design: issue title matches archival report-prefix `[... Report]` — refusing to design. Such titles are reserved for `/research` / `/report-tokens` artifacts. Rename the title and re-invoke /design.**`, exit 1.
4. Calls `title_starts_with_brainstorm "$ISSUE_TITLE"` — on match, prints `**ℹ /design: detected Brainstorm title prefix — auto-enabling brainstorm mode (run-params `brainstorm_requested=true`) even though --brainstorm was not on argv.**` to chat (bold info banner) and sets the mental `brainstorm_requested=true` flag that sub-step 6 will pass into `write-run-params.sh`. Does NOT exit.

The sub-step explicitly states the mandatory ordering: (a) lifecycle-reject (exit on match), (b) archival-report (exit on match), (c) brainstorm (set flag and continue on match). Earlier matches short-circuit.

Also update Step 0b sub-step 1 (verbal-create path) note: after `/larch:issue` returns and `ISSUE_NUMBER` is bound, the same filter applies at sub-step 2.5 — if a verbal-text-derived title happens to match the reject grammar (e.g. operator typed `[IMPLEMENTING] foo` as verbal text), the freshly-created issue is rejected and the operator must rename it before retrying.

Extend the `### Final summary block` orchestrator contract enum list to include `cancelled-title-filter` (insert in alphabetical order alongside `cancelled-clarify | cancelled-already-planned | cancelled-tier-gate | cancelled-sprawl | cancelled-plan-size-hard | cancelled-decompose | approved | approved-partition | failed-plan-write`). Update `skills/design/scripts/render-final-summary.sh` (and sibling `.md`) to accept and render the new outcome value with a clear "Refused (title-filter)" mode-line, mirroring the rendering of other `cancelled-*` outcomes.

Documentation-bias changes only inside SKILL.md beyond the new sub-step text and the enum-list extension; no script changes inside SKILL.md prose blocks.

### UPDATED: `skills/issue/scripts/add-blocked-by.sh`

Remove the stale orphan comment at line 13 referencing the deleted `skills/fix-issue/scripts/find-lock-issue.sh`. Surrounding comment block on lines 11-16 trimmed; the GET-vs-POST asymmetry note stays (it is still accurate; the GET-side caller was just deleted along with fix-issue).

### UPDATED: `Makefile`

Add a `test-lib-title-eligibility` target wired into the appropriate test-harnesses-N shard, mirroring sibling lib-* test targets (e.g. `test-lib-title-markers`). Find the shard with fewest current entries; default to `test-harnesses-1`.

### UPDATED: `scripts/test-design-structure.sh`

Add anchor lines pinning: (a) the new Step 0b sub-step 2.5 prose location (between sub-step 2 and sub-step 3); (b) the mandatory predicate-ordering rule (lifecycle-reject → archival-report → brainstorm); (c) the `cancelled-title-filter` enum value in the Final summary block contract; (d) the literal banner text for both reject branches and the brainstorm bold info banner.

## Edge cases

- **Empty title**: gh would never return an empty title for an open issue, but the predicates default to "no match" (return 1) on empty input to avoid false positives that would block legitimate runs.
- **Title with leading whitespace**: list-issues.sh already strips leading whitespace inside the jq filter via `sub("^[[:space:]]+"; "")`. The bash predicates do the same via a one-line pre-pass (`title="${title#"${title%%[![:space:]]*}"}"` — Bash 3.2 compatible). This guarantees jq/bash equivalence.
- **Title with embedded tabs/newlines**: list-issues.sh strips them after the filter via `gsub`. The bash predicates don't need this because `gh issue view --json title` returns a clean string; defensive: the predicates do not require multi-line matching.
- **Case folding on Bash 3.2**: `shopt -s nocasematch` is available; alternatively, use explicit character classes `[Ii]` in the regex. The latter is more portable and is what `LARCH_TITLE_BRAINSTORM_REGEX` uses.
- **Brainstorm followed by colon**: `Brainstorm:` matches because `:` is non-letter. Matches user intent.
- **Brainstorm with no trailing content**: `Brainstorm` (10 chars exactly) — matches because the regex's alternation `([^A-Za-z]|$)` covers end-of-string.
- **Verbal-create path with rejected title**: see `skills/design/SKILL.md` UPDATED — the filter applies at sub-step 2.5 regardless of how `ISSUE_NUMBER` was bound. A user who types `[DESIGNING] foo` as verbal text will get an issue created (via /larch:issue) and then immediately rejected by /design Step 0b — the issue will exist on GitHub with `[DESIGNING]` prefix but no `larch:plan` body. Operator must rename and re-invoke.
- **Combined lifecycle + brainstorm title** (`[DESIGNING] Brainstorm: foo`): per the mandatory ordering, lifecycle-reject short-circuits first; brainstorm auto-enable never fires; the user sees the lifecycle-reject error banner.

## Failure modes

1. **lib-title-eligibility.sh source path resolution fails in list-issues.sh** — the script aborts on `source` failure (`set -euo pipefail` in list-issues.sh). Earliest warning: `make lint` runs the test harness which exercises sourcing from both layout assumptions. Mitigation: adopt the precedent-verified source-path form (per `UPDATED: skills/issue/scripts/list-issues.sh` above) and validate path in the test harness. The harness must cover both invocation from `skills/issue/scripts/` (relative to PWD) and from arbitrary CWD.
2. **jq regex string drifts from bash regex string** — the two grammars are stored as separate constants in the library. Earliest signal: the test harness's jq/bash equivalence assertion fires when a fixture pass/reject diverges. Mitigation: harness asserts equivalence on every PR via `make lint`.
3. **/design Step 0b sub-step ordering regression** — if a future edit reorders sub-step 2.5 before the fetch (sub-step 2), the filter would run with an unset `ISSUE_TITLE` and silently no-match. Earliest signal: `scripts/test-design-structure.sh` gains anchor lines pinning sub-step 2.5 position, predicate ordering, banner text, and the new enum value. Mitigation: explicit pins in that harness (see UPDATED: scripts/test-design-structure.sh).
4. **Final summary block rendering of new outcome** — `render-final-summary.sh` must learn the new `cancelled-title-filter` value or the post-publish render call will fail closed. Earliest signal: `make lint` runs the existing `scripts/test-design-structure.sh` plus the renderer's own contract; both should be extended to cover the new outcome.

## Testing strategy

- New harness `scripts/test-lib-title-eligibility.sh` covers the predicate fixture matrix above plus the jq/bash equivalence assertion.
- Existing harness `skills/issue/scripts/test-list-issues.sh` is re-run unchanged (its DEDUP_SKIP_PREFIX_FILTER behavior must still pass after the refactor).
- Existing harness `scripts/test-design-structure.sh` gains anchor lines per UPDATED section above.
- Existing renderer harness (`scripts/test-render-final-summary.sh` if it exists, or extend an equivalent contract test) covers the new `cancelled-title-filter` outcome rendering.
- Manual smoke test (post-merge): create a throwaway issue titled `[IMPLEMENTING] test`, run `/design --trivial <issue-N>`, confirm the reject banner fires, exit code is 1, and `$DESIGN_TMPDIR` is preserved with the rendered Final summary block.


## Acceptance

Implementation is complete when ALL of the following pass:

1. `scripts/lib-title-eligibility.sh` exists, is sourced cleanly under `set -euo pipefail`, and exports the four documented constants + three documented predicate functions. Sibling `scripts/lib-title-eligibility.md` describes the contract per `.claude/rules/script-md-siblings.md`.
2. `scripts/test-lib-title-eligibility.sh` passes the full fixture matrix (lifecycle-reject hits/misses, report-prefix hits/misses, brainstorm hits/misses) AND the jq/bash equivalence assertion across 12 fixture titles. Wired into `Makefile` via `test-lib-title-eligibility` target.
3. `skills/issue/scripts/list-issues.sh` sources `lib-title-eligibility.sh` (via a precedent-verified pattern) and reads `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` as `DEDUP_SKIP_PREFIX_FILTER`. The inline `select((.title // "" | ascii_downcase ...)` block is replaced. `skills/issue/scripts/test-list-issues.sh` passes unchanged.
4. `skills/design/SKILL.md` Step 0b has a new sub-step **2.5** between sub-steps 2 and 3 that sources the library, runs `title_has_lifecycle_reject_prefix` → `title_has_archival_report_prefix` → `title_starts_with_brainstorm` in that order, exits 1 on either reject (with `SUMMARY_OUTCOME=cancelled-title-filter` and the Final summary block fired), and sets `brainstorm_requested=true` (with a bold info banner) on brainstorm match.
5. `skills/design/SKILL.md` Final summary block contract lists `cancelled-title-filter` in the allowed `SUMMARY_OUTCOME` enum. `skills/design/scripts/render-final-summary.sh` renders the new outcome with a "Refused (title-filter)" mode line.
6. `skills/issue/scripts/add-blocked-by.sh` no longer contains the stale `skills/fix-issue/scripts/find-lock-issue.sh` comment at line 13.
7. `scripts/test-design-structure.sh` pins: (a) sub-step 2.5 prose location, (b) predicate ordering, (c) the new enum value, (d) the literal banner text for both reject branches and the brainstorm info banner.
8. `bash scripts/relevant-checks.sh` passes clean on the branch.
9. Manual smoke test: a throwaway issue titled `[IMPLEMENTING] test` invoked via `/design --trivial <N>` produces the lifecycle-reject banner on stderr, exit code 1, preserves `$DESIGN_TMPDIR`, and emits the Final summary block with `outcome=cancelled-title-filter`.

diff_lines: 280
