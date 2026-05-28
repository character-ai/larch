## Goal
Implement issue #2738: [IMPLEMENTING] Phase 4/4: phase_coder_select + final SKILL.md collapse + structural pin (umbrella #2732)\n\n## Context.

## Implementation Plan
## Plan

# Phase 4/4: phase_coder_select + final SKILL.md collapse + structural pin (umbrella #2732)

## Open questions for Gate C

**Implicit waterfall order — operator escalation flag (from DECISION_1 dialectic, 2-1 voted)**

The Phase 4 issue body (#2738) text and warning example specify `Cursor → Codex → Claude` ordering. The dialectic vote returned **THESIS=2, ANTI_THESIS=1** for adopting this order; the plan below follows that resolution.

However: **issue #2756 `[DONE]` "Switch to coder=codex default in /implement and fixer"** is a CLOSED landed product decision that put Codex-first into the current repo (SKILL.md L756 "Codex → Cursor → Claude", SECURITY.md L106, `scripts/test-implement-step2-routing.sh:31-32`). The dissenting Cursor judge cited #2756 as the binding contract.

**Operator must consciously approve the order reversal at Gate C.** If you intend Codex-first (i.e., #2756 stands and #2738's order text was illustrative-only), use Gate B's "Switch to discussion mode" or Gate C's "Discuss further" to revise the plan. Per FINDING_16, this Phase 4 plan reverses ONLY the `/implement` Step 0 omitted-`--coder` default; **fixer / review-and-fix dispatch remains Codex-first** (no changes to `skills/review-and-fix/scripts/review-and-fix.sh` or `scripts/lint-fix-loop.sh`). The plan below implements that narrow reversal.

## Approach

Phase 4 finishes the umbrella #2732 consolidation pattern Phases 1-3 established (`[DONE]` #2735 / #2736 / #2737):

1. **Coder selection moves into the script**: `phase_coder_select` in `scripts/implement-bootstrap.sh` becomes the sole authority for resolving the `/implement` Step 0 omitted-`--coder` default; the SKILL.md prompt-side `### Implementer waterfall` section is deleted. Fixer / `review-and-fix.sh` / `lint-fix-loop.sh` are NOT touched and remain on Codex-first per #2756.
2. **`--coder` argv added to the script**: parallels the existing `--issue-number` / `--run-id` / `--forked-target` argv style. SKILL.md Step 0 forwards the resolved value plus bumps `--up-to-phase plan` → `--up-to-phase coder`.
3. **Reuses existing infrastructure end-to-end** (FINDING_1 fix — no local shadowing): `phase_coder_select` references `phase_infra`'s already-exported `codex_available` / `cursor_available` module globals directly. The four probe keys (`CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`) are re-read via `read-session-env-key.sh` only for tri-state `*_BINARY_FOUND` classification on the explicit-coder unavailable path. `lib-quiet.sh` `emit_kv` / `emit` / `larch_err` / `emit_breadcrumb` are reused unchanged. `larch_quiet_truthy` (FINDING_10 fix) gates the coder breadcrumb to match existing breadcrumb helpers.
4. **REPO_UNAVAILABLE / missing-plan gate** (FINDING_2 fix): `phase_coder_select` itself early-returns when `${REPO_UNAVAILABLE:-false}` is `true` or when `${PLAN_FILE:-}` is empty / non-existent — Step 2 dispatch requires both, so a populated `coder=` on a path lacking plan artifacts would be a silent Step 2 break. The orchestrator-side bail routing table also gains a row that skips Step 2 when `PLAN_FILE` is empty (REPO_UNAVAILABLE paths bail before Step 1.r naturally via the existing route).
5. **Permissive phase guard** (DECISION_2 unanimous): `should_run_post_tracking_phase` drops the `DEFERRED!=true` arm and matches `should_run_phase_plan_materialize`'s permissive predicate so every plan-materializing path also resolves `coder=`. DEFERRED stops being a coder-skip trigger; the new REPO_UNAVAILABLE / missing-plan guard above handles the non-implementing paths.
6. **SKILL.md Step 0 collapse**: target ~80 lines (±20%) for the Session Setup subsection (the operational subsection between `## Step 0 — Session Setup` and `### Cross-Skill Presence Propagation`). Other subsections inside the `<!-- step:0 ... <!-- step:2` span (Cross-Skill Presence Propagation, Phantom Untracked Probe, Execution Issues Tracking, Rebase Macro 1.r) stay in place.
7. **Structural pin** in `scripts/test-implement-structure.sh` (FINDING_4 fix — narrowed scope, FINDING_17 fix — drop Larch-log pin): pin the **Session Setup subsection** only (using `## Step 0 — Session Setup` to `## Phantom Untracked Probe` as the anchor range — narrower than the full `step:0` span). Inside that narrowed range: ≤1 fenced bash block, exactly one `implement-bootstrap.sh` invocation, `--up-to-phase coder` literal, foreground banner + per-anchor comment present. Resume-tail invocation lives in the dirty-tree recovery subsection and is pinned separately (allowing one initial + one resume-tail call). Update existing pins to drop deleted-heading anchors including the Larch-log section.
8. **Warning style** (per Round 1 user answer): use the issue-body example phrasing (`**⚠ Cursor unavailable — falling back to Codex implementer.**`) for the two implicit-waterfall transition points. The explicit-coder-unavailable hard-error warnings (`**⚠ /implement Step 0 (implementer waterfall): --coder=<X> requested but ...**`) remain verbatim per the issue's "with the specific bullet's warning text" wording.
9. **`coder_fallback=true` semantics** (per Round 1 user answer): set only on implicit-waterfall arrival at Claude (both externals down). Explicit `--coder=claude` does NOT set the flag.
10. **Cross-file alignment** (per Round 1 user answer #3 + FINDING_9, FINDING_14, FINDING_19): bundle SECURITY.md update (multiple paragraphs, not just L106), `scripts/test-implement-step2-routing.sh` + sibling `.md` retarget, `skills/implement/scripts/test-implement-bootstrap.sh` sibling `.md`, `scripts/test-implement-structure.sh` sibling `.md`, plus retargeting `docs/linting.md` and `skills/shared/subskill-invocation.md` references to the deleted `### Implementer waterfall` heading — all in the same PR so `make lint` stays green.
11. **`step2-implement.sh` `--coder` required** (FINDING_6 fix): make `--coder` required in `step2-implement.sh` (matching the already-required `run-step2-dispatch.sh` contract). This removes the second authority for coder defaults and aligns the contract with "bootstrap is the sole `/implement` Step 0 omitted-`--coder` authority".
12. **CLAUDE_PLUGIN_ROOT recovery** (FINDING_13 fix): keep one top-of-fence recovery block at the very top of the single Session-Setup fence (before the `implement-bootstrap.sh` call). Only the duplicated per-fence boilerplate is removed; the canonical recovery line stays. The dirty-tree resume-tail fence uses the same one-line recovery before its bootstrap invocation.

## Files to modify/create

### UPDATED: `scripts/implement-bootstrap.sh`

**Argv parser additions** in `main()` (around L970-1029):
- Add `--coder` case: accepts exactly one of `claude` | `codex` | `cursor`; sets `CODER_OPT` module variable. Argv validation rejects other values via `die_usage "--coder must be claude, codex, or cursor"`.
- Initialize `CODER_OPT=""` at top of script alongside other option variables.

**Widen `should_run_post_tracking_phase`** (currently L184-188): drop the `[ "${DEFERRED:-false}" != "true" ]` arm so the predicate becomes `[ -z "${IMPLEMENT_BAIL_REASON:-}" ] && [ "${STALL_TRACKING:-false}" != "true" ]`. Update the function-level comment to reflect "skips on hard bail or stall only — REPO_UNAVAILABLE / missing-plan skip is handled inside `phase_coder_select`".

**Replace `phase_coder_select` stub** (L911-914) with the full implementation. Key correctness rules (FINDING_1, FINDING_8, FINDING_10 fixes):

- No local `codex_available` / `cursor_available` declarations — read the existing `phase_infra` globals directly.
- Four-key re-read is for tri-state `*_BINARY_FOUND` classification only.
- Breadcrumb emission centralized at the end of `phase_coder_select` after both explicit / implicit branches return, only fires when `coder` is non-empty AND `IMPLEMENT_BAIL_REASON` is empty.
- Breadcrumb gate uses `larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"`.

```bash
phase_coder_select() {
    # Belt-and-suspenders: skip on bail / stall (the case-block guard already enforces this).
    [ -z "${IMPLEMENT_BAIL_REASON:-}" ] || return 0
    [ "${STALL_TRACKING:-false}" != "true" ] || return 0

    # REPO_UNAVAILABLE / missing-plan gate (FINDING_2). These paths must not produce
    # coder= since Step 2 dispatch requires plan.txt + feature-description.txt.
    if [ "${REPO_UNAVAILABLE:-false}" = "true" ] || [ -z "${PLAN_FILE:-}" ] || [ ! -f "${PLAN_FILE:-/nonexistent}" ]; then
        return 0
    fi

    # Re-read the four probe keys from session-env. These are consumed only by the
    # tri-state classifier in _phase_coder_explicit; phase_infra's codex_available /
    # cursor_available globals drive the routing decisions.
    local codex_binary_found cursor_binary_found
    codex_binary_found=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default "")
    cursor_binary_found=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default "")

    if [ -n "$CODER_OPT" ]; then
        _phase_coder_explicit "$CODER_OPT" "$codex_binary_found" "$cursor_binary_found"
    else
        _phase_coder_implicit
    fi

    # Single centralized breadcrumb emission (FINDING_8). Fires for any successful
    # selection (explicit or implicit) and stays silent on bail paths.
    emit_coder_breadcrumb_if_enabled
    return 0
}

_phase_coder_explicit() {
    local choice=$1 codex_binary_found=$2 cursor_binary_found=$3
    case "$choice" in
        claude)
            coder=claude
            ;;
        cursor)
            if [ "${cursor_available:-false}" = "true" ]; then
                coder=cursor
            else
                _phase_coder_explicit_unavailable cursor "$cursor_binary_found"
            fi
            ;;
        codex)
            if [ "${codex_available:-false}" = "true" ]; then
                coder=codex
            else
                _phase_coder_explicit_unavailable codex "$codex_binary_found"
            fi
            ;;
    esac
}

_phase_coder_explicit_unavailable() {
    local tool=$1 binary_found=$2
    local tool_caps  # for the warning text
    case "$tool" in
        cursor) tool_caps=Cursor ;;
        codex)  tool_caps=Codex  ;;
    esac
    local other1 other2
    case "$tool" in
        cursor) other1=codex; other2=claude ;;
        codex)  other1=cursor; other2=claude ;;
    esac
    if [ "$binary_found" = "false" ]; then
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${tool_caps} binary not found. Re-run without --coder, or with --coder=${other1}|${other2}.**"
    elif [ -z "$binary_found" ]; then
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${tool_caps^^}_BINARY_FOUND could not be determined (Step 0 may have failed). Re-run to re-probe.**"
    else
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${tool_caps} runtime probe failed / auth error. Re-run without --coder, or with --coder=${other1}|${other2}.**"
    fi
    IMPLEMENT_BAIL_REASON=coder-unavailable
    STALL_TRACKING=true
}

_phase_coder_implicit() {
    # Per Phase 4 issue body (#2738): Cursor → Codex → Claude waterfall for the
    # /implement Step 0 omitted-`--coder` default. Fixer/review-and-fix remains
    # Codex-first per #2756 (different consumer, not touched by Phase 4).
    if [ "${cursor_available:-false}" = "true" ]; then
        coder=cursor
        return 0
    fi
    larch_err "**⚠ Cursor unavailable — falling back to Codex implementer.**"
    _phase_coder_append_warning "Step 0 — Cursor unavailable: waterfall fallback to codex"
    if [ "${codex_available:-false}" = "true" ]; then
        coder=codex
        return 0
    fi
    larch_err "**⚠ Codex unavailable — falling back to Claude implementer.**"
    _phase_coder_append_warning "Step 0 — Cursor and Codex unavailable: waterfall fallback to claude"
    coder=claude
    coder_fallback=true
    _phase_coder_manifest_fallback || true
}

# FINDING_5 fix: write the synthetic warning to a temp file rather than piping via
# /dev/stdin. append-tool-failure.sh requires --output-file to name a real readable
# file; /dev/stdin is not portable as a file path under bash 3.2 on macOS.
_phase_coder_append_warning() {
    local message=$1 tmpfile
    tmpfile=$(mktemp "${IMPLEMENT_TMPDIR:-${TMPDIR:-/tmp}}/larch-coder-warn.XXXXXX") || return 0
    printf '%s\n' "$message" >"$tmpfile"
    "$SCRIPT_DIR/append-tool-failure.sh" \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "Step 0 (implementer waterfall)" \
        --tool "phase_coder_select" \
        --exit-code 0 \
        --category Warnings \
        --output-file "$tmpfile" >/dev/null 2>&1 || true
    rm -f "$tmpfile"
}

_phase_coder_manifest_fallback() {
    if [ -z "${RUN_ID:-}" ]; then
        return 0
    fi
    "$SCRIPT_DIR/larch-log.sh" manifest \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --field coder_fallback=true >/dev/null 2>&1 || true
}

emit_coder_breadcrumb_if_enabled() {
    if ! larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        return 0
    fi
    # Centralized emission. Skip on bail paths (coder empty) so the existing
    # "bail paths don't emit phase-success breadcrumbs" convention holds.
    if [ -z "${coder:-}" ] || [ -n "${IMPLEMENT_BAIL_REASON:-}" ]; then
        return 0
    fi
    emit_breadcrumb "→ step0: coder=${coder}"
}
```

**Module global initializations** alongside other phase globals near the top of the script:
- `coder=""` (populated by `phase_coder_select`)
- `coder_fallback=""` (populated by `phase_coder_select` only on implicit→claude path)
- `CODER_OPT=""` (parsed by `main()`)

**`emit_final_tail` adjustments** (around L964-965): no signature change — the existing `emit_kv coder ""` / `emit_kv coder_fallback ""` lines become `emit_kv coder "${coder:-}"` / `emit_kv coder_fallback "${coder_fallback:-}"` so the populated globals flow through.

**Token / timing marks**: add `LARCH_TIMING_SKILL=implement … timing-ledger.sh mark "implement Step 0 — coder select"` and matching `token-ledger.sh mark` calls inside `phase_coder_select` so SKILL.md doesn't need them.

### UPDATED: `scripts/implement-bootstrap.md`

**Argv table**: add `--coder` row:
- `--coder` | no | `claude` \| `codex` \| `cursor` | When set, pins the explicit implementer. On availability mismatch emits the verbatim three-variant warning text + `STALL_TRACKING=true` + `IMPLEMENT_BAIL_REASON=coder-unavailable`. When omitted, the implicit Cursor → Codex → Claude waterfall runs.

**Bail-reason enum** (L82-93): drop `not-yet-implemented-phase-4` row; add `coder-unavailable` row:
- `coder-unavailable` | Explicit `--coder` value's external tool was unavailable at probe time (binary missing, binary present but probe failed, or BINARY_FOUND undeterminable). Tri-state warning text on stderr; `STALL_TRACKING=true`. Operator must re-run with a different `--coder` value or without `--coder` to engage the implicit waterfall.

**Behavior mapping (Step 0 SKILL.md)** table: add row:
- `### Implementer waterfall` (prompt-side waterfall) → `phase_coder_select` (script-side).

**Phase-skip semantics** (L95-97): replace the "Phase 4 keeps the stricter `should_run_post_tracking_phase`, which also skips when `DEFERRED=true`" sentence with: "Phase 4's `should_run_post_tracking_phase` is permissive in the same way as `should_run_phase_plan_materialize`: it runs whenever there is no hard bail and no stall. DEFERRED is intentionally NOT a skip trigger. **REPO_UNAVAILABLE / missing-plan skip is enforced inside `phase_coder_select` itself**, not the guard predicate — when `REPO_UNAVAILABLE=true` or `PLAN_FILE` is empty / non-existent, `phase_coder_select` returns early without populating `coder=`."

**Outputs section** (L29-47): add `coder` and `coder_fallback` to the documented KV tail with semantics:
- `coder` — final implementer choice (`claude` | `codex` | `cursor`). Empty when REPO_UNAVAILABLE / missing-plan path bypassed coder selection, when the case-block guard skipped the phase, or on explicit-coder-unavailable bail.
- `coder_fallback` — `true` only on the implicit waterfall arrival at Claude (both externals down). Empty otherwise (including explicit `--coder=claude`).

Append (FINDING_12 fix): "`diff_lines: <N>` in `plan.txt` is informational sizing context — it does NOT route the implementer. See `scripts/implement-bootstrap.sh` `phase_coder_select` and the bail table above for the actual routing logic."

**Breadcrumbs section** (L57-70): remove "Future Phase 4 may add `→ step0: coder=…`" speculative wording and replace with normative: "`phase_coder_select` emits `→ step0: coder=<claude|codex|cursor>` once a coder is resolved. The breadcrumb fires from a single shared tail after both explicit and implicit branches return, gated on `larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"` and on `coder` being non-empty AND `IMPLEMENT_BAIL_REASON` being empty. Bail paths (`coder-unavailable`) and REPO_UNAVAILABLE / missing-plan early-return paths skip the breadcrumb."

**Edit-in-sync section** (L131-135): expand to include (FINDING_9, FINDING_14, FINDING_19 fixes):
- `SECURITY.md` (default-implementer order documentation in multiple paragraphs).
- `scripts/test-implement-step2-routing.sh` + sibling `.md` (waterfall heading + order pins).
- `skills/implement/scripts/test-implement-bootstrap.md` (test case naming + breadcrumb assertions).
- `scripts/test-implement-structure.md` (Step 0 structural pin documentation).
- `docs/linting.md` (cross-reference to deleted heading).
- `skills/shared/subskill-invocation.md` (cross-reference to deleted heading).
- `skills/implement/scripts/step2-implement.sh` + sibling `.md` (FINDING_6 fix — `--coder` now required).

### UPDATED: `skills/implement/SKILL.md`

**Anti-halt continuation reminder** at L14: change the "after `implement-bootstrap.sh` exits, continue to Step 1.r" wording per the Phase 4 issue body.

**Step 0 Session Setup subsection collapse**: target ~80 lines for the operational Session Setup subsection (between `## Step 0 — Session Setup` heading and `### Cross-Skill Presence Propagation`).

- Delete `### Step 0 — tracking issue adoption` (L666-710 — entire sub-section).
- Delete `### Larch-log Batches and Summary Comments` (L711-735) — move semantic content into `scripts/implement-bootstrap.md`'s Outputs section.
- Delete `### Plan materialization from issue body` (L736-741).
- Delete `### Implementer waterfall` (L742-779) — the entire prompt-side waterfall section.
- Delete **duplicate** inline `CLAUDE_PLUGIN_ROOT` rehydration boilerplate from Step 0 fenced bash blocks. **Retain one top-of-fence recovery line** in the single remaining Session-Setup operational fence (FINDING_13 fix); the dirty-tree resume-tail fence keeps the same one-line recovery.

- Keep `### Cross-Skill Presence Propagation` (L551-552).
- Keep `## Phantom Untracked Probe` (L553-575).
- Keep `## Execution Issues Tracking` (L576-665) and all its h3 sub-sections.
- Keep `### Rebase onto latest main (before implementation)` (L780-801) — Step 1.r.

**Bootstrap invocation update**: at the four Step 0 call sites:
- L297 prose reference: update `--up-to-phase plan` → `--up-to-phase coder` (and the surrounding prose enumerating parsed KV keys to include `coder`, `coder_fallback`).
- L394 main invocation: bump `--up-to-phase plan` → `--up-to-phase coder`; add `--coder "$coder"` when `$coder` is set (from the slash-command argv parsing).
- L478 dirty-tree recovery prose: change `--up-to-phase plan --resume-plan-tail` → `--up-to-phase coder --resume-plan-tail`.
- L510 dirty-tree recovery invocation: same bump + forward `--coder "$coder"`.

**KV scan extension**: extend `_ib_kv_scan` to include `coder` and `coder_fallback` arms.

**Bail routing table**: add a row for `IMPLEMENT_BAIL_REASON=coder-unavailable` → "skip to Step 18 (`STALL_TRACKING=true` already set by the script)".

**Step 2.4 messaging cleanup** (FINDING_3 fix): the existing Step 2.4 conditions reference `coder_explicit` / `coder_fallback_target` which were prompt-side variables; the deletion of the waterfall section removes their definitions. Replace those Step 2.4 branches with conditions on the parsed `coder_fallback` (now sourced from bootstrap KV) plus a preserved boolean indicating whether the operator passed `--coder` on the slash-command argv (e.g., `coder_explicit_argv=true`). The two-warning text from Step 2.4 ("When the orchestrator earlier reported Codex unavailable / unavailable AND coder=codex was NOT explicitly requested" and "When coder=claude AND coder_explicit=true") is rewritten in terms of those two parsed/argv signals.

**Default-implementer wording at L756-760**: this content is in the deleted `### Implementer waterfall` section. The replacement is the bail routing table + the `--coder` argv documentation; no new prompt-side waterfall prose is added.

### UPDATED: `SECURITY.md`

**Multi-paragraph update** (FINDING_9, FINDING_16 fixes):

- **L90 paragraph** (External tool delegation, "/implement resolves the omitted-`--coder` implementer in Step 0"): replace `### Implementer waterfall` cross-reference with "`phase_coder_select` in `scripts/implement-bootstrap.sh`". Update the order text: "Step 2 implementation then consumes that resolved `--coder` and, when `--coder` was still omitted upstream, routes by external availability: Cursor → Codex → Claude (main agent only when both are unavailable)". (The rest of the paragraph about explicit `--coder=cursor` and Codex fallback launcher mechanics is unchanged.)

- **L106 paragraph** (Current omitted-`--coder` routing): change `Codex → Cursor → Claude by external availability` → `Cursor → Codex → Claude by external availability`. Update example: "This can select Codex without an explicit `--coder=codex` when Cursor is unavailable; the Codex implementer trust model above applies to that fallback path".

- **Add adjacency sentence** (FINDING_16 — narrow scope): "Phase 4 (#2738, umbrella #2732) reverses **only the omitted-`--coder` `/implement` Step 0 default** from the Codex-first ordering landed by issue #2756 [DONE] back to Cursor-first per the Phase 4 issue body. Fixer / `review-and-fix.sh` / `lint-fix-loop.sh` dispatch is NOT touched by Phase 4 and remains on the Codex-first contract from #2756. Operators relying on the Codex-first `/implement` default should re-pin via explicit `--coder=codex` until the next product-direction review."

- **L94 dialectic debater paragraph**: no order text here; verify no SKILL-heading cross-references that need updating.

- **L142 paragraph** (External Cursor / Codex filesystem access): no order text here; no changes needed.

### UPDATED: `scripts/test-implement-step2-routing.sh`

**L31** (`### Implementer waterfall` heading anchor): this heading is deleted from SKILL.md by Phase 4 — drop this assertion entirely.

**L32** (`Codex → Cursor → Claude` order pin): change to `Cursor → Codex → Claude` and retarget the assertion to `scripts/implement-bootstrap.md` (where the implicit waterfall is now documented).

**L36-40** (`--coder=codex requested but Codex binary not found` etc.): the explicit-coder-unavailable warning strings move from SKILL.md to `scripts/implement-bootstrap.sh` via `larch_err`. Retarget the pins to `scripts/implement-bootstrap.sh` so the assertions still pass.

**L38** (`When \`coder_explicit=true\`...` assert_not_contains): keep — asserts old wording does not return.

**L40** (`Cursor and Codex both unavailable`): the both-down warning string moves from SKILL.md to `scripts/implement-bootstrap.sh`. Retarget the pin to `scripts/implement-bootstrap.sh`.

### UPDATED: `scripts/test-implement-step2-routing.md`

(FINDING_14 fix — sibling `.md` update). Update the harness contract documentation to reflect the retargeted pins: the heading anchor is gone; order text is now in `scripts/implement-bootstrap.md`; explicit-coder warnings live in `scripts/implement-bootstrap.sh`.

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh`

Add coder-related test cases. Per FINDING_7 (label collision), use **B11-B17** as the new range, picking up after the existing B5 (current highest B-prefix). This is sequential, non-colliding, and groups Phase 4's tests in one contiguous block.

- **B11-coder-explicit-cursor-available**: `--up-to-phase coder --coder=cursor` with cursor available. Expected: `coder=cursor`, `coder_fallback=` (empty), `→ step0: coder=cursor` breadcrumb, no warning. (Happy-path explicit; covers FINDING_1 regression — confirms `phase_infra` global is consumed correctly.)

- **B12-coder-explicit-codex-available**: same but `--coder=codex` with codex available. Expected: `coder=codex`, no fallback, breadcrumb fires.

- **B13-coder-explicit-claude**: `--coder=claude`. Expected: `coder=claude`, `coder_fallback=` (empty — explicit choice is not fallback), breadcrumb fires.

- **B14-coder-explicit-cursor-unavailable**: `--coder=cursor` with cursor unavailable (use `LARCH_TEST_CURSOR_AVAILABLE=false`). Expected: `IMPLEMENT_BAIL_REASON=coder-unavailable`, `STALL_TRACKING=true`, stderr contains the verbatim `/implement Step 0 (implementer waterfall): --coder=cursor requested but ...` warning, `coder=` empty, `coder_fallback=` empty, NO `→ step0: coder=` breadcrumb.

- **B14-coder-explicit-codex-unavailable**: same shape for `--coder=codex` + codex unavailable.

- **B14-coder-explicit-binary-undeterminable**: `--coder=cursor` with `CURSOR_BINARY_FOUND` absent from session-env. Expected: `coder-unavailable` + STALL + warning text mentioning "could not be determined (Step 0 may have failed)".

- **B15-coder-implicit-cursor-available**: no `--coder`; cursor available. Expected: `coder=cursor`, no `coder_fallback`, no implicit-waterfall warning, breadcrumb fires.

- **B15-coder-implicit-cursor-down-codex-available**: no `--coder`; cursor unavailable, codex available. Expected: `coder=codex`, no `coder_fallback`, stderr contains `**⚠ Cursor unavailable — falling back to Codex implementer.**`, Warnings entry `Step 0 — Cursor unavailable: waterfall fallback to codex`, breadcrumb fires.

- **B15-coder-implicit-both-down**: no `--coder`; cursor + codex unavailable. Expected: `coder=claude`, `coder_fallback=true`, stderr contains both fallback warnings, Warnings entry `Step 0 — Cursor and Codex unavailable: waterfall fallback to claude`, `larch-log.sh manifest --field coder_fallback=true` invocation captured in invoke-log, breadcrumb fires.

- **B16-coder-skip-repo-unavailable** (FINDING_2 fix coverage): `--up-to-phase coder` with `REPO_UNAVAILABLE=true`. Expected: `phase_coder_select` early-returns; `coder=` empty; `coder_fallback=` empty; NO breadcrumb; NO bail (existing REPO_UNAVAILABLE bail / skip handled upstream).

- **B16-coder-skip-missing-plan** (FINDING_2 fix coverage): `--up-to-phase coder` reaches `phase_coder_select` but `PLAN_FILE` is empty (plan materialization skipped for non-REPO_UNAVAILABLE reasons). Expected: same as B16-repo-unavailable.

- **B17-breadcrumb-count-5**: deterministic happy-path scenario with `LARCH_QUIET_BREADCRUMBS=1`. Construct sandbox so all 4 prior breadcrumbs fire (infra ready + tracking adopted + branch + plan-logged + larch:plan posted) AND `phase_coder_select` succeeds. Total assertion: exactly 5 lines matching `^→ step0:` in stdout.

- **Update B4-all + B5-all assertions** (existing): now that `phase_coder_select` runs on DEFERRED paths under the widened guard, B4-all (deferred / POSTED=false) MUST also assert `coder=cursor|codex|claude` is populated and `→ step0: coder=...` breadcrumb fires. B5-all (tracking-init-failed STALL_TRACKING bail) MUST assert `coder=` remains empty (stall short-circuits).

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.md`

(FINDING_14 fix — sibling `.md` update). Document the new B11-B17 test case range, the test-seam env vars (`LARCH_TEST_CURSOR_AVAILABLE`, `LARCH_TEST_CODEX_AVAILABLE`, `LARCH_TEST_LARCH_LOG_RECORD`, etc. — confirm names match the harness conventions), and the assertion contracts (KV expectations, stderr expectations, invoke-log expectations).

### UPDATED: `scripts/test-implement-structure.sh`

**Drop existing pins anchored on deleted SKILL.md headings**:
- L390-391: `### Step 0 — tracking issue adoption` heading pin → DROP.
- L401-407: SKILL.md `token-ledger Step 0 — tracking issue` / `timing-ledger Step 0 — tracking issue` mark pins → DROP; these marks now live inside `scripts/implement-bootstrap.sh` (via the existing Phase 2 absorption).
- L414-417: existing pins on `implement-bootstrap.sh` retain `implement Step 0 — plan materialization` marks — KEEP. (Verify the line numbers shift with implement-bootstrap.sh growth from Phase 4.)
- L418-419: `Plan materialization is now fully owned by ...` SKILL.md pin → DROP.
- **FINDING_17 fix**: drop any positive pin on `### Larch-log Batches and Summary Comments` heading (verify L-range with grep; the section is deleted, the pin must go).

**Add new Step 0 Session Setup structural pins** (FINDING_4 fix — narrowed scope):

```bash
# Narrowed anchor range: the Session Setup operational subsection only.
# The full step:0 ... step:2 span includes Cross-Skill Presence Propagation,
# Phantom Untracked Probe, Execution Issues Tracking, and Rebase Macro 1.r,
# which retain their own fences and prose. The Session Setup subsection is
# between '## Step 0 — Session Setup' and the first '### Cross-Skill Presence'
# h3 (or '## Phantom Untracked Probe' h2 if Cross-Skill is moved). Use a
# narrow awk pattern that matches the operational subsection only.
session_setup_block_count=$(awk '
  /^## Step 0 — Session Setup$/        { in_section=1; next }
  /^## Phantom Untracked Probe$/       { in_section=0 }
  /^### Cross-Skill Presence Propagation$/ { in_section=0 }
  in_section && /^```bash$/ { c++ }
  END { print c+0 }
' "$SKILL_MD")
[[ "$session_setup_block_count" -le 1 ]] \
  || fail "SKILL.md Step 0 Session Setup must contain at most 1 fenced bash block (found $session_setup_block_count)"

# Pin: that single Session Setup fence contains exactly one implement-bootstrap.sh
# invocation. (The dirty-tree resume-tail invocation lives in a SEPARATE fence
# outside the Session Setup subsection and is pinned independently below.)
session_setup_bootstrap_count=$(awk '
  /^## Step 0 — Session Setup$/        { in_section=1; next }
  /^## Phantom Untracked Probe$/       { in_section=0 }
  /^### Cross-Skill Presence Propagation$/ { in_section=0 }
  in_section { print }
' "$SKILL_MD" | grep -cE 'implement-bootstrap\.sh')
[[ "$session_setup_bootstrap_count" -eq 1 ]] \
  || fail "SKILL.md Step 0 Session Setup must invoke implement-bootstrap.sh exactly once (found $session_setup_bootstrap_count)"

# Pin: --up-to-phase coder literal in the Session Setup fence.
grep -Fq -- '--up-to-phase coder' "$SKILL_MD" \
  || fail "SKILL.md Step 0 Session Setup must invoke implement-bootstrap.sh with --up-to-phase coder"

# Pin: foreground banner inside the Session Setup fence.
# Note: the Session Setup fence is foreground-only (implement-bootstrap.sh is NOT
# on the Family B background-denylist for this fence — it runs synchronously and
# the orchestrator parses KV output directly). Pin only the "Foreground required:"
# style comment; the "Background pair required" comment is reserved for genuine
# Family B background+monitor pairs in other fences.
grep -Fq '# Foreground required: see BASH_AUTHORING.md §4' "$SKILL_MD" \
  || fail "SKILL.md Step 0 Session Setup fence must include the foreground banner comment"

# Pin: KV scan exports coder and coder_fallback.
grep -Fq 'coder=' "$SKILL_MD" \
  || fail "SKILL.md Step 0 must parse the coder KV"
grep -Fq 'coder_fallback=' "$SKILL_MD" \
  || fail "SKILL.md Step 0 must parse the coder_fallback KV"

# Pin: phase_coder_select breadcrumb writer lives in implement-bootstrap.sh.
grep -Fq '→ step0: coder=' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must emit the → step0: coder= breadcrumb"

# Pin: SKILL.md no longer references the old prompt-side waterfall section.
! grep -Fq '### Implementer waterfall' "$SKILL_MD" \
  || fail "SKILL.md must no longer contain the prompt-side ### Implementer waterfall section (absorbed into phase_coder_select)"

# Pin: no leftover not-yet-implemented-phase-* strings in implement-bootstrap.sh.
! grep -E 'not-yet-implemented-phase-[0-9]+' "$REPO_ROOT/scripts/implement-bootstrap.sh" >/dev/null \
  || fail "implement-bootstrap.sh must not retain any not-yet-implemented-phase-* transitional bail values"

# Pin: dirty-tree resume-tail invocation is allowed once outside the Session Setup
# fence (in the dirty-tree recovery subsection).
resume_tail_count=$(grep -cE -- '--up-to-phase[[:space:]]+coder[[:space:]]+--resume-plan-tail' "$SKILL_MD")
[[ "$resume_tail_count" -eq 1 ]] \
  || fail "SKILL.md must contain exactly one dirty-tree resume-tail invocation (--up-to-phase coder --resume-plan-tail) (found $resume_tail_count)"
```

### UPDATED: `scripts/test-implement-structure.md`

(FINDING_14 fix — sibling `.md` update). Document the new Session Setup structural pins, the narrowed anchor range, the resume-tail allowance, and the dropped Larch-log / tracking-issue-adoption / plan-materialization-ownership pins.

### UPDATED: `skills/implement/scripts/step2-implement.sh`

(FINDING_6 fix). Make `--coder` a required argv flag (matching `run-step2-dispatch.sh`'s already-required contract). Remove the current Codex-first default fallback inside `step2-implement.sh` since bootstrap (via `phase_coder_select`) is now the sole authority for `/implement` Step 0 omitted-`--coder` routing. Print a clear error and exit non-zero when `--coder` is absent.

### UPDATED: `skills/implement/scripts/step2-implement.md`

Document the `--coder` requirement; remove the legacy default-fallback documentation; note that the prompt-side `/implement` orchestrator always passes `--coder` (resolved either from the user's slash-command argv or from bootstrap's `coder` KV output).

### UPDATED: `docs/linting.md`

(FINDING_19 fix). Find and update any references to `### Implementer waterfall` or "Codex → Cursor → Claude" (in the `/implement` Step 0 context). Retarget to `scripts/implement-bootstrap.md` (`phase_coder_select` section). Keep references to "Codex → Cursor → Claude" that target fixer / `review-and-fix.sh` / `lint-fix-loop.sh` unchanged.

### UPDATED: `skills/shared/subskill-invocation.md`

(FINDING_19 fix). Find and update any references to the deleted `### Implementer waterfall` heading. Retarget to "Preflight plus Step 0 bootstrap plan materialization" or to `scripts/implement-bootstrap.md` (whichever fits the cross-reference context).

## Edge cases

1. **Tri-state explicit-coder unavailability**: `CURSOR_BINARY_FOUND` and `CODEX_BINARY_FOUND` can be `true`, `false`, or empty (undeterminable when Step 0 failed early). The classifier in `_phase_coder_explicit_unavailable` MUST handle all three cases — empty input must NOT silently fall through to the implicit waterfall on the explicit path; it must emit the undeterminable warning + `STALL_TRACKING=true`.

2. **`coder_fallback=true` scope creep**: only set on implicit `cursor → codex → claude` arriving at Claude. Explicit `--coder=claude` does NOT set the flag. Intermediate fallback (Cursor unavailable → Codex available, `coder=codex`) does NOT set the flag.

3. **DEFERRED + `phase_coder_select`**: with the widened guard, DEFERRED paths run `phase_coder_select`. On DEFERRED runs where plan materialized AND repo is available, coder selection succeeds and `coder=` is populated. The new REPO_UNAVAILABLE / missing-plan early-return handles non-implementing paths (DEFERRED with no plan, fork-mode pure-defer).

4. **REPO_UNAVAILABLE coupling**: `phase_plan_materialize` is gated by `should_run_phase_plan_materialize` which already drops on `REPO_UNAVAILABLE=true`. The new `should_run_post_tracking_phase` does NOT check REPO_UNAVAILABLE in the predicate; `phase_coder_select` checks `REPO_UNAVAILABLE` internally and early-returns without populating `coder=`. This keeps the guard predicate symmetric across phases (both permissive) while preserving the operational invariant (no `coder=` without `plan.txt`).

5. **Bail order preservation**: `phase_coder_select` MUST NOT overwrite an existing `IMPLEMENT_BAIL_REASON` (the F7 class regression from #2732 prior phases). The function early-returns at the top when `IMPLEMENT_BAIL_REASON` is non-empty.

6. **Breadcrumb count determinism**: the "exactly 5" assertion requires the deterministic happy-path scenario to also produce the other 4 breadcrumbs (`infra ready`, `tracking adopted`, `branch + plan logged`, `larch:plan posted`). If `LARCH_QUIET_BREADCRUMB_FD` is set, breadcrumbs go to a dedicated FD; the test reads from the right FD. Construct the test sandbox so `LARCH_TEST_POSTED=true` to fire `larch:plan posted`.

7. **`larch-log.sh manifest --field coder_fallback=true` best-effort failure**: the helper redirects stdout/stderr to /dev/null and unconditionally returns 0 (`|| true`). The KV tail emission of `coder_fallback=true` is the authoritative signal; the manifest update is informational.

8. **Empty `$RUN_ID`**: on stalled-tracking paths, `RUN_ID` may be empty. The `_phase_coder_manifest_fallback` helper short-circuits when `RUN_ID` is empty (returns 0 without attempting the call). This prevents a malformed `larch-log.sh manifest --run-id ""` invocation.

9. **Warning helper tempfile cleanup** (FINDING_5 fix): `_phase_coder_append_warning` writes to a `mktemp` file under `$IMPLEMENT_TMPDIR` or `$TMPDIR` and removes it after `append-tool-failure.sh` returns. On `mktemp` failure the helper returns 0 silently — synthetic warnings are best-effort surface text, not load-bearing.

10. **`larch_quiet_truthy` semantics** (FINDING_10 fix): the breadcrumb helper uses `larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"` so values like `0`, empty, `false`, `no` are treated as disabled (matching the helper's contract). Any non-zero / non-empty / non-false / non-no value enables.

## Failure modes (top 3)

1. **Cursor judge dissent on order (DECISION_1 2-1 split)** — Phase 4 plan implements Cursor → Codex → Claude per dialectic vote, but landed product issue #2756 explicitly switched to Codex-first. Earliest warning signal: Gate C user pushes back or `make lint` fails on `test-implement-step2-routing.sh` if the order pin update misses a callsite. Mitigation: prominent `## Open questions for Gate C` callout at the top of this plan with the explicit Phase 4 narrow-reversal scoping (FINDING_16); SECURITY.md updates are paired across all routing paragraphs in the same commit; pre-merge transcript shows the user consciously approved the order reversal.

2. **`should_run_post_tracking_phase` widening + REPO_UNAVAILABLE / missing-plan internal gate** — Two-layer change: widen the predicate, add the internal early-return. Earliest warning signal: B16-coder-skip-repo-unavailable or B16-coder-skip-missing-plan test fails (asserting `coder=` stays empty), OR B4-all asserts `coder=` populated and fails because the new internal gate over-skipped. Mitigation: the new B16 tests pin the new contract explicitly; the updated B4-all and B5-all assertions cover the existing DEFERRED / stall paths; sibling `.md` documents the split between guard predicate and internal gate.

3. **Inline rehydration partial removal breaks dirty-tree recovery** — SKILL.md Step 0 currently re-derives `CLAUDE_PLUGIN_ROOT` inside fenced bash blocks for resilience. Removing duplicates while keeping one top-of-fence canonical recovery (FINDING_13 fix) requires per-fence audit. Earliest warning signal: dirty-tree recovery path fails with "CLAUDE_PLUGIN_ROOT unbound" on `--resume-plan-tail` re-entry from a degraded session-env. Mitigation: keep one canonical `CLAUDE_PLUGIN_ROOT` recovery line at the very top of the single Session-Setup fence AND at the top of the dirty-tree resume-tail fence; only remove the per-fence duplicates inside operational blocks; the new structural pin allows this exact shape (one initial + one resume-tail invocation).

## Testing strategy

1. **`make test-implement-bootstrap`** must pass with the new B11-B17 test cases plus updated B4-all/B5-all assertions.
2. **`make test-implement-structure`** must pass with the narrowed Step 0 Session Setup pins, dropped legacy pins (tracking-issue-adoption / plan-materialization-ownership / Larch-log section), and the new resume-tail allowance pin.
3. **`make test-implement-step2-routing`** must pass after the retargeted pins (heading drop + order text + explicit-coder warning relocation + sibling `.md` update).
4. **`make lint`** (full pre-commit hook chain) must pass, including any agent-lint S030 path pins.
5. **Manual smoke transcript**: a `/implement <issue>` invocation on clean main shows exactly 1 Bash call for Step 0 Session Setup (excluding 1.r Rebase Macro and excluding dirty-tree resume-tail) and 5 operator-visible `→ step0:` breadcrumbs.
6. **Manual smoke transcript** for explicit-coder-unavailable: `/implement --coder=cursor <issue>` with Cursor unavailable shows the verbatim warning + STALL + skip to Step 18.
7. **Manual smoke transcript** for implicit→claude: `/implement <issue>` with both externals unavailable shows both fallback warnings, `coder=claude`, and the manifest update to `coder_fallback=true`.
8. **SECURITY.md review**: confirm no other paragraph references the old `/implement` Step 0 Codex-first order; only the L90 + L106 + adjacency sentence changes (fixer references remain Codex-first per FINDING_16).
9. **Phase-skip sanity**: verify `should_run_post_tracking_phase` still blocks coder selection on `tracking-init-failed`, `run-flags-persist-failed`, `dirty-tree`, `branch-create-failed`, `adopted-issue-closed`, `adopted-issue-is-pr` bail paths.
10. **Step 2 dispatcher consumer**: verify `step2-implement.sh` rejects invocations without `--coder` after the FINDING_6 fix; verify `/implement` orchestrator always passes `--coder` from bootstrap KV in the happy path.
11. **Cross-reference sweep**: grep `docs/linting.md`, `skills/shared/subskill-invocation.md`, and any other documentation for stale references to `### Implementer waterfall` or the old SKILL.md L756 wording.

## Acceptance

- `/implement <issue>` transcript on a clean main branch shows exactly 1 Bash call for Step 0 Session Setup (excluding the post-Step-0 Rebase Macro 1.r and excluding any dirty-tree resume-tail call) and 5 operator-visible `→ step0:` breadcrumbs (`infra ready`, `tracking adopted`, `branch + plan logged`, `larch:plan posted`, `coder=<value>`).
- SKILL.md Step 0 Session Setup subsection prose is ~80 lines (target ±20%); the four deleted sub-sections (`### Step 0 — tracking issue adoption`, `### Larch-log Batches and Summary Comments`, `### Plan materialization from issue body`, `### Implementer waterfall`) are gone, and the retained sibling sections (Cross-Skill Presence Propagation, Phantom Untracked Probe, Execution Issues Tracking, Rebase Macro 1.r) remain in place.
- `make lint` passes including `test-implement-structure`, `test-implement-bootstrap`, and `test-implement-step2-routing` with their new pins and dropped legacy anchors.
- `scripts/implement-bootstrap.sh` contains no `not-yet-implemented-phase-N` strings; bail enum gains `coder-unavailable` and drops `not-yet-implemented-phase-4`; `phase_coder_select` is fully implemented per the plan (no shadowing of `phase_infra` globals; tri-state explicit-coder classifier; centralized breadcrumb emission gated by `larch_quiet_truthy`; REPO_UNAVAILABLE / missing-plan early-return; `coder_fallback=true` only on implicit→claude path).
- `skills/implement/scripts/step2-implement.sh` requires `--coder` (FINDING_6); sibling `.md` documents the requirement.
- SECURITY.md routing references are updated to the narrowed reversal scope (Phase 4 reverses ONLY the `/implement` Step 0 omitted-`--coder` default; fixer / review-and-fix.sh / lint-fix-loop.sh remain Codex-first per #2756).
- `docs/linting.md` and `skills/shared/subskill-invocation.md` no longer reference the deleted `### Implementer waterfall` heading.
- `SECURITY.md` reviewed; trust model section confirmed updated (or unchanged where appropriate).
- No regression in existing `make test-implement-*` harnesses; B4-all/B5-all assertions updated for the widened phase guard.

diff_lines: 1180

## Test plan
(no test plan section in plan-file)
