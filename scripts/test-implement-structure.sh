#!/bin/bash
# Structural regression test for /implement SKILL.md + references/ topology (closes #234).
# Asserts live load-bearing invariants (assertion 5 retired; numbered list runs 1–4, 6–30, with lettered sub-pins) across skills/implement/SKILL.md and the
# reference docs under skills/implement/references/. Complements scripts/test-implement-rebase-macro.sh,
# which owns the Rebase Checkpoint Macro mechanics; this harness owns top-level section
# headings, the MANDATORY ↔ reference-file binding, the focus-area CI-parity check,
# the no-`see Step N below|above` invariant in references/*.md, and (closes #323) the
# three load-bearing marker literals in anchor-template-canonical-body.md (split from
# anchor-comment-template.md per #1627) plus ≥1 references each to
# `anchor-template-canonical-body.md` and `anchor-template-oos-pipeline.md` in SKILL.md,
# and ≥1 `pr-body-template.md` floor in SKILL.md. The cross-skill
# Consumer/Contract/When-to-load header triplet (formerly assertion 8 here, implement-
# scoped) moved to scripts/test-references-headers.sh as of #308 and now applies repo-
# wide to every skills/*/references/*.md. Intentional overlap: assertion (3) (single
# `## Rebase Checkpoint Macro` heading) and assertion (5) (verbosity literals) duplicate
# peer-harness assertions (A) and (D) respectively — accepted duplication per design-
# phase sketch consensus.
#
# Assertion history: assertion 18 added the Protocol Execution Directive pin;
# assertion 19 added the Step 2 external implementer dispatcher pin; assertion
# 20 added the design-manifest + --design-only path pin; assertion 21 added the
# --inline / --subagent forwarding pin, issue #1036; assertion 22 added the
# orchestrator-edit-authority gate pin; assertion 24 added implementer base
# inclusion/generated-marker checks, Gemini structural parity with Cursor's
# shared guardrails, and later OOS triage sub-pins; assertion 25 added the
# clean-main Step 0 entry gate; assertion 26
# added the post-merge anti-halt literal pin, issue #1143; assertion 28 added
# timing instrumentation pins; assertion 29 added the anti-pattern doc-drift
# pin (issue #1512, was #1498); assertion 30 added the Coder simplicity
# override pin (issue #1512, was #1482). Assertion 5 is retired, so the
# numbered list runs 1–4, 6–30; assertion 23 pins Gemini machinery
# preservation, including negative pin 23j against re-introducing
# launch-review.sh --tool gemini.
#  (1) Exactly 1 `^## Load-Bearing Invariants$` heading in skills/implement/SKILL.md.
#  (2) Exactly 1 `^## NEVER List$` heading.
#  (3) Exactly 1 `^## Rebase Checkpoint Macro$` heading.
#  (4) At least 6 `MANDATORY — READ ENTIRE FILE` occurrences (floor, not ceiling),
#      AND each expected reference filename appears on a `MANDATORY —
#      READ ENTIRE FILE` line in SKILL.md (step-to-reference binding from design FINDING_7).
#  (6) CI-parity focus-area enum: at least one line in SKILL.md contains the literal
#      `code-quality / risk-integration / correctness / architecture` AND that same
#      line also contains `security`. Mirrors .github/workflows/ci.yaml L121/L125
#      (agent-sync job's UNQUOTED_FILES check). The single-line same-line pattern
#      prevents a false-pass when the five tokens appear in unrelated prose blocks
#      (e.g., the NEVER List) but the actual Cursor/Codex quick-review prompt strings
#      regress. Design FINDING_2.
#  (7) Expected `skills/implement/references/*.md` files exist with expected names
#      (anchor fragments added per #1627: four new per-step fragment files).
#  (8) Zero occurrences of `see Step N below` / `see Step N above` patterns inside any
#      references/*.md — progressive-disclosure invariant (references must not
#      back-reference parent SKILL.md step numbers with direction words).
#  (9) Load-bearing marker literals split across per-step fragment files per #1627
#      (migrated from anchor-comment-template.md per umbrella #348 Phase 3):
#      (9a) three byte-pinned marker literals must be present in
#      anchor-template-canonical-body.md (`Accepted OOS (GitHub issues filed)`,
#      `| OOS issues filed |`, `<details><summary>Execution Issues</summary>`) —
#      parsed and written at runtime by the Step 9a.1 OOS issue-filing pipeline
#      (anchor's `oos-issues` + `run-statistics` sections) and the Step 11
#      post-execution anchor refresh (anchor's `execution-issues` section).
#      Renaming or removing any marker silently breaks runtime behavior with no
#      other test failure. (9b) SKILL.md must reference `anchor-template-canonical-body.md`
#      at least 1 time (Step 0.5 MANDATORY) AND `anchor-template-oos-pipeline.md`
#      at least 1 time (Step 9a.1 MANDATORY). (9c) SKILL.md must reference
#      `pr-body-template.md` at least 1 time (the MANDATORY pointer at Step 9a).
#      (9d) The canonical Step 9a.1 procedure (now in anchor-template-oos-pipeline.md)
#      must require `--title-prefix "[OOS]"` while keeping `/issue` label flags
#      out of that procedure, and must document `--blocked-by-issue $ISSUE_NUMBER`
#      forwarding only when the tracking issue is resolved and non-degraded.
#      (9e) The same procedure must document conditional
#      `--intra-batch-deps-file` forwarding for Step 9a.1's file-conflict
#      pre-pass.
#      (9f) The same procedure must reference the literal `oos-combined.md`
#      so the combine-pass output path (consumed by `oos-file-conflict-deps.sh`
#      and `/issue --input-file`) cannot regress to a placeholder or split inputs
#      while CI stays green.
#      (9g) The same procedure must pin the per-run OOS issue cap helper,
#      `OOS_ISSUES_PER_RUN_CAP`, the fail-closed warning string, and the
#      skip-step wording so helper-script tests cannot pass after prompt-side
#      integration is accidentally removed.
#      (9h) The same procedure must pin Rule A and Rule B prepend, cascade
#      order, override-independence semantics, worksheet artifact path and
#      contract sub-pins, and sentinel-skip clauses.
# (10) Cross-skill bail-token pin (umbrella #348 Phase 4): skills/implement/SKILL.md
#      must contain the literal `IMPLEMENT_BAIL_REASON=adopted-issue-closed`.
#      `/fix-issue` Step 6a scans this token in captured `/implement` output to
#      branch to a specific warning + skip-to-cleanup path; the token literal
#      is simultaneously pinned in skills/fix-issue/SKILL.md by
#      skills/fix-issue/scripts/test-fix-issue-bail-detection.sh. A rename of
#      the token is therefore a dual-repo change caught by CI.
# (11) Phase 5 (umbrella #348) rebase-rebump-subprocedure.md reference set.
#      Sub-procedure step 6 retargeted from PR-body refresh to anchor
#      `version-bump-reasoning` refresh:
#      (11a) references `anchor-comment-template.md` ≥1 (Contract citation).
#      (11b) references `tracking-issue-read.sh --sentinel` ≥1 (Step 6a).
#      (11c) references `assemble-anchor.sh` ≥1 AND `upsert-anchor` ≥1 (Step 6d,e).
#      (11d) zero invocation lines of `${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-read.sh`
#            or `${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-update.sh` — scoped to
#            invocation patterns to preserve historical/prose mentions (per
#            design FINDING_7). A lingering invocation is a Phase 5 regression.
# (12) Phase 5 single-source-of-truth invariant for SECTION_MARKERS:
#      (12a) tracking-issue-write.sh must reference `anchor-section-markers.sh`
#            (the shared source-of-truth helper).
#      (12b) tracking-issue-write.sh must NOT contain a standalone
#            `SECTION_MARKERS=(` declaration — any re-inline would silently
#            diverge its ordering from assemble-anchor.sh.
# (13) Orchestrator-judgment-bail invariant (closes #553): two byte-pinned
#      anchor literals must be present in skills/implement/SKILL.md so future
#      edits cannot silently delete the rule — the headline of NEVER #7 and the
#      headline of the Step 2 "scope-lock" cue. Mirrors the byte-pin pattern of
#      assertion (5).
# (14) Step 0.5 Branch 2/3 anchor-lookup contract (closes #654): SKILL.md
#      must invoke `tracking-issue-write.sh find-anchor` for the marker probe
#      AND must NOT contain the legacy non-paginated inline pattern
#      `gh api ... /comments --jq ... | head -1` for that probe. The legacy
#      pattern (Branch 2 line 267, Branch 3 line 316 pre-fix) silently missed
#      anchors past the first page of issue comments and silently picked one
#      anchor when multiple existed, corrupting the canonical state. The
#      paginated, multi-anchor-fail-closed `find-anchor` subcommand replaces
#      that pattern. Both find-anchor invocations (Branch 2: --issue
#      "$ISSUE_ARG"; Branch 3: --issue "$RECOVERED_N") must be present so a
#      future edit reverting either branch to the buggy pattern would
#      regress #654 silently against the unit-test harness alone — this
#      assertion is the structural pin.
# (15) Substantive-validation flag pin (closes #661): the Step 5 quick-mode
#      collect-agent-results.sh invocation in SKILL.md must carry both
#      --substantive-validation AND --validation-mode on the same line as
#      --timeout 1860 so banner-only reviewer output (e.g., "Authentication
#      required") is rejected as STATUS=NOT_SUBSTANTIVE rather than passing
#      as STATUS=OK. SKILL.md only contains the Step 5 quick-mode
#      collect-agent-results.sh invocation (the dialectic-execution and
#      adjudication invocations live in sibling skill references, not in
#      this SKILL.md), so the assertion is unambiguous. A future edit that
#      drops either flag, or splits the invocation across lines, fails
#      closed under `set -o pipefail`.
# (16) Cross-skill plan-heading drift-prevention pin (closes #749): the
#      `plan-goals-test` anchor fragment composed by /implement Step 1
#      must agree with /design's emitted plan heading. /design Step 2b
#      prints under `## Implementation Plan` (and plan-review.md prints
#      `## Revised Implementation Plan` when superseded). The legacy
#      consumer instruction at SKILL.md:510 directed composition from
#      `## Goal` and `## Test plan` sections — headings /design never
#      emitted — so the fragment was structurally non-extractable.
#      (16a) Producer pin: skills/design/SKILL.md contains `## Implementation Plan`;
#            skills/design/references/plan-review.md contains `## Revised Implementation Plan`.
#      (16b) Consumer positive pin (scoped): the line range from `### Anchor-section fragments`
#            to the next `### ` heading in skills/implement/SKILL.md must contain
#            `## Implementation Plan` — scoping isolates the rewritten line 510
#            from the unrelated quick-mode `## Implementation Plan` reference at
#            skills/implement/SKILL.md:480 (Step 1 quick-mode "Inline design"),
#            which would false-pass a whole-file grep.
#      (16c) Anchor-template positive pin: skills/implement/references/anchor-comment-template.md
#            placeholder prose references `## Implementation Plan` (synthesis source).
#      (16d) Negative pin (broken-pattern): the contiguous legacy phrase
#            `` `/design`'s `## Goal` and `## Test plan` sections `` (with single
#            backticks as it actually appeared in pre-fix SKILL.md:510) MUST NOT
#            appear in skills/implement/SKILL.md. Implementation is a single fixed-string
#            grep against the full phrase (NOT two independent same-line checks);
#            the rewritten line 510 drops the contiguous substring while preserving
#            `## Goal` and `## Test plan` separately as the anchor body's rendered
#            target headings, so this negative pin fails closed on broken main and
#            passes on the fixed branch.
# (26) Post-merge anti-halt literal pin (issue #1143): SKILL.md must retain
#      the NEVER #7 post-merge sub-clause, Step 12a ACTION=already_merged
#      continuation reminder, and Step 12b post-merge blockquote opener so
#      the merge breadcrumb cannot silently become a terminal boundary before
#      Steps 14, 15, 16, 17, 18 run.
#
# Exit 0 on pass, exit 1 on any assertion failure.
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/implement/references"

expected_refs=(
  "anchor-template-canonical-body.md"
  "anchor-template-execution-issues.md"
  "anchor-template-oos-pipeline.md"
  "anchor-template-quick-mode.md"
  "bump-verification.md"
  "codex-manifest-schema.md"
  "conflict-resolution.md"
  "pr-body-template.md"
  "rebase-rebump-subprocedure.md"
)

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing: $SKILL_MD"
[[ -d "$REFS_DIR" ]] || fail "skills/implement/references/ missing: $REFS_DIR"

# ---------------------------------------------------------------------------
# (1) Exactly one `^## Load-Bearing Invariants$` heading.
# ---------------------------------------------------------------------------
count=$(grep -c '^## Load-Bearing Invariants$' "$SKILL_MD" || true)
[[ "$count" == "1" ]] \
  || fail "(1) expected exactly 1 '^## Load-Bearing Invariants$' heading in SKILL.md, found $count"

# ---------------------------------------------------------------------------
# (2) Exactly one `^## NEVER List$` heading.
# ---------------------------------------------------------------------------
count=$(grep -c '^## NEVER List$' "$SKILL_MD" || true)
[[ "$count" == "1" ]] \
  || fail "(2) expected exactly 1 '^## NEVER List$' heading in SKILL.md, found $count"

# ---------------------------------------------------------------------------
# (3) Exactly one `^## Rebase Checkpoint Macro$` heading.
# ---------------------------------------------------------------------------
count=$(grep -c '^## Rebase Checkpoint Macro$' "$SKILL_MD" || true)
[[ "$count" == "1" ]] \
  || fail "(3) expected exactly 1 '^## Rebase Checkpoint Macro$' heading in SKILL.md, found $count"

# ---------------------------------------------------------------------------
# (4) MANDATORY — READ ENTIRE FILE: at least 6 occurrences AND each expected
#     reference filename appears on a MANDATORY line (step-to-reference binding).
# ---------------------------------------------------------------------------
# Use `|| true` to keep set -e + pipefail from aborting before the fail() diagnostic
# when there are zero matches (grep -o exits 1 on no match, which propagates via pipefail).
occurrences=$(grep -o 'MANDATORY — READ ENTIRE FILE' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ' || true)
if ! [[ "$occurrences" =~ ^[0-9]+$ ]] || (( occurrences < 6 )); then
  fail "(4) expected at least 6 'MANDATORY — READ ENTIRE FILE' occurrences in SKILL.md, found ${occurrences:-0}"
fi

# Step-to-reference binding: each expected reference filename must appear on a
# MANDATORY line in SKILL.md. Isolate MANDATORY lines first, then do a fixed-string
# match against the filename so `.` in the filename is treated literally (not as ERE
# "any character", which would false-pass on corrupted pointers like `pr-body-templateXmd`).
mandatory_lines=$(grep 'MANDATORY — READ ENTIRE FILE' "$SKILL_MD" || true)
for ref in "${expected_refs[@]}"; do
  printf '%s\n' "$mandatory_lines" | grep -Fq "$ref" \
    || fail "(4) no 'MANDATORY — READ ENTIRE FILE' line in SKILL.md references '$ref' — step-to-reference binding broken"
done

# ---------------------------------------------------------------------------
# (6) CI-parity focus-area enum check.
#     .github/workflows/ci.yaml L121/L125 (agent-sync job's UNQUOTED_FILES loop):
#       grep -n 'code-quality / risk-integration / correctness / architecture' "$f"
#       then checks that each matching line also contains 'security'.
#     Mirror that here: at least one line must match the enum AND contain 'security'.
# ---------------------------------------------------------------------------
enum_hits=$(grep -n 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" || true)
[[ -n "$enum_hits" ]] \
  || fail "(6) SKILL.md lacks the unquoted slash-separated focus-area enum ('code-quality / risk-integration / correctness / architecture') — CI's agent-sync guard would fail"

# Mirror CI's per-line enforcement: fail immediately on ANY enum line that lacks
# 'security'. The CI loop at .github/workflows/ci.yaml L122-129 iterates every hit
# and fails if any lacks 'security'. A simple "first match wins" here would silently
# allow a future enum line without 'security' to pass the harness while CI fails.
while IFS= read -r hit; do
  [[ -z "$hit" ]] && continue
  line_text="${hit#*:}"
  if ! printf '%s\n' "$line_text" | grep -q 'security'; then
    fail "(6) focus-area enum line lacks 'security' on same line — CI's agent-sync guard would fail: $line_text"
  fi
done <<< "$enum_hits"

# ---------------------------------------------------------------------------
# (7) Expected references/*.md files exist (anchor fragments added per #1627).
# ---------------------------------------------------------------------------
for ref in "${expected_refs[@]}"; do
  [[ -f "$REFS_DIR/$ref" ]] \
    || fail "(7) expected reference file missing: skills/implement/references/$ref"
done

# ---------------------------------------------------------------------------
# (8) Zero 'see Step N below' / 'see Step N above' patterns in any references/*.md.
#     Pattern is narrow: requires both a step number AND a direction word (below|above).
#     Permits legitimate cross-refs like 'see Step 8' with no direction word.
#     Case-insensitive: catches sentence-initial 'See Step 8 below' variants.
#     The step-number token is `[0-9][0-9a-z.]*` so bare digits (`8`), letter-suffix
#     forms (`9a`), and dotted substep forms (`9a.1`, `3c.2`) are all caught — matching
#     /implement's dotted substep numbering (closes #253).
#     Scans every *.md under references/ (not just the five expected refs) so new
#     reference files added in the future are covered automatically — the contract
#     documented in the header and scripts/test-implement-structure.md (sibling contract) covers "references/*.md" generally.
#     Cross-skill Consumer/Contract/When-to-load header-triplet invariant lives in
#     scripts/test-references-headers.sh as of #308, not here.
# ---------------------------------------------------------------------------
shopt -s nullglob
ref_files=( "$REFS_DIR"/*.md )
shopt -u nullglob
[[ "${#ref_files[@]}" -gt 0 ]] \
  || fail "(8) no .md files found under $REFS_DIR — cannot validate the 'see Step N below|above' invariant"

match_files=""
for ref_path in "${ref_files[@]}"; do
  if grep -qiE 'see Step [0-9][0-9a-z.]* (below|above)' "$ref_path"; then
    match_files="$match_files $(basename "$ref_path")"
  fi
done
if [[ -n "$match_files" ]]; then
  fail "(8) found forbidden 'see Step N below|above' patterns (case-insensitive) in:$match_files"
fi

# ---------------------------------------------------------------------------
# (9a) Three load-bearing marker literals must appear at least once in
#      skills/implement/references/anchor-template-canonical-body.md (split
#      from anchor-comment-template.md per #1627). Step 9a.1 (OOS
#      issue-filing pipeline) parses and rewrites the OOS placeholder and the
#      Run Statistics OOS cell in the anchor's `oos-issues` + `run-statistics`
#      sections; Step 11 (post-execution anchor refresh) locates and rewrites
#      the Execution Issues details block in the anchor's `execution-issues`
#      section. A future rename or removal in anchor-template-canonical-body.md
#      silently breaks runtime behavior with no other test failure. Use
#      fixed-string matching since the literals contain regex metachars.
# ---------------------------------------------------------------------------
ANCHOR_TEMPLATE="$REFS_DIR/anchor-template-canonical-body.md"
anchor_markers=(
  'Accepted OOS (GitHub issues filed)'
  '| OOS issues filed |'
  '<details><summary>Execution Issues</summary>'
)
for marker in "${anchor_markers[@]}"; do
  grep -Fq "$marker" "$ANCHOR_TEMPLATE" \
    || fail "(9a) anchor-template-canonical-body.md lost load-bearing marker literal: $marker"
done

# ---------------------------------------------------------------------------
# (9b) skills/implement/SKILL.md must reference `anchor-template-canonical-body.md`
#      at least 1 time (Step 0.5 MANDATORY) AND `anchor-template-oos-pipeline.md`
#      at least 1 time (Step 9a.1 MANDATORY). These replace the old monolithic
#      anchor-comment-template.md requirement (split per #1627). Assertion (4)
#      already checks the MANDATORY lines exist; this guards against a future
#      edit that orphans Steps 0.5 or 9a.1 from the extracted fragments.
#      Use fixed-string matching so the `.` in the filename is literal.
# ---------------------------------------------------------------------------
canonical_body_refs=$(grep -cF 'anchor-template-canonical-body.md' "$SKILL_MD" || true)
if ! [[ "$canonical_body_refs" =~ ^[0-9]+$ ]] || (( canonical_body_refs < 1 )); then
  fail "(9b) expected at least 1 reference to 'anchor-template-canonical-body.md' in SKILL.md (Step 0.5 MANDATORY), found ${canonical_body_refs:-0}"
fi
oos_pipeline_refs=$(grep -cF 'anchor-template-oos-pipeline.md' "$SKILL_MD" || true)
if ! [[ "$oos_pipeline_refs" =~ ^[0-9]+$ ]] || (( oos_pipeline_refs < 1 )); then
  fail "(9b) expected at least 1 reference to 'anchor-template-oos-pipeline.md' in SKILL.md (Step 9a.1 MANDATORY), found ${oos_pipeline_refs:-0}"
fi

# ---------------------------------------------------------------------------
# (9c) skills/implement/SKILL.md must reference `pr-body-template.md` at
#      least 1 time — the MANDATORY pointer at Step 9a. Lower floor than
#      pre-Phase-3 (was >=3) since rich report content moved to
#      anchor-comment-template.md. Use fixed-string matching.
# ---------------------------------------------------------------------------
pr_body_refs=$(grep -cF 'pr-body-template.md' "$SKILL_MD" || true)
if ! [[ "$pr_body_refs" =~ ^[0-9]+$ ]] || (( pr_body_refs < 1 )); then
  fail "(9c) expected at least 1 reference to 'pr-body-template.md' in SKILL.md (Step 9a MANDATORY pointer), found ${pr_body_refs:-0}"
fi

# ---------------------------------------------------------------------------
# (9d) Step 9a.1 OOS issue-filing flag contract. Scope to the canonical
#      procedure section only (now in anchor-template-oos-pipeline.md per #1627):
#      it must require the `[OOS]` title prefix on the `/issue` batch invocation,
#      must not contain any label flag token, and must document
#      `--blocked-by-issue $ISSUE_NUMBER` forwarding only when `$ISSUE_NUMBER` is
#      set, `deferred=false`, and `repo_unavailable=false`, with an explicit
#      degraded-mode skip rule. This prevents the OOS pipeline from regressing to
#      unlabeled-title output, from triggering label-not-found warnings in
#      consumer repos, or from silently dropping the tracking-issue native
#      blocking edge in the resolved-tracking-issue path.
# ---------------------------------------------------------------------------
OOS_PIPELINE_TEMPLATE="$REFS_DIR/anchor-template-oos-pipeline.md"
[[ -f "$OOS_PIPELINE_TEMPLATE" ]] \
  || fail "(9d) anchor-template-oos-pipeline.md missing: $OOS_PIPELINE_TEMPLATE"

step_9a1_oos_procedure=$(awk '
  /^## Step 9a\.1 OOS pipeline procedure/ { flag=1; next }
  /^## / { flag=0 }
  flag { print }
' "$OOS_PIPELINE_TEMPLATE")

[[ -n "$step_9a1_oos_procedure" ]] \
  || fail "(9d) could not extract Step 9a.1 OOS pipeline procedure section from anchor-template-oos-pipeline.md"
# Sentinel: catch silent slice truncation when a future PR inserts a new
# "## " heading inside Step 9a.1. Without this guard the awk slice would
# shrink and the (9d)-(9h) literal pins below would fail in opaque ways.
# The current section is ~13KB; 4000 bytes is well above any plausible
# truncation slice and well below normal evolution.
extracted_bytes=$(printf '%s' "$step_9a1_oos_procedure" | wc -c | tr -d ' ')
(( extracted_bytes >= 4000 )) \
  || fail "(9d) extracted slice suspiciously short (${extracted_bytes} bytes) — has a new ## heading been inserted inside Step 9a.1 of anchor-template-oos-pipeline.md?"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '--title-prefix "[OOS]"' \
  || fail "(9d) Step 9a.1 OOS pipeline procedure must require '/issue --title-prefix \"[OOS]\"'"
if printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '--label'; then
  fail "(9d) Step 9a.1 OOS pipeline procedure must not pass a /issue label flag; use the '[OOS]' title prefix instead"
fi
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '--blocked-by-issue $ISSUE_NUMBER' \
  || fail "(9d) Step 9a.1 OOS pipeline procedure must document '/issue --blocked-by-issue \$ISSUE_NUMBER' forwarding"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'When `$ISSUE_NUMBER` is non-empty AND `deferred=false` AND `repo_unavailable=false`' \
  || fail "(9d) Step 9a.1 OOS pipeline procedure must gate blocked-by forwarding on ISSUE_NUMBER + deferred=false + repo_unavailable=false"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'In any of the three degraded modes' \
  || fail "(9d) Step 9a.1 OOS pipeline procedure must document the degraded-mode blocked-by skip rule"

# ---------------------------------------------------------------------------
# (9e) Step 9a.1 file-conflict pre-pass forwarding contract. Scope to the
#      canonical procedure section only and pin the literal
#      `--intra-batch-deps-file` token. The helper may emit a TSV only when
#      accepted OOS items likely modify the same file; when it does, /implement
#      must forward that TSV through /issue's existing caller-supplied edge
#      channel so the rows merge with Phase 2 deps and pass through validation,
#      DUPLICATE override, and SCC cycle resolution.
# ---------------------------------------------------------------------------
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '--intra-batch-deps-file' \
  || fail "(9e) Step 9a.1 OOS pipeline procedure must document conditional '--intra-batch-deps-file' forwarding"

# ---------------------------------------------------------------------------
# (9e.1) Step 9a.1 file-conflict dep-edge gating. When the file-conflict pre-pass
#        exits 0 with a non-empty TSV, the procedure forwards --intra-batch-deps-file
#        to /issue; Phase-2 LLM dep-analysis still runs for semantic deps between
#        non-conflicting entries (the pre-pass supplies only same-file conflict edges).
#        --no-dep-llm must NOT be forwarded based on OOS_FILE_CONFLICT_COMPLETE alone.
#        Pin both flag name and the OOS_FILE_CONFLICT_COMPLETE gating variable.
# ---------------------------------------------------------------------------
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '--no-dep-llm' \
  || fail "(9e.1) Step 9a.1 OOS pipeline procedure must document '--no-dep-llm' forwarding"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'OOS_FILE_CONFLICT_COMPLETE' \
  || fail "(9e.1) Step 9a.1 OOS pipeline procedure must document 'OOS_FILE_CONFLICT_COMPLETE' gating condition"

# ---------------------------------------------------------------------------
# (9f) Step 9a.1 combine-pass output path. Pin the literal `oos-combined.md`
#      inside the canonical procedure so a future edit cannot rename or drop
#      the combine-pass output path (consumed by `oos-file-conflict-deps.sh`
#      and `/issue --input-file`) without CI catching the drift.
# ---------------------------------------------------------------------------
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'oos-combined.md' \
  || fail "(9f) Step 9a.1 OOS pipeline procedure must reference the literal 'oos-combined.md' (combine-pass output path)"

# ---------------------------------------------------------------------------
# (9g) Step 9a.1 per-run OOS issue cap integration. The cap is enforced by
#      prompt-side orchestration around a helper, so pin the key literals in
#      anchor-comment-template.md: helper path, env var, fail-closed warning,
#      and skip-step wording.
# ---------------------------------------------------------------------------
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'oos-issue-cap.sh' \
  || fail "(9g) Step 9a.1 OOS pipeline procedure must invoke oos-issue-cap.sh"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'OOS_ISSUES_PER_RUN_CAP' \
  || fail "(9g) Step 9a.1 OOS pipeline procedure must document OOS_ISSUES_PER_RUN_CAP"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- '**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**' \
  || fail "(9g) Step 9a.1 OOS pipeline procedure must retain the oos-issue-cap fail-closed warning string"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'SKIP step 3.5 and step 4' \
  || fail "(9g) Step 9a.1 OOS pipeline procedure must document skipping step 3.5 and step 4 on cap helper failure"

# ---------------------------------------------------------------------------
# (9h) Step 9a.1 aggressive OOS combine cascade. Rules A/B are prompt-side
#      orchestration policy, so pin the load-bearing literals in the canonical
#      procedure: prepend order, hard-combine overrides, worksheet path and
#      worksheet contract, sentinel recovery skip, and Rule B's singleton
#      predicate.
# ---------------------------------------------------------------------------
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rule A — same logical concern' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document Rule A same logical concern"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rule B — leaked SIMPLE entries' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document Rule B leaked SIMPLE entries"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rule A is HARD COMBINE: it OVERRIDES' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document Rule A hard-combine override"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rule B is HARD COMBINE: same independence-override semantics as Rule A' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document Rule B hard-combine override"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rule A -> Rule B -> existing criteria 1-4' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document the Rule A/B cascade order"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'oos-grouping-worksheet.md' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document the grouping worksheet path"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Rules A and B as well as criteria 1-6' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document sentinel recovery skipping Rules A/B and criteria 1-6"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'sentinel branch does NOT write' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document sentinel recovery skipping worksheet writes"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Every input INPUT_' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document every worksheet input exactly once"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'g-singleton-' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document singleton group IDs"
printf '%s\n' "$step_9a1_oos_procedure" | grep -Fq -- 'Let S be the set of entries that remained as singleton' \
  || fail "(9h) Step 9a.1 OOS pipeline procedure must document Rule B singleton predicate"

# ---------------------------------------------------------------------------
# (10) Cross-skill bail-token pin (umbrella #348 Phase 4): SKILL.md must
#      contain the literal `IMPLEMENT_BAIL_REASON=adopted-issue-closed`.
#      `/implement` Step 0.5 Branch 2 emits this token on stdout when the
#      adopted tracking issue is CLOSED; `/fix-issue` Step 6a greps captured
#      output for it. Paired assertion on the consumer side lives in
#      skills/fix-issue/scripts/test-fix-issue-bail-detection.sh. Use
#      fixed-string matching since the literal contains `=`.
# ---------------------------------------------------------------------------
grep -Fq 'IMPLEMENT_BAIL_REASON=adopted-issue-closed' "$SKILL_MD" \
  || fail "(10) skills/implement/SKILL.md must contain the cross-skill bail token literal 'IMPLEMENT_BAIL_REASON=adopted-issue-closed'"

# ---------------------------------------------------------------------------
# (11) Phase 5 (umbrella #348) rebase-rebump-subprocedure.md reference set.
#      Sub-procedure step 6 retargeted from PR-body refresh to anchor
#      `version-bump-reasoning` refresh (via tracking-issue sentinel read +
#      assemble-anchor.sh + upsert-anchor). Assertions:
#      (11a) references anchor-comment-template.md ≥1 (Contract citation).
#      (11b) references `tracking-issue-read.sh --sentinel` ≥1 (Step 6a).
#      (11c) references `assemble-anchor.sh` ≥1 AND `upsert-anchor` ≥1 (Step 6d,e).
#      (11d) zero invocation lines of `gh-pr-body-read.sh` or `gh-pr-body-update.sh`
#            — scoped to invocation patterns (the literal
#            `${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-{read,update}.sh`) to
#            preserve historical/prose mentions if any remain (per design
#            FINDING_7). A lingering invocation is a Phase 5 regression.
# ---------------------------------------------------------------------------
REBASE_SUBPROC="$REFS_DIR/rebase-rebump-subprocedure.md"
[[ -f "$REBASE_SUBPROC" ]] || fail "(11) rebase-rebump-subprocedure.md missing: $REBASE_SUBPROC"

anchor_template_refs=$(grep -cF 'anchor-comment-template.md' "$REBASE_SUBPROC" || true)
if ! [[ "$anchor_template_refs" =~ ^[0-9]+$ ]] || (( anchor_template_refs < 1 )); then
  fail "(11a) expected at least 1 reference to 'anchor-comment-template.md' in rebase-rebump-subprocedure.md (Contract citation), found ${anchor_template_refs:-0}"
fi

sentinel_refs=$(grep -cF 'tracking-issue-read.sh --sentinel' "$REBASE_SUBPROC" || true)
if ! [[ "$sentinel_refs" =~ ^[0-9]+$ ]] || (( sentinel_refs < 1 )); then
  fail "(11b) expected at least 1 reference to 'tracking-issue-read.sh --sentinel' in rebase-rebump-subprocedure.md (Step 6a), found ${sentinel_refs:-0}"
fi

assemble_refs=$(grep -cF 'assemble-anchor.sh' "$REBASE_SUBPROC" || true)
refresh_refs=$(grep -cF 'refresh-anchor.sh' "$REBASE_SUBPROC" || true)
if ! [[ "$assemble_refs" =~ ^[0-9]+$ ]]; then assemble_refs=0; fi
if ! [[ "$refresh_refs" =~ ^[0-9]+$ ]]; then refresh_refs=0; fi
if (( assemble_refs + refresh_refs < 1 )); then
  fail "(11c-1) expected at least 1 reference to 'assemble-anchor.sh' or 'refresh-anchor.sh' in rebase-rebump-subprocedure.md (Step 6d), found ${assemble_refs}+${refresh_refs}"
fi

upsert_refs=$(grep -cF 'upsert-anchor' "$REBASE_SUBPROC" || true)
if ! [[ "$upsert_refs" =~ ^[0-9]+$ ]]; then upsert_refs=0; fi
if (( upsert_refs + refresh_refs < 1 )); then
  fail "(11c-2) expected at least 1 reference to 'upsert-anchor' or 'refresh-anchor.sh' in rebase-rebump-subprocedure.md (Step 6e), found ${upsert_refs}+${refresh_refs}"
fi

# (11d) No remaining invocation patterns. Match the literal
# `${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-read.sh` or `…/gh-pr-body-update.sh`
# only — historical prose mentions (e.g., "replaced the old gh-pr-body-*.sh")
# are allowed.
gh_pr_body_read_invocations=$(grep -cF '${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-read.sh' "$REBASE_SUBPROC" || true)
if ! [[ "$gh_pr_body_read_invocations" =~ ^[0-9]+$ ]] || (( gh_pr_body_read_invocations > 0 )); then
  fail "(11d-1) rebase-rebump-subprocedure.md still invokes 'gh-pr-body-read.sh' (found ${gh_pr_body_read_invocations:-0}); Phase 5 retargeted to assemble-anchor.sh + upsert-anchor"
fi
gh_pr_body_update_invocations=$(grep -cF '${CLAUDE_PLUGIN_ROOT}/scripts/gh-pr-body-update.sh' "$REBASE_SUBPROC" || true)
if ! [[ "$gh_pr_body_update_invocations" =~ ^[0-9]+$ ]] || (( gh_pr_body_update_invocations > 0 )); then
  fail "(11d-2) rebase-rebump-subprocedure.md still invokes 'gh-pr-body-update.sh' (found ${gh_pr_body_update_invocations:-0}); Phase 5 retargeted to assemble-anchor.sh + upsert-anchor"
fi

# ---------------------------------------------------------------------------
# (12) Phase 5 single-source-of-truth invariant for SECTION_MARKERS.
#      tracking-issue-write.sh must source anchor-section-markers.sh and
#      must NOT contain a standalone `SECTION_MARKERS=(` declaration
#      (the old inline declaration was removed; any re-inline would silently
#      diverge tracking-issue-write.sh's ordering from assemble-anchor.sh).
# ---------------------------------------------------------------------------
TRACKING_WRITE_SH="$REPO_ROOT/scripts/tracking-issue-write.sh"
[[ -f "$TRACKING_WRITE_SH" ]] || fail "(12) tracking-issue-write.sh missing: $TRACKING_WRITE_SH"

markers_sourced=$(grep -cF 'anchor-section-markers.sh' "$TRACKING_WRITE_SH" || true)
if ! [[ "$markers_sourced" =~ ^[0-9]+$ ]] || (( markers_sourced < 1 )); then
  fail "(12a) tracking-issue-write.sh must reference 'anchor-section-markers.sh' (source-of-truth helper); found ${markers_sourced:-0}"
fi

inline_markers=$(grep -cE '^[[:space:]]*SECTION_MARKERS=\(' "$TRACKING_WRITE_SH" || true)
if ! [[ "$inline_markers" =~ ^[0-9]+$ ]] || (( inline_markers > 0 )); then
  fail "(12b) tracking-issue-write.sh must NOT contain a standalone 'SECTION_MARKERS=(' declaration (now lives in anchor-section-markers.sh); found ${inline_markers:-0}"
fi

# ---------------------------------------------------------------------------
# (13) Orchestrator-judgment-bail invariant (closes #553): two byte-pinned
#      anchor literals must be present in skills/implement/SKILL.md so future
#      edits cannot silently delete the rule. The two literals are the
#      headline of NEVER #7 and the headline of the Step 2 "scope-lock" cue.
#      Both literals are byte-unique within SKILL.md by construction (each is
#      a distinctive headline), so the whole-file fixed-string check is
#      sufficient — this assertion guards against deletion, not against
#      relocation. Mirrors the pattern of assertion (5)'s verbosity literal
#      list.
# ---------------------------------------------------------------------------
never7_literals=(
  'NEVER bail mid-run on orchestrator-judgment "scope" or "capacity" concerns without a mechanical justification.'
  '**No mid-run scope re-litigation.**'
)
for lit in "${never7_literals[@]}"; do
  grep -Fq "$lit" "$SKILL_MD" \
    || fail "(13) SKILL.md lost orchestrator-judgment-bail invariant literal: $lit"
done

# ---------------------------------------------------------------------------
# (14) Step 0.5 Branch 2/3 anchor-lookup contract pin (closes #654).
#      Positive: both find-anchor invocations must be present in SKILL.md
#      (Branch 2: --issue "$ISSUE_ARG"; Branch 3: --issue "$RECOVERED_N").
#      Negative: the legacy non-paginated inline pattern
#      `gh api .../issues/<var>/comments` followed by a jq pipeline ending
#      in `head -1` must NOT be present in SKILL.md — that pattern was the
#      source of #654 and any future revert would silently re-introduce
#      the silent-data-loss path.
# ---------------------------------------------------------------------------
fa_branch2=$(grep -cF 'tracking-issue-write.sh find-anchor --issue "$ISSUE_ARG"' "$SKILL_MD" || true)
if ! [[ "$fa_branch2" =~ ^[0-9]+$ ]] || (( fa_branch2 < 1 )); then
  fail "(14) SKILL.md missing Branch 2 find-anchor invocation 'tracking-issue-write.sh find-anchor --issue \"\$ISSUE_ARG\"' (closes #654)"
fi
fa_branch3=$(grep -cF 'tracking-issue-write.sh find-anchor --issue "$RECOVERED_N"' "$SKILL_MD" || true)
if ! [[ "$fa_branch3" =~ ^[0-9]+$ ]] || (( fa_branch3 < 1 )); then
  fail "(14) SKILL.md missing Branch 3 find-anchor invocation 'tracking-issue-write.sh find-anchor --issue \"\$RECOVERED_N\"' (closes #654)"
fi
# Negative pin: the legacy non-paginated lookup pattern must be gone from
# Step 0.5. Match the most distinctive shape of the old code: a `gh api`
# line that hits an `/issues/<var>/comments` path with a jq that pipes
# through `head -1`. Use a single ERE match that requires both pieces
# on the same line so historical/explanatory prose mentioning either
# fragment in isolation is not a false positive.
legacy_pattern=$(grep -cE 'gh api "?/repos/.*/issues/.*/comments".* \| head -1' "$SKILL_MD" || true)
if ! [[ "$legacy_pattern" =~ ^[0-9]+$ ]] || (( legacy_pattern > 0 )); then
  fail "(14) SKILL.md still contains the legacy non-paginated 'gh api .../comments | head -1' anchor-lookup pattern (closes #654); use tracking-issue-write.sh find-anchor instead"
fi

# ---------------------------------------------------------------------------
# (15) Substantive-validation flag pin (#661). The Step 5 quick-mode
#      collect-agent-results.sh invocation in SKILL.md must carry both
#      --substantive-validation AND --validation-mode on the SAME line as
#      --timeout 1860 so banner-only reviewer output (e.g., "Authentication
#      required") is rejected as STATUS=NOT_SUBSTANTIVE rather than passing as
#      STATUS=OK. Pipeline matches the test-review-structure.sh (13) and
#      test-design-structure.sh (7) patterns: each filter stage threads one
#      literal while preserving line granularity. A future edit that drops
#      either flag, or splits the invocation across multiple lines, fails
#      closed under `set -o pipefail`. SKILL.md contains multiple
#      collect-agent-results.sh invocations (Step 5 quick-mode reviewer
#      collector with --substantive-validation); this assertion pins the
#      Step 5 invocation specifically because the pipeline requires all
#      four tokens on one line.
#      Dialectic-execution and adjudication invocations live in sibling skill
#      references, not in this SKILL.md.
# ---------------------------------------------------------------------------
grep 'collect-agent-results.sh' "$SKILL_MD" \
  | grep -F -- '--timeout 1860' \
  | grep -F -- '--substantive-validation' \
  | grep -Fq -- '--validation-mode' \
  || fail "(15) no single SKILL.md line carries 'collect-agent-results.sh', '--timeout 1860', '--substantive-validation', and '--validation-mode' together — issue #661 substantive-validation contract pin is broken"

# ---------------------------------------------------------------------------
# (16) Cross-skill plan-heading drift-prevention pin (closes #749). /design's
#      Step 2b prints the implementation plan under `## Implementation Plan`,
#      and plan-review.md prints `## Revised Implementation Plan` when the plan
#      is revised by accepted findings. /implement's Step 1 plan-goals-test
#      fragment must synthesize from those headings — the legacy consumer
#      instruction at SKILL.md:510 directed composition from `## Goal` and
#      `## Test plan` sections that /design never emitted, leaving the fragment
#      structurally non-extractable on every path. (16a) producer pin —
#      design/SKILL.md and plan-review.md carry their respective heading
#      literals. (16b) consumer scoped positive pin — line range from
#      `### Anchor-section fragments` to next `### ` in implement/SKILL.md
#      must reference `## Implementation Plan`; whole-file grep would
#      false-pass via the unrelated quick-mode "Inline design" reference
#      elsewhere in SKILL.md, so scoping isolates the rewritten plan-goals-test
#      composition bullet. (16c) anchor-template positive pin —
#      anchor-comment-template.md placeholder prose references
#      `## Implementation Plan` as the synthesis source. (16d) broken-pattern
#      negative pin — the legacy contiguous phrase `\`/design\`'s \`## Goal\`
#      and \`## Test plan\` sections` (with backticks as it actually appeared
#      in pre-fix line 510) must NOT appear in implement/SKILL.md. The fix
#      removes that exact substring from line 510 while preserving `## Goal`
#      and `## Test plan` separately (they remain the anchor body's rendered
#      target headings). The negative pin fails closed on broken main and
#      passes on the fixed branch.
# ---------------------------------------------------------------------------
DESIGN_SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
ANCHOR_TEMPLATE_MD="$REFS_DIR/anchor-template-canonical-body.md"

[[ -f "$DESIGN_SKILL_MD" ]] || fail "(16a) skills/design/SKILL.md missing: $DESIGN_SKILL_MD"
[[ -f "$PLAN_REVIEW_MD" ]] || fail "(16a) skills/design/references/plan-review.md missing: $PLAN_REVIEW_MD"
[[ -f "$ANCHOR_TEMPLATE_MD" ]] || fail "(16c) skills/implement/references/anchor-template-canonical-body.md missing: $ANCHOR_TEMPLATE_MD"

grep -Fq '## Implementation Plan' "$DESIGN_SKILL_MD" \
  || fail "(16a) skills/design/SKILL.md missing producer heading literal '## Implementation Plan' — /design must print the plan under this heading for the /implement plan-goals-test consumer to synthesize from (closes #749)"
grep -Fq '## Revised Implementation Plan' "$PLAN_REVIEW_MD" \
  || fail "(16a) skills/design/references/plan-review.md missing producer heading literal '## Revised Implementation Plan' — plan-review.md must print the revised plan under this heading when findings are accepted by vote (closes #749)"

# (16b) Consumer scoped positive pin: extract the line range from
#       `### Anchor-section fragments` (open) to the next `### ` heading
#       (exclusive). The awk pattern `flag=1; next` skips the open heading
#       itself; `/^### /{flag=0}` clears the flag at the next heading without
#       printing it. Whole-file grep would false-pass via the unrelated
#       quick-mode reference at SKILL.md:480.
section_anchor_fragments=$(awk '
  /^### Anchor-section fragments/ { flag=1; next }
  /^### / { flag=0 }
  flag { print }
' "$SKILL_MD")
printf '%s\n' "$section_anchor_fragments" | grep -Fq '## Implementation Plan' \
  || fail "(16b) skills/implement/SKILL.md '### Anchor-section fragments' section does not reference '## Implementation Plan' — the plan-goals-test composition bullet must direct synthesis from /design's actual emitted heading (closes #749)"

# (16c) Anchor-template placeholder prose references the synthesis source heading.
grep -Fq '## Implementation Plan' "$ANCHOR_TEMPLATE_MD" \
  || fail "(16c) skills/implement/references/anchor-template-canonical-body.md missing '## Implementation Plan' reference — placeholder prose under <!-- section:plan-goals-test --> must name the synthesis source heading from /design (closes #749)"

# (16d) Broken-pattern negative pin: the contiguous legacy phrase must not
#       appear in implement/SKILL.md. Backticks are escaped with backslashes
#       inside the double-quoted string so they are literal (no command
#       substitution).
NEGATIVE_PHRASE_16D="\`/design\`'s \`## Goal\` and \`## Test plan\` sections"
if grep -Fq -- "$NEGATIVE_PHRASE_16D" "$SKILL_MD"; then
  fail "(16d) skills/implement/SKILL.md still contains the legacy plan-goals-test composition phrase (\`/design\`'s \`## Goal\` and \`## Test plan\` sections) — /design never emits those sections; rewrite the plan-goals-test composition bullet to synthesize from /design's '## Implementation Plan' (closes #749)"
fi

# ---------------------------------------------------------------------------
# (17) ci-wait.sh synchronous-only invocation pin (closes #842) — guards both
#      `skills/implement/SKILL.md` and
#      `skills/implement/references/rebase-rebump-subprocedure.md` against
#      regressions that would re-introduce the leaked-polling-loop failure
#      mode from PR #821. Two scoped checks per file:
#      (17a) Negative pin: scoped to `ci-wait.sh` adjacency. Fail if any line
#            within ±5 lines of a line containing `ci-wait.sh` ALSO contains
#            `run_in_background: true`. The window is intentionally local —
#            this assertion does NOT ban `run_in_background: true` globally
#            because Step 5 quick-mode reviewer launches and `/design`
#            Step 2a sketch launches legitimately use it. Implementation:
#            awk pass that tracks line-distance from the most recent line
#            containing `ci-wait.sh`; when distance ≤5 AND the current line
#            contains `run_in_background: true`, fail.
#      (17b) Positive pin: each of the two files must contain at least one
#            line with the literal `ci-wait.sh MUST be invoked synchronously`.
#            This guards against a future edit that silently deletes the
#            guardrail paragraph next to the ci-wait.sh invocation block.
#            FINDING_3 from the design panel asked for per-site count
#            enforcement (e.g., exactly 2 occurrences in SKILL.md); the
#            panel voted EXONERATE — the per-site count would force lockstep
#            updates whenever a legitimate new ci-wait.sh invocation block
#            is added. The single-occurrence check + the FINDING_8 explicit
#            site enumeration in scripts/ci-wait.md provide proportionate
#            coverage.
# ---------------------------------------------------------------------------
REBASE_REBUMP_MD="$REFS_DIR/rebase-rebump-subprocedure.md"

[[ -f "$REBASE_REBUMP_MD" ]] || fail "(17) skills/implement/references/rebase-rebump-subprocedure.md missing: $REBASE_REBUMP_MD"

# (17a) Negative pin via awk — scoped to ci-wait.sh adjacency only.
# Lines that contain the literal "MUST be invoked synchronously" are the
# guardrail-defining sentence that legitimately mentions both `ci-wait.sh`
# and the negated phrase `run_in_background: true` ("no `run_in_background:
# true`"); they are whitelisted from the negative scan. The positive pin
# (17b) ensures that literal is present, so the whitelist cannot be
# silently exploited to re-introduce a backgrounded invocation block.
check_ci_wait_adjacency_negative() {
    local file="$1"
    local label="$2"
    awk -v label="$label" '
        function is_violation(line) {
            # Lines containing the synchronous-only guardrail literal are
            # not violations — they document the rule, they do not break it.
            return (line ~ /run_in_background: true/) && (line !~ /MUST be invoked synchronously/)
        }
        /ci-wait\.sh/ { last_ci_wait_line = NR }
        last_ci_wait_line > 0 && (NR - last_ci_wait_line) <= 5 && is_violation($0) {
            printf "FAIL: %s line %d contains run_in_background: true within 5 lines of a ci-wait.sh reference (line %d) — see #842\n", label, NR, last_ci_wait_line
            found = 1
        }
        # Also check lines BEFORE a ci-wait.sh line (look-behind via buffering).
        # Buffer the last 5 lines so we can re-check when we hit a ci-wait.sh line.
        {
            buf[NR % 6] = $0
            line_num[NR % 6] = NR
        }
        /ci-wait\.sh/ {
            for (i = 1; i <= 5; i++) {
                idx = (NR - i) % 6
                if (line_num[idx] >= 1 && is_violation(buf[idx])) {
                    printf "FAIL: %s line %d contains run_in_background: true within 5 lines BEFORE a ci-wait.sh reference (line %d) — see #842\n", label, line_num[idx], NR
                    found = 1
                }
            }
        }
        END { exit found ? 1 : 0 }
    ' "$file"
}

if ! check_ci_wait_adjacency_negative "$SKILL_MD" "skills/implement/SKILL.md" >&2; then
    fail "(17a) skills/implement/SKILL.md has run_in_background: true adjacent to a ci-wait.sh reference — see #842 (the leaked-polling-loop failure mode); ci-wait.sh MUST be invoked synchronously"
fi

if ! check_ci_wait_adjacency_negative "$REBASE_REBUMP_MD" "skills/implement/references/rebase-rebump-subprocedure.md" >&2; then
    fail "(17a) skills/implement/references/rebase-rebump-subprocedure.md has run_in_background: true adjacent to a ci-wait.sh reference — see #842; ci-wait.sh MUST be invoked synchronously"
fi

# (17b) Positive pin: synchronous-only guidance literal must appear in each file.
# The actual prose may format `ci-wait.sh` with markdown backticks
# (`` `ci-wait.sh` `` / `**`ci-wait.sh`**`), so the byte-pinned literal is the
# stable suffix `MUST be invoked synchronously`. The leading `ci-wait.sh` is
# implied by the per-file scoping (we only run this check against files known
# to reference ci-wait.sh) and by the negative pin (17a) which guarantees
# adjacency.
SYNC_GUIDANCE_LITERAL='MUST be invoked synchronously'
grep -Fq -- "$SYNC_GUIDANCE_LITERAL" "$SKILL_MD" \
    || fail "(17b) skills/implement/SKILL.md missing the synchronous-only guardrail literal '$SYNC_GUIDANCE_LITERAL' near the ci-wait.sh invocation blocks (Step 10 / Step 12a) — closes #842 regression"
grep -Fq -- "$SYNC_GUIDANCE_LITERAL" "$REBASE_REBUMP_MD" \
    || fail "(17b) skills/implement/references/rebase-rebump-subprocedure.md missing the synchronous-only guardrail literal '$SYNC_GUIDANCE_LITERAL' near step 7's ci-wait.sh re-invocation directives — closes #842 regression"

# (18) Protocol Execution Directive pin: the literal must appear exactly once
# in SKILL.md (global count check). Guards against accidental deletion of the
# preamble that prevents orchestrator freelancing.
DIRECTIVE_LITERAL='Protocol Execution Directive'
DIRECTIVE_COUNT=$(grep -cF -- "$DIRECTIVE_LITERAL" "$SKILL_MD")
if [[ "$DIRECTIVE_COUNT" -ne 1 ]]; then
    fail "(18) Expected exactly 1 '$DIRECTIVE_LITERAL' in skills/implement/SKILL.md, found $DIRECTIVE_COUNT"
fi

# (19) Step 2 external implementer dispatcher pin: SKILL.md must reference the dispatcher
# script path at least once (the dispatcher invocation block) AND the dispatcher
# script + its sibling contract MUST exist and be executable. Guards against an
# edit that quietly removes the mandatory external-implementer dispatcher path.
DISPATCHER_LITERAL='skills/implement/scripts/step2-implement.sh'
grep -Fq -- "$DISPATCHER_LITERAL" "$SKILL_MD" \
    || fail "(19) skills/implement/SKILL.md missing dispatcher invocation literal '$DISPATCHER_LITERAL' — Step 2 Codex spawn would be orphaned"
DISPATCHER_PATH="$REPO_ROOT/$DISPATCHER_LITERAL"
[[ -x "$DISPATCHER_PATH" ]] \
    || fail "(19) dispatcher script missing or not executable: $DISPATCHER_PATH"
[[ -f "$REPO_ROOT/skills/implement/scripts/step2-implement.md" ]] \
    || fail "(19) dispatcher sibling contract missing: skills/implement/scripts/step2-implement.md"
[[ -x "$REPO_ROOT/scripts/launch-codex-implement.sh" ]] \
    || fail "(19) Codex implementer launcher missing or not executable: scripts/launch-codex-implement.sh"
[[ -f "$REPO_ROOT/agents/codex-implementer.md" ]] \
    || fail "(19) Codex implementer system prompt missing: agents/codex-implementer.md"
[[ -x "$REPO_ROOT/scripts/launch-cursor-implement.sh" ]] \
    || fail "(19) Cursor implementer launcher missing or not executable: scripts/launch-cursor-implement.sh"
[[ -f "$REPO_ROOT/scripts/launch-cursor-implement.md" ]] \
    || fail "(19) Cursor implementer launcher sibling contract missing: scripts/launch-cursor-implement.md"
[[ -f "$REPO_ROOT/agents/cursor-implementer.md" ]] \
    || fail "(19) Cursor implementer system prompt missing: agents/cursor-implementer.md"
[[ -x "$REPO_ROOT/skills/implement/scripts/test-cursor-implementer.sh" ]] \
    || fail "(19) Cursor implementer test harness missing or not executable: skills/implement/scripts/test-cursor-implementer.sh"
[[ -f "$REPO_ROOT/skills/implement/scripts/test-cursor-implementer.md" ]] \
    || fail "(19) Cursor implementer test harness sibling contract missing: skills/implement/scripts/test-cursor-implementer.md"
[[ -x "$REPO_ROOT/scripts/launch-gemini-implement.sh" ]] \
    || fail "(19) Gemini implementer launcher missing or not executable: scripts/launch-gemini-implement.sh"
[[ -f "$REPO_ROOT/scripts/launch-gemini-implement.md" ]] \
    || fail "(19) Gemini implementer launcher sibling contract missing: scripts/launch-gemini-implement.md"
[[ -f "$REPO_ROOT/agents/gemini-implementer.md" ]] \
    || fail "(19) Gemini implementer system prompt missing: agents/gemini-implementer.md"
[[ -x "$REPO_ROOT/skills/implement/scripts/test-gemini-implementer.sh" ]] \
    || fail "(19) Gemini implementer test harness missing or not executable: skills/implement/scripts/test-gemini-implementer.sh"
[[ -f "$REPO_ROOT/skills/implement/scripts/test-gemini-implementer.md" ]] \
    || fail "(19) Gemini implementer test harness sibling contract missing: skills/implement/scripts/test-gemini-implementer.md"

# (20) Design manifest + design-only path pin: Step 1 must read the design
# manifest, the flag table must expose --design-only, and Step 18 must mark
# design-only runs DONE without requiring a PR number.
grep -Fq -- '--design-only' "$SKILL_MD" \
    || fail "(20) skills/implement/SKILL.md missing --design-only flag"
grep -Fq -- 'read-design-manifest.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"' "$SKILL_MD" \
    || fail "(20) Step 1 missing read-design-manifest.sh invocation"
grep -Fq -- 'DESIGN_ONLY_DONE=true' "$SKILL_MD" \
    || fail "(20) Step 1 missing DESIGN_ONLY_DONE short-circuit state"
grep -Fq -- '$PR_NUMBER` is set OR `DESIGN_ONLY_DONE=true' "$SKILL_MD" \
    || fail "(20) Step 18 DONE branch must fire for PR_NUMBER or DESIGN_ONLY_DONE"
grep -Fq -- '$IMPLEMENT_TMPDIR/code-flow-diagram.md' "$SKILL_MD" \
    || fail "(20) Step 7a/9a must use code-flow diagram file path"

# (21) --inline flag and --subagent forwarding pin (issue #1036). SKILL.md must:
#      (21a) document the `--inline` flag with `inline_mode=true` literal in the flag list.
#      (21b) include `[--subagent]` in the canonical /design invocation order block.
#      (21c) describe the conditional-forward rule tying `--subagent` forwarding to `inline_mode=false`.
grep -Fq -- '--inline' "$SKILL_MD" \
  || fail "(21a) skills/implement/SKILL.md missing '--inline' flag literal (issue #1036)"
grep -Fq -- 'inline_mode=true' "$SKILL_MD" \
  || fail "(21a) skills/implement/SKILL.md missing 'inline_mode=true' literal (issue #1036)"
grep -Fq -- '[--subagent]' "$SKILL_MD" \
  || fail "(21b) skills/implement/SKILL.md missing '[--subagent]' in canonical /design invocation order (issue #1036)"
grep -Fq -- 'inline_mode=false' "$SKILL_MD" \
  || fail "(21c) skills/implement/SKILL.md missing 'inline_mode=false' default-forwarding rule (issue #1036)"
grep -Fq -- '[--design-classification "$ROUTER_CLASSIFICATION"]' "$SKILL_MD" \
  || fail "(21d) skills/implement/SKILL.md missing --design-classification in canonical /design invocation order"
grep -Fq -- 'POST_PLAN_WORKFLOW_PATH' "$SKILL_MD" \
  || fail "(21e) skills/implement/SKILL.md missing POST_PLAN_WORKFLOW_PATH post-plan router key"
grep -Fq -- 'Do not run the pre-design router or overwrite a reused classification' "$SKILL_MD" \
  || fail "(21f) manifest-reuse path must not overwrite reused design classification"

# (22) Orchestrator-edit-authority gate pin: SKILL.md must reference the
# mechanical gate literals introduced by the dispatcher contract — NEVER #10,
# the ORCHESTRATOR_EDIT_AUTHORITY KV key, the §2.1.5 envelope-validation
# block, and the orchestrator-local synthetic bail token. Mirrors (17b) for
# the ci-wait synchronous-only literal: prevents silent deletion of the prompt
# half of the gate (the mechanical half is pinned by test-step2-dispatch.sh
# Test 11).
grep -Fq -- 'ORCHESTRATOR_EDIT_AUTHORITY' "$SKILL_MD" \
    || fail "(22) skills/implement/SKILL.md missing 'ORCHESTRATOR_EDIT_AUTHORITY' literal — Step 2 mechanical edit-authority gate would be undocumented"
grep -Fq -- '2.1.5 — Envelope validation' "$SKILL_MD" \
    || fail "(22) skills/implement/SKILL.md missing '2.1.5 — Envelope validation' header — fail-closed envelope-validation block would be unreachable from the Step 2 narrative"
grep -Fq -- 'orchestrator-envelope-invalid' "$SKILL_MD" \
    || fail "(22) skills/implement/SKILL.md missing 'orchestrator-envelope-invalid' synthetic bail token — §2.1.5 fail-closed routing would have no named REASON"
# NEVER #10 anchor: assert at least one of the SKILL-internal anchors that
# point at the rule. The rule body literal is too long to byte-pin reliably,
# but every cross-reference funnels through one of these short anchors.
grep -Fq -- 'NEVER #10' "$SKILL_MD" \
    || fail "(22) skills/implement/SKILL.md missing 'NEVER #10' cross-reference anchor — the orchestrator-edit-authority NEVER rule would have no inbound references"

# (23) Gemini probe removed (#1720, Part 1). /implement no longer launches Gemini reviewers
# in Step 5 quick mode (the review call sites were removed deliberately while
# preserving the `--coder=gemini` dispatch path). Step 0 no longer passes
# --check-gemini-reviewer; session-setup.sh hard-codes GEMINI_HEALTHY=false.
# Step 5 quick mode uses a 3-round 6-reviewer panel.
grep -Fq -- '--gemini-healthy' "$SKILL_MD" \
  || fail "(23b) /implement does not write GEMINI_HEALTHY into session-env"
grep -Fq 'gemini_available=false' "$SKILL_MD" \
  || fail "(23c) /implement lacks gemini_available=false default for --coder=gemini gating"
grep -Fq 'up to 3 rounds' "$SKILL_MD" \
  || fail "(23f) quick-mode missing 3-round cap"
grep -Fq '5 Cursor specialists + generic Codex' "$SKILL_MD" \
  || fail "(23g) quick-mode missing 6-reviewer panel wording"
if grep -Fq 'Cursor → Codex → Claude' "$SKILL_MD"; then
  fail "(23h) quick-mode must not retain rounds 4+ Cursor → Codex → Claude chain"
fi
grep -Fq 'GEMINI_HEALTHY' "$SKILL_MD" \
  || fail "(23i) /implement cross-skill health propagation omits GEMINI_HEALTHY"
# (24) Implementer generated-prompt structure. The shared implementer body
# lives in agents/_implementer-base.md, and generated prompts carry
# AUTO-GENERATED markers. Cursor/Gemini prose after `## Shared guardrails`
# remains byte-identical modulo the per-tool token substitution
# `cursor-modified-history` ↔ `gemini-modified-history` and
# `cursor-commit-stderr.txt` ↔ `gemini-commit-stderr.txt`, so the two
# unsandboxed implementer prompts do not drift in safety-critical instructions
# while still showing each implementer the concrete token it will see in a
# bail.
[[ -f "$REPO_ROOT/agents/_implementer-base.md" ]] \
  || fail "(24) agents/_implementer-base.md missing"
for implementer_prompt in \
  "$REPO_ROOT/agents/codex-implementer.md" \
  "$REPO_ROOT/agents/cursor-implementer.md" \
  "$REPO_ROOT/agents/gemini-implementer.md"
do
  grep -Fq '<!-- AUTO-GENERATED:' "$implementer_prompt" \
    || fail "(24) $(basename "$implementer_prompt") missing AUTO-GENERATED marker"
done
CURSOR_SHARED=$(awk 'found { print } /^## Shared guardrails$/ { found=1 }' "$REPO_ROOT/agents/cursor-implementer.md" \
  | sed -e 's/cursor-modified-history/TOOL-modified-history/g' -e 's/cursor-commit-stderr\.txt/TOOL-commit-stderr.txt/g')
GEMINI_SHARED=$(awk 'found { print } /^## Shared guardrails$/ { found=1 }' "$REPO_ROOT/agents/gemini-implementer.md" \
  | sed -e 's/gemini-modified-history/TOOL-modified-history/g' -e 's/gemini-commit-stderr\.txt/TOOL-commit-stderr.txt/g')
[[ -n "$CURSOR_SHARED" ]] \
  || fail "(24) agents/cursor-implementer.md missing non-empty Shared guardrails section"
[[ "$CURSOR_SHARED" == "$GEMINI_SHARED" ]] \
  || fail "(24) agents/gemini-implementer.md Shared guardrails section drifted from agents/cursor-implementer.md (modulo per-tool token substitution)"

# (24b) External implementer OOS triage gate and Step 9a.1 defensive
# security re-exclusion pins. These literals prevent the implementer prompts
# from regressing to pre-triage `oos_observations[]` semantics and prevent the
# last-line public-filing backstop from being deleted from the anchor template.
for implementer_prompt in \
  "$REPO_ROOT/agents/codex-implementer.md" \
  "$REPO_ROOT/agents/cursor-implementer.md" \
  "$REPO_ROOT/agents/gemini-implementer.md"
do
  grep -Fq '## OOS triage gate before manifest' "$implementer_prompt" \
    || fail "(24b) $(basename "$implementer_prompt") missing OOS triage gate heading"
  grep -Fq 'Security findings are NEVER folded inline and NEVER filed via this OOS path regardless of size' "$implementer_prompt" \
    || fail "(24b) $(basename "$implementer_prompt") missing security carve-out in OOS triage gate"
  grep -Fq 'Inline-triage rule N:' "$implementer_prompt" \
    || fail "(24b) $(basename "$implementer_prompt") missing Inline-triage audit annotation contract"
  grep -Fq 'contains only filed-OOS candidates after this triage' "$implementer_prompt" \
    || fail "(24b) $(basename "$implementer_prompt") missing post-triage oos_observations semantics"
done

grep -Fq 'defensively filter out any `### OOS_N:` block whose content contains the canonical token `focus-area\s*=\s*security`' "$REFS_DIR/anchor-template-oos-pipeline.md" \
  || fail "(24c) anchor-template-oos-pipeline.md missing Step 9a.1 defensive security re-exclusion sub-bullet"
grep -Fq 'post-filter entry list is logically empty after security re-exclusion' "$REFS_DIR/anchor-template-oos-pipeline.md" \
  || fail "(24c) anchor-template-oos-pipeline.md missing post-filter empty-batch early-exit path"
grep -Fq 'Match discrimination (false-positive guard)' "$REFS_DIR/anchor-template-oos-pipeline.md" \
  || fail "(24c) anchor-template-oos-pipeline.md missing Match discrimination (false-positive guard) sub-bullet"
grep -Fq 'Security counter-invariant' "$REFS_DIR/anchor-template-oos-pipeline.md" \
  || fail "(24c) anchor-template-oos-pipeline.md missing Security counter-invariant clause"

# (25) Clean-main Step 0 entry gate pin. Scope positive checks to Step 0 so
# the later Step 1 branch creation check cannot satisfy the entry-gate
# assertion by accident. The gate must flow create-branch -> session-entry-gate
# -> session-setup, and Step 0 must preserve the continue_from_current alias for
# downstream Step 1.m compatibility.
step0_section=$(awk '
  /^## Step 0 — Session Setup$/ { flag=1; next }
  /^## / && flag { flag=0 }
  flag { print }
' "$SKILL_MD")
[[ -n "$step0_section" ]] \
  || fail "(25) could not extract /implement Step 0 section"

protocol_line=$(grep -F 'Protocol Execution Directive.' "$SKILL_MD" | head -1 || true)
printf '%s\n' "$protocol_line" | grep -Fq 'create-branch.sh --check' \
  || fail "(25) Protocol Execution Directive must mention create-branch.sh --check"
printf '%s\n' "$protocol_line" | grep -Fq 'session-entry-gate.sh' \
  || fail "(25) Protocol Execution Directive must mention session-entry-gate.sh"
printf '%s\n' "$protocol_line" | grep -Fq 'session-setup.sh' \
  || fail "(25) Protocol Execution Directive must mention session-setup.sh"
if printf '%s\n' "$protocol_line" | grep -Fq 'BOTH `create-branch.sh`'; then
  fail "(25) Protocol Execution Directive still contains the legacy BOTH create-branch phrasing"
fi

# shellcheck disable=SC2016 # fixed-string grep literal contains shell variable syntax
printf '%s\n' "$step0_section" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check' \
  || fail "(25) Step 0 must run create-branch.sh --check before session setup"
printf '%s\n' "$step0_section" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh' \
  || fail "(25) Step 0 must invoke session-entry-gate.sh"
printf '%s\n' "$step0_section" | grep -Fq -- '--mode implement' \
  || fail "(25) Step 0 must invoke session-entry-gate.sh with --mode implement"
printf '%s\n' "$step0_section" | grep -Fq 'SKIP_BRANCH_CHECK' \
  || fail "(25) Step 0 must parse/use SKIP_BRANCH_CHECK as the authoritative key"
printf '%s\n' "$step0_section" | grep -Fq 'GATE_ERROR' \
  || fail "(25) Step 0 must handle GATE_ERROR separately from PREFLIGHT_ERROR"
printf '%s\n' "$step0_section" | grep -Fq 'continue_from_current=true' \
  || fail "(25) Step 0 must preserve the continue_from_current=true alias"
printf '%s\n' "$step0_section" | grep -F 'session-setup.sh' \
  | grep -F -- '--skip-branch-check' >/dev/null \
  || fail "(25) Step 0 must include a session-setup.sh invocation with --skip-branch-check for SKIP_BRANCH_CHECK=true"
printf '%s\n' "$step0_section" | grep -Fq 'If `SKIP_BRANCH_CHECK=false`, run setup without `--skip-branch-check`' \
  || fail "(25) Step 0 must document the strict setup path without --skip-branch-check"
printf '%s\n' "$step0_section" | grep -F 'session-setup.sh --prefix claude-implement --check-reviewers' >/dev/null \
  || fail "(25) Step 0 must include the no-skip session-setup.sh invocation for strict clean-main preflight"
printf '%s\n' "$step0_section" | grep -Fq '/implement requires clean main to start' \
  || fail "(25) Step 0 must include the normalized /implement clean-main failure message"

create_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --check' | head -1 | cut -d: -f1 || true)
gate_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/session-entry-gate.sh' | head -1 | cut -d: -f1 || true)
setup_line=$(printf '%s\n' "$step0_section" | grep -nF '${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$create_line" && -n "$gate_line" && -n "$setup_line" ]] \
  || fail "(25) could not locate create-branch, session-entry-gate, and session-setup lines in Step 0"
if (( create_line >= gate_line || gate_line >= setup_line )); then
  fail "(25) Step 0 ordering must be create-branch.sh --check before session-entry-gate.sh before session-setup.sh"
fi

old_unconditional_prose="--skip-branch-check is required so Step 1's IS_USER_BRANCH=true branch-resume paths are reachable"
if grep -Fq -- "$old_unconditional_prose" "$SKILL_MD"; then
  fail "(25) SKILL.md still contains the legacy unconditional --skip-branch-check prose"
fi

# Fork-mode structural pins (issue #1415). These checks intentionally sit near
# assertion 25 because the fork helper is the only permitted pre-setup exception
# to the Step 0 clean-main entry gate.
grep -Fq -- '--forked' "$SKILL_MD" \
  || fail "(25-fork) SKILL.md argument/flag surface must advertise --forked"
printf '%s\n' "$protocol_line" | grep -Fq 'implement-fork-env.sh' \
  || fail "(25-fork) Protocol Execution Directive must name implement-fork-env.sh as the fork pre-setup exception"
# Round 1 FINDING_1 + Round 3 FINDING_1 fix: Step 0 invokes
# implement-fork-env.sh WITHOUT --tmpdir (the helper allocates its own
# bootstrap via mktemp because IMPLEMENT_TMPDIR is not yet set when
# this runs). Pin both the bare invocation and the absence of the old
# --tmpdir-passing form so future edits cannot silently regress.
printf '%s\n' "$step0_section" | grep -Eq '\$\{CLAUDE_PLUGIN_ROOT\}/scripts/implement-fork-env\.sh($|[^ ]| *$)' \
  || fail "(25-fork) Step 0 must invoke implement-fork-env.sh exactly once under forked_target=true"
printf '%s\n' "$step0_section" | grep -Fq 'implement-fork-env.sh --tmpdir "$IMPLEMENT_TMPDIR"' \
  && fail "(25-fork) Step 0 must NOT pass --tmpdir \"\$IMPLEMENT_TMPDIR\" (Round 1 FINDING_1 — IMPLEMENT_TMPDIR is unset at this point)"
printf '%s\n' "$step0_section" | grep -Fq 'CALLER_ENV_PATH' \
  || fail "(25-fork) Step 0 fork-mode prose must mention CALLER_ENV_PATH (Round 1 FINDING_1 — capture from helper stdout)"
grep -Fq 'If `forked_target=true`: print `⏭️ 11: execution-issues status=bypass reason=forked-dry-run elapsed=<elapsed>`' "$SKILL_MD" \
  || fail "(25-fork) Step 11 must have an explicit forked_target=true short-circuit"
grep -Fq 'omit the `Closes #<TRACKING_ISSUE_NUMBER>` line unconditionally' "$SKILL_MD" \
  || fail "(25-fork) Step 9a must unconditionally suppress Closes under fork mode"
grep -Fq 'Fork-mode carve-out for Invariants #1 and #2' "$SKILL_MD" \
  || fail "(25-fork) Load-Bearing Invariants must document the fork-mode carve-out"
grep -Fq '**Fork-mode carve-out**: when `forked_target=true`' "$SKILL_MD" \
  || fail "(25-fork) NEVER #5 must document the fork-mode carve-out"

# ---------------------------------------------------------------------------
# (26) Post-merge anti-halt literal pin (issue #1143). The post-merge
#      boundary is halt-prone because the merge breadcrumb sounds terminal
#      while Steps 14, 15, 16, 17, 18 remain mandatory. Pin the three
#      reminder sites with fixed-string checks, plus a count floor for the
#      shared enumeration so deleting either the NEVER #7 reminder or the
#      ACTION=already_merged reminder fails closed.
# ---------------------------------------------------------------------------
post_merge_never7_literals=(
  '**Post-merge sub-clause (highest-stakes halt boundary)**'
  'the celebratory "merged!" tone makes the run feel complete, but Steps 14, 15, 16, 17, 18 still must run'
)
for lit in "${post_merge_never7_literals[@]}"; do
  grep -Fq "$lit" "$SKILL_MD" \
    || fail "(26a) SKILL.md lost NEVER #7 post-merge anti-halt literal: $lit"
done

already_merged_literals=(
  '"force-merged externally" feels terminal but is mid-run'
  'Steps 14, 15, 16, 17, 18 still must run.'
)
for lit in "${already_merged_literals[@]}"; do
  grep -Fq "$lit" "$SKILL_MD" \
    || fail "(26b) SKILL.md lost Step 12a ACTION=already_merged continuation literal: $lit"
done

post_merge_step_count=$(grep -Fc 'Steps 14, 15, 16, 17, 18 still must run' "$SKILL_MD" || true)
if ! [[ "$post_merge_step_count" =~ ^[0-9]+$ ]] || (( post_merge_step_count < 2 )); then
  fail "(26b-count) expected at least 2 post-merge Step 14-18 continuation enumerations in SKILL.md (NEVER #7 + Step 12a ACTION=already_merged), found ${post_merge_step_count:-0}"
fi

post_merge_blockquote_literals=(
  '> **Continue to Step 14 IMMEDIATELY.**'
  'Halting here is a NEVER #7-family violation regardless of how natural the boundary feels'
)
for lit in "${post_merge_blockquote_literals[@]}"; do
  grep -Fq "$lit" "$SKILL_MD" \
    || fail "(26c) SKILL.md lost Step 12b post-merge blockquote literal: $lit"
done

# ---------------------------------------------------------------------------
# (27) Step 1 normal-mode ordering pin (closes #1165). Within
#      `## Step 1 — Ensure Design Plan Exists`, the line introducing
#      `**Manifest reuse (resumed sessions — runs first)**` must precede the
#      lines introducing `**Simplicity classification preamble**` and
#      `**Both-externals-down inline-plan branch**`. The ordering is
#      load-bearing: the manifest-reuse guard must run BEFORE simplicity
#      classification (which can auto-switch to quick mode) and BEFORE the
#      both-externals-down inline-plan branch (which writes a degraded
#      plan.txt) so a resumed session never overwrites the prior `/design`
#      artifact set. Step 1 contains the normative prose stating
#      "runs first" / "BEFORE simplicity classification" / "BEFORE the
#      both-externals-down inline-plan branch", but a future prose-only
#      re-reorder of the actual sub-step headings would not be caught by
#      any other check (assertion 20 only pins the presence of
#      `read-design-manifest.sh`). Mirrors the ordering-comparison style of
#      assertion 25's create-branch → session-entry-gate → session-setup
#      check. Scoped to the Step 1 section via awk so similarly-worded
#      text under other steps cannot satisfy the ordering by accident.
# ---------------------------------------------------------------------------
step1_section=$(awk '
  /^## Step 1 — / { flag=1; next }
  /^## Step / && flag { flag=0 }
  flag { print }
' "$SKILL_MD")
[[ -n "$step1_section" ]] \
  || fail "(27) could not extract /implement Step 1 section"

manifest_line=$(printf '%s\n' "$step1_section" | grep -nF -- '**Manifest reuse (resumed sessions — runs first)**' | head -1 | cut -d: -f1 || true)
simplicity_line=$(printf '%s\n' "$step1_section" | grep -nF -- '**Simplicity classification preamble — skip condition**' | head -1 | cut -d: -f1 || true)
both_down_line=$(printf '%s\n' "$step1_section" | grep -nF -- '**Both-externals-down inline-plan branch**' | head -1 | cut -d: -f1 || true)
[[ -n "$manifest_line" && -n "$simplicity_line" && -n "$both_down_line" ]] \
  || fail "(27) could not locate Manifest reuse, Simplicity classification preamble, and Both-externals-down inline-plan branch lines in /implement Step 1 section (closes #1165)"
if (( manifest_line >= simplicity_line || manifest_line >= both_down_line )); then
  fail "(27) Step 1 normal-mode ordering must be: Manifest reuse, then Simplicity classification preamble, then Both-externals-down inline-plan branch (closes #1165)"
fi

# ---------------------------------------------------------------------------
# (28) Timing instrumentation pins. Timing is intentionally parallel to the
#      token observability plane, so these checks catch unpaired step marks,
#      missing workflow-path exits, anchor drift, invalid timing-kind literals,
#      and the review-loop round mark that gives nested /review rows useful
#      boundaries.
# ---------------------------------------------------------------------------
token_mark_count=$(grep -Fc 'scripts/token-ledger.sh" mark "Step' "$SKILL_MD" || true)
timing_mark_count=$(grep -Fc 'scripts/timing-ledger.sh" mark "Step' "$SKILL_MD" || true)
if [[ "$token_mark_count" != "$timing_mark_count" ]]; then
  fail "(28a) /implement token/timing mark count mismatch: token=$token_mark_count timing=$timing_mark_count"
fi

token_rehydrate_gaps=$(awk '
  /^```bash$/ { in_block=1; block=""; start=NR; next }
  /^```$/ && in_block {
    if (block ~ /token-(ledger|report)\.sh / &&
        block !~ /Step 0 — preflight/ &&
        block !~ /read-session-env-key\.sh" --file "\$IMPLEMENT_TMPDIR\/session-env\.sh" --key LARCH_TOKEN_SESSION_ID/) {
      print start
    }
    in_block=0
    block=""
    next
  }
  in_block { block = block $0 "\n" }
' "$SKILL_MD")
if [[ -n "$token_rehydrate_gaps" ]]; then
  fail "(28a2) /implement token-ledger/token-report Bash blocks missing LARCH_TOKEN_SESSION_ID rehydrate prefix at code-fence starts: $token_rehydrate_gaps"
fi

grep -Fq '<!-- section:timing-report -->' "$REFS_DIR/anchor-template-canonical-body.md" \
  || fail "(28b) anchor-template-canonical-body.md missing timing-report open marker"
grep -Fq '<!-- section-end:timing-report -->' "$REFS_DIR/anchor-template-canonical-body.md" \
  || fail "(28b) anchor-template-canonical-body.md missing timing-report close marker"

grep -Fq '<!-- section:token-report -->' "$REFS_DIR/anchor-template-canonical-body.md" \
  || fail "(28b2) anchor-template-canonical-body.md missing token-report open marker"
grep -Fq '<!-- section-end:token-report -->' "$REFS_DIR/anchor-template-canonical-body.md" \
  || fail "(28b2) anchor-template-canonical-body.md missing token-report close marker"

workflow_path_count=$(grep -Fc 'timing-ledger.sh" workflow-path' "$SKILL_MD" || true)
if [[ "$workflow_path_count" != "7" ]]; then
  fail "(28c) expected 7 /implement workflow-path emission sites, found $workflow_path_count"
fi

REVIEW_SKILL_MD="$REPO_ROOT/skills/review/SKILL.md"
grep -Fq 'review Step 3 round ${round_num} — review cycle' "$REVIEW_SKILL_MD" \
  || fail "(28d) /review SKILL.md missing per-round Step 3 timing mark literal"

forbidden_round_kind="cursor-review-roundN""-generic"
if find "$REPO_ROOT/skills" "$REPO_ROOT/scripts" -type f ! -path "$0" -print0 \
  | xargs -0 grep -Fq "$forbidden_round_kind"; then
  fail "(28e) forbidden cursor-review-roundN generic literal found; use cursor-review-generic"
fi

if grep -n 'quick-review.*launch-.*-review\.sh' "$SKILL_MD" | grep -v -- '--timing-task-kind' >/dev/null; then
  fail "(28f) quick-mode launch-*-review.sh invocation missing --timing-task-kind"
fi

allowed_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-timing-kinds-allowed.XXXXXX")
actual_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-timing-kinds-actual.XXXXXX")
trap 'rm -f "$allowed_tmp" "$actual_tmp"' EXIT
awk '
  /^[[:space:]]*[a-z][a-z0-9-]*$/ { print $1 }
' "$REPO_ROOT/scripts/lib-timing-kinds.sh" | sort -u > "$allowed_tmp"
grep -RhoE -- '--timing-task-kind[[:space:]]+[a-z][a-z0-9-]*' "$REPO_ROOT/skills" "$REPO_ROOT/scripts"/launch-* 2>/dev/null \
  | awk '$2 != "requires" && $2 != "defaults" { print $2 }' | sort -u > "$actual_tmp" || true
while IFS= read -r kind; do
  [[ -z "$kind" ]] && continue
  grep -qxF "$kind" "$allowed_tmp" \
    || fail "(28g) --timing-task-kind literal not present in TIMING_TASK_KINDS_ALLOWED: $kind"
done < "$actual_tmp"
for kind in \
  codex-specialist-structure \
  codex-specialist-correctness \
  codex-specialist-testing \
  codex-specialist-security \
  codex-specialist-edge-cases
do
  grep -qxF "$kind" "$allowed_tmp" \
    || fail "(28g) codex specialist timing kind missing from TIMING_TASK_KINDS_ALLOWED: $kind"
done

# ---------------------------------------------------------------------------
# (29) Anti-pattern doc-drift pin (closes #1512, was #1498). Issue #1480 added
#      three documentary surfaces — the dialectic-execution.md recovery
#      sentence, the heavy-worker.md `run_in_background: true` + yield
#      anti-pattern + SendMessage-dependency note, and the AGENTS.md
#      SendMessage requirement bullet — none of which were mechanically
#      pinned. A future edit could silently regress any of them. Pin each
#      with a fixed-string check so deletion fails CI. Mirrors the
#      whole-file byte-pin pattern of assertions (13)/(26).
# ---------------------------------------------------------------------------
DESIGN_REFS_DIR="$REPO_ROOT/skills/design/references"
DIALECTIC_EXEC_MD="$DESIGN_REFS_DIR/dialectic-execution.md"
HEAVY_WORKER_MD="$DESIGN_REFS_DIR/heavy-worker.md"
AGENTS_MD="$REPO_ROOT/AGENTS.md"

[[ -f "$DIALECTIC_EXEC_MD" ]] || fail "(29a) skills/design/references/dialectic-execution.md missing: $DIALECTIC_EXEC_MD"
[[ -f "$HEAVY_WORKER_MD" ]] || fail "(29b) skills/design/references/heavy-worker.md missing: $HEAVY_WORKER_MD"
[[ -f "$AGENTS_MD" ]] || fail "(29c) AGENTS.md missing: $AGENTS_MD"

dialectic_exec_pin='do NOT yield control back to the parent'
grep -Fq "$dialectic_exec_pin" "$DIALECTIC_EXEC_MD" \
  || fail "(29a) skills/design/references/dialectic-execution.md missing pin '$dialectic_exec_pin' — see #1512"

heavy_worker_pins=(
  '`run_in_background: true` + yield'
  '**SendMessage dependency.**'
)
for lit in "${heavy_worker_pins[@]}"; do
  grep -Fq "$lit" "$HEAVY_WORKER_MD" \
    || fail "(29b) skills/design/references/heavy-worker.md missing pin '$lit' — see #1512"
done

agents_pin='`/design --subagent` requires `SendMessage`'
grep -Fq "$agents_pin" "$AGENTS_MD" \
  || fail "(29c) AGENTS.md missing pin '$agents_pin' — see #1512"

# ---------------------------------------------------------------------------
# (30) Coder simplicity override pin (closes #1512, was #1482).
#      skills/implement/SKILL.md grew a "### Coder simplicity override"
#      section (Step 1) that auto-routes implementer selection to claude
#      for small, surgical plans when --coder was not explicitly passed.
#      The section's heading, gate phrase, and literal breadcrumb are
#      runtime-load-bearing: the orchestrator emits the breadcrumb verbatim
#      when the override fires, and `/fix-issue` and other consumers expect
#      that breadcrumb shape. Future edits to SKILL.md could drop or
#      paraphrase any of the three without failing any other check. Pin
#      each with a fixed-string check.
# ---------------------------------------------------------------------------
coder_override_heading='### Coder simplicity override'
grep -Fq "$coder_override_heading" "$SKILL_MD" \
  || fail "(30a) skills/implement/SKILL.md missing pin '$coder_override_heading' — see #1512"

coder_override_gate='`coder_explicit=false` AND `design_only=false`'
grep -Fq "$coder_override_gate" "$SKILL_MD" \
  || fail "(30b) skills/implement/SKILL.md missing pin '$coder_override_gate' — see #1512"

coder_override_breadcrumb='**⚡ 1: design plan — task classified as small (≤ ~100 LOC, no new abstractions); coder auto-set to claude (no explicit --coder).**'
grep -Fq "$coder_override_breadcrumb" "$SKILL_MD" \
  || fail "(30c) skills/implement/SKILL.md missing pin '$coder_override_breadcrumb' — see #1512"

# ---------------------------------------------------------------------------
# (31) CLONE_TAG basename algorithm pin (closes #1563, #1572). The Step 13.5 / Step 14
#      state-file snippets compute EXPECTED_TMPDIR_BASENAME_PREFIX, which
#      Step 18's verify_cleanup_target compares against the actual session
#      tmpdir basename to authorize rm-rf. The prefix MUST exactly mirror what
#      `scripts/session-setup.sh`'s CLONE_TAG derivation block and
#      `scripts/implement-finalize.sh::clone_basename_prefix` produce — a
#      four-step pipeline: (1) basename, (2) sanitize via tr (NOT a one-pipe
#      `basename "$PWD" | tr` form, which bakes basename's trailing newline
#      into a stray '_'), (3) truncate to 32 chars, (4) empty-fallback to '_'.
#      Both Step 13.5 and Step 14 must compute the full algorithm into a
#      pre-heredoc CLONE_TAG_FULL variable, so the positive pin requires at
#      least 2 occurrences each of the 4 sentinel literals and the heredoc
#      reference; the negative pins forbid the buggy one-pipe form and the
#      literal-quote form (closes #1572 — surrounding double quotes in the
#      heredoc cause read_state to return `"claude-implement-larch3-"` with
#      literal quotes, so verify_cleanup_target's case-glob looks for a
#      basename starting with `"` and refuses rm-rf even when session-id-match=y).
# ---------------------------------------------------------------------------
declare -a clone_tag_pins=(
  "31a:CLONE_TAG_FULL=\$(basename \"\$PWD\"):basename capture"
  "31b:CLONE_TAG_FULL=\$(printf '%s' \"\$CLONE_TAG_FULL\" | tr -c 'A-Za-z0-9_-' '_'):sanitize step"
  "31c:CLONE_TAG_FULL=\${CLONE_TAG_FULL:0:32}:truncate to 32 chars"
  '31d:[ -n "$CLONE_TAG_FULL" ] || CLONE_TAG_FULL="_":empty-fallback to _'
  '31e:EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-${CLONE_TAG_FULL}-:heredoc reference (unquoted form)'
)
for clone_tag_pin in "${clone_tag_pins[@]}"; do
  pin_id="${clone_tag_pin%%:*}"
  rest="${clone_tag_pin#*:}"
  pin_lit="${rest%:*}"
  pin_desc="${rest##*:}"
  pin_count=$(grep -F -c "$pin_lit" "$SKILL_MD" || true)
  [[ "$pin_count" -ge 2 ]] \
    || fail "($pin_id) skills/implement/SKILL.md must apply $pin_desc at both Step 13.5 and Step 14 (found $pin_count, expected >= 2) — see #1563 / #1572"
done

clone_tag_buggy_idiom='basename "$PWD" | tr -c'
if grep -Fq "$clone_tag_buggy_idiom" "$SKILL_MD"; then
  fail "(31f) skills/implement/SKILL.md must NOT use the one-pipe CLONE_TAG form '$clone_tag_buggy_idiom' (tr sees basename's trailing newline before \$() strips it) — see #1563"
fi

clone_tag_quoted_form='EXPECTED_TMPDIR_BASENAME_PREFIX="claude-implement-'
if grep -Fq "$clone_tag_quoted_form" "$SKILL_MD"; then
  fail "(31g) skills/implement/SKILL.md must NOT use the quoted EXPECTED_TMPDIR_BASENAME_PREFIX form '$clone_tag_quoted_form...' — surrounding double quotes in the heredoc cause read_state to return the value with literal quotes, breaking verify_cleanup_target's case-glob — see #1572"
fi

echo "PASS: test-implement-structure.sh — structural invariants hold (assertion 5 retired)"
exit 0
