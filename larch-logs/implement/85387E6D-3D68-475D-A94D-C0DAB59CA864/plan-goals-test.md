## Goal
Create shared upsert-diagrams-comment.sh helper; move Architecture diagram to /design; /implement keeps only Code Flow; delete compose-architecture-sketch family

## Implementation Plan
## Plan

# Plan — Issue #2840: /design publishes architecture diagram to issue; /implement owns only code flow

Move the architecture-diagram surface so that /design generates and posts it to the GitHub tracking issue (as a `larch:diagrams` summary comment), and /implement stops producing or referencing the architecture diagram entirely. /implement keeps owning the Code Flow diagram and learns to preserve /design's Architecture section when upserting the same comment to add Code Flow.

## Files to modify/create

### NEW: `scripts/upsert-diagrams-comment.sh`

Shared helper that owns the merge-and-upsert logic for the `larch:diagrams` summary comment so /design and /implement do NOT each ship a private copy of the parser.

Synopsis: `upsert-diagrams-comment.sh --issue N [--repo OWNER/REPO] [--architecture-file PATH | --clear-architecture] [--code-flow-file PATH | --clear-code-flow] [--marker '<!-- larch:diagrams v1 -->'] [--dry-run]`.

Behavior:

- Require at least one of `--architecture-file`, `--clear-architecture`, `--code-flow-file`, or `--clear-code-flow`. Modes per section:
  - `--architecture-file PATH` with a non-empty existing file: REPLACE the Architecture section with that file's body.
  - `--clear-architecture`: explicitly REMOVE the Architecture section if present (used by /design Step 5c.5 on the non-architectural-skip path when a prior Architecture section exists — see FINDING_8 rationale).
  - Neither flag and no flag override: PRESERVE any existing Architecture section unchanged.
  - Same three modes for Code Flow with the corresponding flags.
  - Absent or empty `--architecture-file PATH` (file does not exist or has zero bytes) is treated as PRESERVE (NOT clear) — callers MUST use `--clear-architecture` to remove a stale section deliberately. Same convention for Code Flow.
- Fetch the existing comment via a TWO-STEP request to preserve full multiline bodies (FINDING_2): first list comments with `gh api "/repos/$REPO/issues/$ISSUE/comments" --paginate --jq '.[] | (.id|tostring) + "\t" + ((.body // "") | split("\n")[0])'` for marker matching on the first line; then, when exactly one match is found, refetch that comment's full body with `gh api "/repos/$REPO/issues/comments/$COMMENT_ID" --jq '.body // ""'`. This yields a JSON-decoded, byte-faithful body including tabs and embedded newlines.
- Parse the existing body into the `## Architecture Diagram` and `## Code Flow Diagram` sections using an awk state-machine that tracks mermaid-fence depth (```` ```mermaid ```` open, ```` ``` ```` close). H2 lines inside any open fence are NOT treated as section boundaries.
- Compose the new SECTIONS-ONLY body (no marker line) consisting of: blank line if needed, the (provided | preserved) Architecture section, blank line, the (provided | preserved) Code Flow section. Sections that resolve to "cleared" or "absent with no prior" are omitted entirely (no "not available" placeholder). The marker line is supplied to `tracking-issue-summary.sh` via `--marker`, NOT prepended to `--content-file`. This is the **anti-pattern FINDING_1**: never put the marker inside the file passed to `--content-file` because `tracking-issue-summary.sh upsert-summary` always prepends `MARKER + blank line` to the content — passing a marker-prefixed body would produce a duplicate marker line and break exact first-line marker matching on subsequent upserts.
- Pipe the composed body through `scripts/redact-secrets.sh` and `scripts/redact-tmpdir-paths.sh` BEFORE calling `tracking-issue-summary.sh` (defense-in-depth — `tracking-issue-summary.sh` also redacts internally, but redacting the composed file makes the dry-run preview accurate to the published body). Write the redacted sections-only file to a temp path and pass that to `tracking-issue-summary.sh upsert-summary --content-file`.
- `--dry-run`: render TWO previews to stdout — (a) the marker line followed by blank line followed by the sections-only body (this is what the published comment will look like), and (b) the sections-only body alone (this is what `--content-file` would receive). Exit 0 without calling `gh api`.
- Emit standard `lib-quiet.sh` KV on FD 3: `UPSERT_STATUS` (`ok|no-op|failed`), `COMMENT_URL`, `UPDATED` (true/false), `ARCHITECTURE_SOURCE` (`new|preserved|cleared|absent`), `CODE_FLOW_SOURCE` (`new|preserved|cleared|absent`). On `failed`, emit `ERROR` with a short diagnostic.
- Bash 3.2 compatible (no `mapfile`, no associative arrays, no `${var^^}`).

### NEW: `scripts/upsert-diagrams-comment.md`

Sibling contract document. Cover synopsis, callers (Step 5c.5 of /design; Step 7a of /implement), invariants (stable marker is the only marker that intentionally omits `runid=`; comment is issue-scoped, jointly-owned by /design and /implement), the marker-NOT-in-content-file rule (FINDING_1), the two-step full-body fetch contract (FINDING_2), the clear-vs-preserve flag semantics (FINDING_3, FINDING_8), regression harness, and Makefile wiring.

### NEW: `scripts/test-upsert-diagrams-comment.sh`

Offline regression harness. Use the existing `gh` stub patterns from `scripts/test-tracking-issue-summary.sh` to fake API responses; no live network calls. Cover:

- New comment when no prior exists: architecture-only call from /design first; code-flow-only call from /implement first.
- Preserve Architecture when /implement upserts Code Flow over /design's prior comment (byte-faithful match including embedded newlines and tabs).
- Preserve Code Flow when /design upserts Architecture over /implement's prior comment.
- `--clear-architecture` removes the Architecture section while preserving Code Flow (covers FINDING_8 stale-section path).
- `--clear-code-flow` removes the Code Flow section while preserving Architecture.
- Absent/empty `--architecture-file PATH` is treated as PRESERVE, NOT clear (regression guard for FINDING_3).
- Two-step fetch round-trips multiline bodies with tabs and literal `\n` text in mermaid fences (FINDING_2).
- The awk fence state-machine ignores `## Architecture Diagram` and `## Code Flow Diagram` lines inside open ```` ```mermaid ```` ... ```` ``` ```` fences.
- Legacy `<!-- larch:diagrams v1 runid=... -->` comments are NOT matched by the stable marker (left as orphans on the issue).
- `--dry-run` emits the two documented previews and exits 0 without `gh` calls.
- Redaction chain runs on the composed sections-only body BEFORE upsert (planted secret literal disappears from both the dry-run preview and the file passed to `tracking-issue-summary.sh`).
- Duplicate-marker pre-condition (two comments share the stable marker) fails with the same error semantics as `tracking-issue-summary.sh` (paste-d-joined ID list).
- The `--content-file` passed to `tracking-issue-summary.sh` does NOT contain the marker line (FINDING_1 regression guard).

### NEW: `scripts/test-upsert-diagrams-comment.md`

Sibling test contract stub pointing at `scripts/upsert-diagrams-comment.md`.

### UPDATED: `skills/design/SKILL.md`

Add a new sub-step **5c.5** between current items 4 (`plan-block-write`) and the existing item 6 (resolve `REPO`). Specifically:

- Move the existing `REPO` resolution prose (currently item 6) into the new item 5c.5 prologue so the helper has `REPO` available, then re-letter the trailing items. (Alternative: leave item 6 in place and duplicate the resolution into 5c.5; pick whichever produces the smaller, clearer SKILL.md diff.)
- New sub-step body: AFTER `plan-block-write.sh` succeeds, AND when `$DESIGN_TMPDIR/architecture-diagram.md` exists and is non-empty, call `scripts/upsert-diagrams-comment.sh --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"} --architecture-file "$DESIGN_TMPDIR/architecture-diagram.md"`.
- Step 3b non-architectural skip path: when `$DESIGN_TMPDIR/architecture-diagram.md` is absent AND a sentinel `$DESIGN_TMPDIR/architecture-diagram.skipped` exists (Step 3b writes this sentinel on the non-architectural skip; see Step 3b update below), call the helper with `--clear-architecture` instead of skipping. This addresses FINDING_8: re-running /design on the same issue with a now-non-architectural plan removes the stale Architecture section. If neither the file nor the sentinel exists (clean first run on non-architectural feature), skip the helper entirely.
- Capture stdout/stderr; parse `UPSERT_STATUS`. On `failed`, append a `Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md` via `scripts/append-tool-failure.sh` (do NOT roll back the successful `plan-block-write`, do NOT block subsequent publish/rename).
- Print the breadcrumb `> **🔶 /design 5c.5: larch:diagrams (architecture)**` on entry; print a terminal status line `⏩ 5c.5: status=<UPSERT_STATUS> arch=<ARCHITECTURE_SOURCE>`.

Also update the **anti-halt continuation reminder** at the top of `skills/design/SKILL.md` (FINDING_6): the existing chain `5c.1→5c.7→5c.8` must become `5c.1→5c.5→5c.7→5c.8`. Grep the SKILL.md for every transition list that omits 5c.5 and update each.

Adjust the introductory `Pre-publish` / `Post-publish` rationale in Step 5c so the new helper is named in the durable GitHub-write phase enumeration.

### UPDATED: `skills/design/SKILL.md` Step 3b (non-architectural skip sentinel)

When Step 3b classifies the plan as non-architectural and skips diagram generation, write a zero-byte sentinel `$DESIGN_TMPDIR/architecture-diagram.skipped` so Step 5c.5 can distinguish "no diagram was generated this run" from "no diagram surface at all". The sentinel is consumed only by Step 5c.5.

### UPDATED: `scripts/test-design-structure.sh`

Add the new sub-step `5c.5` to the pinned anti-halt sequence grep (FINDING_6). Specifically, the existing literal `5→5a→5b→5c.1→5c.7→5c.8→6` (or whatever the current pinned sequence is — confirm by reading `scripts/test-design-structure.sh` line covering the design-structure step-sequence assertion) must become `5→5a→5b→5c.1→5c.5→5c.7→5c.8→6`. Update any associated check-count constant if the harness expects a fixed number of step labels.

Add an assertion (FINDING_9) that `skills/design/SKILL.md` references `scripts/upsert-diagrams-comment.sh` exactly under the Step 5c.5 sub-section, AFTER the `plan-block-write.sh` mention and BEFORE the `design-log-publish.sh` mention. Use grep with anchor lines to enforce ordering. Also assert the SKILL.md mentions `architecture-diagram.skipped` sentinel handling near Step 3b AND near Step 5c.5.

### UPDATED: `skills/implement/scripts/step-7a.sh`

Refactor the diagrams handling end-to-end:

- Remove `ARCHITECTURE_DIAGRAM_FILE` reads from `compose_summary_diagrams`. The function name and shape may stay, but its output changes: it produces ONLY the Code Flow content. When `generate-code-flow-diagram.sh` reports `STATUS=ok`, write `$IMPLEMENT_TMPDIR/code-flow-section.md` containing the H2 `## Code Flow Diagram` heading plus the diagram body. When `STATUS=skipped` or `STATUS=failed`, **do NOT write `code-flow-section.md`** (FINDING_3): the absence of the file tells `scripts/upsert-diagrams-comment.sh` to preserve any previously valid Code Flow section instead of clobbering it with a placeholder. Operators who want to explicitly remove the Code Flow section can run the helper directly with `--clear-code-flow`.
- Replace the existing `tracking-issue-summary.sh upsert-summary --marker "<!-- larch:diagrams v1 runid=$RUN_ID -->" --content-file ".../summary-diagrams.md"` call with a conditional: when `$IMPLEMENT_TMPDIR/code-flow-section.md` exists, call `scripts/upsert-diagrams-comment.sh --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"} --code-flow-file "$IMPLEMENT_TMPDIR/code-flow-section.md"`. When the file is absent, skip the upsert entirely.
- Map `UPSERT_STATUS=failed` to the existing best-effort-failure log path (preserve current error-handling shape).
- Delete the `summary-diagrams.md` composition path entirely. The helper owns the final composed body.
- Stop touching `ARCHITECTURE_DIAGRAM_FILE` in any branch.

### UPDATED: `skills/implement/scripts/step-7a.md`

Mirror the SKILL.md / script changes: drop references to the run-scoped `<!-- larch:diagrams v1 runid=... -->` marker; document the new shared-marker contract; describe the new `code-flow-section.md` intermediate file (omit on skip/fail — FINDING_3); cite the new shared helper as the upsert dispatcher; update the regression-harness checklist to enumerate the new cases listed under `test-step-7a.sh` below.

### UPDATED: `skills/implement/references/pr-body-template.md`

Drop the `<details><summary>Architecture Diagram</summary>` block and its body entirely. Update the `Composition notes` bullets to reflect that the Architecture Diagram is no longer part of the PR body — point at the tracking-issue `larch:diagrams` comment instead.

### UPDATED: `skills/implement/references/summary-comment-template.md`

Document the stable-marker exception. Specifically:

- Change the listed marker for `larch:diagrams` from the legacy form (with `runid=<R>`) to the stable form (no `runid=`).
- Add a paragraph immediately below the marker block explaining that `larch:diagrams` is the only marker that drops `runid=`: the comment is issue-scoped (not run-scoped) and is jointly written by /design (Architecture) and /implement (Code Flow). All other markers (`metadata`, `plan`, `final-summary`) remain run-scoped.
- Update the "Large runtime payloads" exception paragraph (which already calls out larch:diagrams as embedding diagram bodies) so it is consistent with the new joint-ownership contract.

### UPDATED: `skills/shared/mermaid-safe-content.md`

Update per FINDING_5: remove any references to a `diagrams` larch-log batch (the comment is the only authoritative publish surface now). Document the new issue-scoped `larch:diagrams` helper, the remaining PR Code Flow embed (PR body still has Code Flow, not Architecture), and the redaction/sanitizer boundaries between Step 3b (sanitizer at generation time), Step 5c.5 (redact at publish time), and `tracking-issue-summary.sh` (redacts internally for defense-in-depth).

### UPDATED: `SECURITY.md`

Per FINDING_7 and the repo policy that `SECURITY.md` MUST track security-relevant behavior changes: document `scripts/upsert-diagrams-comment.sh`, `/design` Step 5c.5, the stable issue-scoped `<!-- larch:diagrams v1 -->` marker, and the redaction order (`redact-secrets.sh` + `redact-tmpdir-paths.sh` in the helper; same chain inside `tracking-issue-summary.sh` for defense-in-depth). Note that Architecture diagrams are now posted earlier in the lifecycle (at /design completion) rather than at /implement completion, broadening the public exposure window — reviewers should redact path or symbol mentions in Architecture diagrams the same way they redact them in plan bodies.

### UPDATED: `scripts/ship-pr.sh`

In `run_pr_prep_phase`:

- Delete the `architecture_file` local variable, the `${ARCHITECTURE_DIAGRAM_FILE:-}` read, and the `compose-architecture-sketch.sh` fallback invocation.
- Delete the `<details><summary>Architecture Diagram</summary>` block emission in the PR body composition.
- Keep `code_flow_file` reading and its `<details><summary>Code Flow Diagram</summary>` block unchanged.
- Remove the `architecture` argument from the `sanitize_diagram_or_placeholder` call.

Grep the whole `scripts/ship-pr.sh` for any other architecture-diagram references (state machine, post-merge flush, etc.) and remove them in the same edit.

### UPDATED: `scripts/tracking-issue-read.sh`

In the summary-marker filter case statement, add a new alternative for the stable form `<!-- larch:diagrams v1 -->`. Keep the existing legacy alternative (the form with `runid=<R>`) so orphan comments from prior /implement runs are still skipped from the issue-context dump. Both shapes filter out alongside `metadata`, `plan`, `final-summary`, and the lifecycle markers.

### UPDATED: `skills/implement/SKILL.md`

Update any prose that cites the legacy run-scoped `larch:diagrams` marker shape so it matches the new stable marker. Specifically: the Step 7a prose around marker composition; the prose in the "Summary comments" section that lists the four markers; any cross-references to the diagrams comment shape. Grep for `larch:diagrams v1 runid` across `skills/implement/` and update every prose hit in lockstep.

### UPDATED: `skills/implement/scripts/test-step-7a.sh`

Extend the regression harness with the cases enumerated in the new helper section, plus:

- Stable marker `<!-- larch:diagrams v1 -->` is passed to the upsert call (assert the new shared helper is invoked, not `tracking-issue-summary.sh` directly with a `runid=` marker).
- When a prior `<!-- larch:diagrams v1 -->` comment with Architecture content exists, the next step-7a run preserves the Architecture section byte-for-byte and replaces the Code Flow section.
- When no `larch:diagrams` comment exists yet (no /design run before /implement), step-7a posts a code-flow-only body (no Architecture placeholder).
- When `generate-code-flow-diagram.sh` reports `STATUS=skipped` or `STATUS=failed`, `code-flow-section.md` is NOT written and step-7a skips the helper upsert entirely; any prior Code Flow section on the issue is preserved (regression guard for FINDING_3).
- Legacy `<!-- larch:diagrams v1 runid=... -->` orphan comments do NOT collide with the new stable marker (the helper does NOT delete or edit them; the upsert posts a separate new comment with the stable marker).
- The `ARCHITECTURE_DIAGRAM_FILE` env var has no effect (set it in the test environment and observe identical output).

### UPDATED: `agent-lint.toml`

Per FINDING_4 and FINDING_10. Specifically:

- Remove the `scripts/test-compose-architecture-sketch.sh` and `scripts/test-compose-architecture-sketch.md` entries from the dead-script `[lint]` exclude block (and any sibling allowlist that names them).
- Revise the nearby explanatory comment so it covers only the remaining genuine exclusions (e.g., `compose-pr-summary`) and no longer mentions the now-deleted compose-architecture-sketch family.
- Verify any shard or harness count notes in adjacent comments are still accurate; update `test-harnesses-<N>` references that drift as a result of removing the harness.

### UPDATED: `Makefile`

Wire two new harness targets: `test-upsert-diagrams-comment` and any other added harness names. Follow the existing `test-*` patterns. Remove the `test-compose-architecture-sketch` target alongside the script deletion.

### UPDATED: `docs/run-logs.md`, `docs/configuration-and-permissions.md`, `README.md`, and any other docs that mention the diagrams comment

Grep `docs/` and `README.md` for prose references to the per-run `larch:diagrams` marker shape and update in lockstep. Drift in docs is the single largest repeat-OOS source — the final verification grep enumerated in the "Approach" section explicitly catches stragglers.

### DELETED: `scripts/compose-architecture-sketch.sh`, `scripts/compose-architecture-sketch.md`, `scripts/test-compose-architecture-sketch.sh`, `scripts/test-compose-architecture-sketch.md`

After removing the only caller (ship-pr.sh's `run_pr_prep_phase` fallback), `compose-architecture-sketch.sh` becomes dead code. Delete all four files in the same commit so the orphan-deletion invariant from `KARPATHY_CLAUDE.md` §3 is respected. The post-deletion verification grep (broadened per FINDING_10) is documented in "Approach" below.

## Approach

The change is structurally simple: one new shared helper (`scripts/upsert-diagrams-comment.sh`), three call-site additions/refactors (/design Step 5c.5; /implement step-7a.sh; ship-pr.sh deletions), one marker-shape change in two reader/writer call sites plus all docs that name the marker, and a dead-code deletion of the compose-architecture-sketch family. The dominant complexity sits in (a) the merge-and-preserve logic inside the new helper — especially the two-step fetch for full multiline bodies and the awk fence state-machine — and (b) the doc-prose sweep across every file that currently mentions the per-run diagrams marker.

The helper is the single source of truth for parsing and composing the comment body. /design calls it with `--architecture-file` (or `--clear-architecture` when Step 3b skipped on a re-run with a now-non-architectural plan); /implement calls it with `--code-flow-file` only when generation succeeded (omitted-file means preserve, not clear); either side can re-run idempotently. The helper internally fetches the existing comment via a two-step list-then-fetch pattern that preserves multiline bodies, parses the existing top-level H2 sections with an awk state-machine that tracks mermaid-fence nesting, and composes the new SECTIONS-ONLY body (no marker line). The marker is passed to `tracking-issue-summary.sh` via `--marker` so that helper's mandatory marker-prepending logic produces exactly one marker line.

The shared marker `<!-- larch:diagrams v1 -->` is the load-bearing rollout decision. Existing per-run `<!-- larch:diagrams v1 runid=... -->` comments stay on the issue as orphans. `scripts/tracking-issue-read.sh` keeps both marker shapes in its skip-filter.

Roll the rename and the new helper together as ONE merged change. A staggered rollout would temporarily produce comments with mismatched markers.

Final verification grep (broadened per FINDING_10): `grep -rn 'compose-architecture-sketch\|ARCHITECTURE_DIAGRAM_FILE\|larch:diagrams v1 runid' . --exclude-dir=larch-logs --exclude-dir=.git --exclude-dir=node_modules`. Expected: zero hits OUTSIDE the `tracking-issue-read.sh` legacy-orphan filter line and any docs that explicitly call out the legacy orphan handling. Run this grep before opening the PR and resolve every hit.

## Edge cases

- /design Step 3b skipped (non-architectural plan), no prior comment: Step 5c.5 sees no `architecture-diagram.md` and no prior matching comment; skips the helper entirely.
- /design Step 3b skipped on a re-run after a prior architectural plan: Step 5c.5 sees the `architecture-diagram.skipped` sentinel AND a prior matching comment with an Architecture section; calls helper with `--clear-architecture` to remove the stale section (FINDING_8). Code Flow section (if any) is preserved.
- /implement runs before /design: /implement's helper call finds no `<!-- larch:diagrams v1 -->` comment, posts a code-flow-only body. /design later runs and the helper finds /implement's comment; preserves the Code Flow section while writing the Architecture section.
- /implement's `generate-code-flow-diagram.sh` returns STATUS=skipped or failed: step-7a does NOT write `code-flow-section.md`; helper is not invoked; any prior valid Code Flow section on the issue is preserved (FINDING_3).
- Concurrent /design + /implement upserts: last-writer-wins. Read-merge-patch preserves the loser's content if its section heading is intact in the winning patch's input — which it is, because the winner read after the loser committed. The only failure mode is two writers reading the same baseline and both committing; one section is then lost. Accept the residual risk (matches today's `larch:plan` race semantics; the single-runner invariants further reduce the window).
- Reruns of /design (Already-planned path): /design Step 5c.5 re-upserts; Architecture section is replaced, Code Flow preserved (or cleared on the non-architectural-skip path). Same idempotence for /implement reruns of Code Flow.
- Mermaid fence body containing H2 lines that look like section headings: the awk splitter tracks ```` ```mermaid ``` ```` fence depth and ignores `##` lines inside any open fence. The harness covers this case explicitly.
- Empty architecture-diagram.md (Step 3b candidate sanitizer-rejected and deleted before promotion): file absent; if `architecture-diagram.skipped` sentinel is absent too (sanitizer-rejection is a generation failure path, not the non-architectural-skip path), Step 5c.5 skips the helper entirely. This preserves any prior valid Architecture section from a previous run.
- Comment fetch fails (gh API outage): helper exits `UPSERT_STATUS=failed`; both call sites map to the existing best-effort `Warnings` log path. The plan-block-write succeeded and the rest of Step 5c proceeds.
- Duplicate stable-marker comments (operator error): helper fails with the same error semantics as `tracking-issue-summary.sh`.
- Legacy runid-bearing comment plus a new stable comment coexist on one issue: helper ignores the legacy comment entirely (only matches the exact stable marker). The legacy comment remains as a frozen artifact.

## Failure modes

1. **Section parser confuses mermaid-fence prose for a section heading**, dropping Architecture or Code Flow content silently on the next upsert. Earliest signal: a diffless-looking `gh api PATCH` that nevertheless loses content; CI harness assertion fails the byte-faithful preserve test. Mitigation: the test harness must include at least one comment body where a mermaid fence contains the literal substring `## Code Flow Diagram` so the fence-state-machine is exercised end-to-end.
2. **Marker rollout drift** — one of /design, /implement, `scripts/tracking-issue-read.sh`, docs, or `agent-lint.toml` still references the legacy run-scoped form. Earliest signal: an /implement run after /design produces a SECOND `larch:diagrams` comment (different marker shape) instead of updating the first. Mitigation: ship all marker call-site edits in one commit; run the broadened pre-merge grep (under "Approach"); `make lint` must pass.
3. **Redaction chain regression** — the shared helper bypasses `redact-tmpdir-paths.sh` or `redact-secrets.sh`. Mitigation: the helper calls `tracking-issue-summary.sh upsert-summary` as the final publish step (do NOT re-implement the upsert HTTP path) so the existing internal redaction chain still runs; AND the helper runs the same redact chain itself before passing the file (defense-in-depth, also makes `--dry-run` accurate).

## Testing strategy

- `scripts/test-upsert-diagrams-comment.sh` covers the new helper end-to-end (all cases enumerated under the NEW section).
- `skills/implement/scripts/test-step-7a.sh` covers the call-site refactor (cases enumerated under the UPDATED section).
- `scripts/test-design-structure.sh` covers the SKILL.md anti-halt-chain update AND the Step 5c.5 invocation/ordering pin (FINDING_6, FINDING_9).
- `scripts/test-tracking-issue-summary.sh` smoke-tests the stable marker round-trip through `upsert-summary` (the helper delegates to this script).
- `make lint` and `make lint-foreground` must stay green. The new helper is NOT on the Family B denylist (short read-merge-patch, not a long-running blocker); no breadcrumb-monitor pair is required.

Manual verification on this very issue (#2840) after merge: run `/design` on a follow-up architectural change, observe the `larch:diagrams` comment appearing with only Architecture; subsequent `/implement` run observes Code Flow appended with Architecture preserved.

diff_lines: 750


## Acceptance

- A new helper `scripts/upsert-diagrams-comment.sh` exists with its sibling `.md` contract and offline harness `scripts/test-upsert-diagrams-comment.sh`.
- The helper uses a two-step `gh api` fetch (list, then per-id full body) and an awk fence-aware H2 splitter; multiline Architecture/Code Flow sections round-trip byte-faithfully (regression test for FINDING_2).
- The helper passes a sections-only body to `scripts/tracking-issue-summary.sh upsert-summary` via `--content-file`, with the stable marker `<!-- larch:diagrams v1 -->` supplied only via `--marker` — no duplicate marker line on the published comment (regression test for FINDING_1).
- `--clear-architecture` and `--clear-code-flow` flags remove their respective sections explicitly; absent/empty `--*-file` paths PRESERVE prior sections rather than clearing (regression test for FINDING_3 and FINDING_8).
- /design Step 5c.5 invokes the helper after `plan-block-write.sh` succeeds; on the Step 3b non-architectural-skip path with a prior matching comment, Step 5c.5 calls `--clear-architecture` (FINDING_8). The Step 3b skip path writes a sentinel `architecture-diagram.skipped`.
- /design SKILL.md anti-halt chain and `scripts/test-design-structure.sh` step-sequence pin include `5c.5` so `make lint` stays green (FINDING_6).
- `scripts/test-design-structure.sh` asserts that SKILL.md Step 5c.5 references the helper after `plan-block-write.sh` and before `design-log-publish.sh` (FINDING_9).
- /implement Step 7a's `step-7a.sh` no longer reads `ARCHITECTURE_DIAGRAM_FILE`. It only writes `code-flow-section.md` when generation status is OK; otherwise the file is absent and the helper preserves any prior Code Flow section.
- The `Architecture Diagram` section is removed from `skills/implement/references/pr-body-template.md` and from `scripts/ship-pr.sh`'s `run_pr_prep_phase` PR-body composition.
- `scripts/tracking-issue-read.sh` filters BOTH the stable `<!-- larch:diagrams v1 -->` and the legacy `<!-- larch:diagrams v1 runid=*` -->` markers from the summary skip list.
- `skills/implement/references/summary-comment-template.md`, `skills/shared/mermaid-safe-content.md`, `SECURITY.md`, and any docs that mention the diagrams marker are updated to the stable-marker contract (FINDING_5, FINDING_7).
- `agent-lint.toml` no longer references the deleted `compose-architecture-sketch` family (FINDING_4); shard/harness-count notes updated.
- The four `compose-architecture-sketch.*` files are deleted along with the Makefile target.
- The final pre-merge verification grep `grep -rn 'compose-architecture-sketch\|ARCHITECTURE_DIAGRAM_FILE\|larch:diagrams v1 runid' . --exclude-dir=larch-logs --exclude-dir=.git --exclude-dir=node_modules` returns zero hits OUTSIDE `tracking-issue-read.sh`'s legacy-orphan filter and any docs that explicitly call out the legacy orphan handling (FINDING_10).
- `skills/implement/scripts/test-step-7a.sh` adds the cases enumerated in the plan (stable marker; Architecture preserved; no-prior-comment posts code-flow-only; STATUS=skipped/failed leaves prior Code Flow intact; ARCHITECTURE_DIAGRAM_FILE env var has no effect; legacy orphan comments not collided with).
- `make lint` and `make lint-foreground` are green; the new helper is NOT on the Family B denylist.

diff_lines: 750

## Test plan
(no test plan section in plan-file)
