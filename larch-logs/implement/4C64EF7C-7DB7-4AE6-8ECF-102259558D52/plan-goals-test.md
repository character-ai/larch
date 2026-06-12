## Goal
Implement issue #4057: [IMPLEMENTING] [BUG] design post-mortem 61A4DB5D: derive() slot attribution case-sensitivity +…\n\ndesign post-mortem 61A4DB5D: derive() slot attribution case-sensitivity + --no-dedup on OOS recovery.

## Implementation Plan
design post-mortem 61A4DB5D: derive() slot attribution case-sensitivity + --no-dedup on OOS recovery

Two bugs surfaced during design session 61A4DB5D-3573-48C0-A4F4-C2BCFA9BB1CB (issue #3927, F3e tracking-issue migration).

## Bug 1 — `render-review-phase-detail.sh derive()` misattributes mixed-case dynamic slot names

**Symptom.** The Top Reviewers section in the final summary issued `unknown/Cursor-dyn-contract-parity` instead of `cursor/Cursor-dyn-contract-parity` (or `dynamic/cursor-dyn-contract-parity`).

**Root cause.** `scripts/render-review-phase-detail.sh` uses a fallback `derive()` awk function when a slot has no panel-manifest entry (dynamic slots never do). The function contains case-sensitive patterns:

```awk
if (core ~ /^(cursor|codex|claude_sub|claude)-/) {
    vendor = core; sub(/-.*$/, "", vendor)
    ...
    return vendor "/" rest
}
...
return "unknown/" core
```

The dynamic Cursor slot was named `Cursor-dyn-contract-parity` (capital C from the dynamic slot naming convention). `^cursor-` does not match `Cursor-`. The `^dyn-` branch also misses because the name starts with `Cursor-dyn-`, not a bare `dyn-`. The function falls through to `return "unknown/" core`.

**Suggested fix.** Normalize `core` to lowercase once at the top of `derive()`, before all pattern tests:

```awk
function derive(b,    core, rest, vendor, arch) {
    core = b
    sub(/\.txt$/, "", core)
    sub(/-output-ns-retry$/, "", core)
    sub(/-output$/, "", core)
    sub(/-ns-retry$/, "", core)
    core = tolower(core)   # add: normalize before pattern tests
    ...
```

One-line change. No behavioral change for static slots (already lowercase). Fixes all mixed-case dynamic slot names.

**File:** `scripts/render-review-phase-detail.sh:91` (`derive()` body).

---

## Bug 2 — `design-step5b-annotate.sh` writes sentinel on rc=1; manual OOS recovery path omits `--no-dedup`

### 2a: Sentinel written on annotate failure

**Symptom.** `design-step5b-annotate.sh` was called before `/larch:issue` created the OOS issues (sequencing error). `oos-issue.stdout.txt` was empty, so `file-design-oos.sh annotate` exited rc=1. Despite rc=1, `design-step5b-annotate.sh` wrote the `step-5b` sentinel and logged the failure as a warning only. The orchestrator saw `STEP5B_STATUS=annotate-complete` and proceeded to Step 5c.

**Root cause.** `design-step5b-annotate.sh` writes its sentinel unconditionally regardless of annotate rc. The rc=1 path only appends to `execution-issues.md`; it does not gate the sentinel. The sentinel's purpose is to prove Step 5b ran successfully — writing it on failure defeats that purpose and hides sequencing errors from downstream steps.

**Suggested fix.** Gate the sentinel write on annotate rc:

```bash
if [[ "$OOS_ANN_RC" -ne 0 ]]; then
    # Do NOT write step-5b sentinel — annotate failed; Step 5c must not proceed
    emit_kv STEP5B_STATUS annotate-failed
    exit "$OOS_ANN_RC"
fi
: > "$DESIGN_TMPDIR/.completed/step-5b"
emit_kv STEP5B_STATUS annotate-complete
```

**File:** `skills/design/scripts/design-step5b-annotate.sh`.

### 2b: `--no-dedup` missing in manual OOS recovery

**What happened.** When recovering from the premature annotate call, `/larch:issue` was invoked manually without `--no-dedup`. The full Phase 1/2 dedup + dep-analysis pipeline ran.

**Root cause.** The normal `file-design-oos.sh` flow invokes `/larch:issue` with `--no-dedup` because OOS items are archival — unique per design session, so dedup is always wasteful. When the orchestrator bypassed `file-design-oos.sh` and called `/larch:issue` directly, `--no-dedup` was not part of the mental model.

Note: `--no-dedup` and `--blocked-by-issue` are mutually exclusive per the `/issue` SKILL.md. The normal OOS path handles this correctly: `--blocked-by-issue` is NOT used in the `/larch:issue` call; the blocker edge is applied separately via `issue add-blocked-by` after creation.

**Suggested fix.** Document the correct manual OOS recovery sequence in `skills/design/SKILL.md` Step 5b:

```
# Manual OOS recovery when design-step5b-annotate.sh ran before /larch:issue:
1. /larch:issue --no-dedup --input-file <oos-combined.md> \
     --title-prefix "[OOS]" --label "enhancement"
   (do NOT use --blocked-by-issue — mutually exclusive with --no-dedup)
2. Capture stdout to oos-issue.stdout.txt
3. Apply blocker manually:
   python3 python/cli.py issue add-blocked-by \
     --client-issue <OOS_NUM> --blocker-issue <TRACKING_NUM> --repo <REPO>
4. bash $CLAUDE_PLUGIN_ROOT/skills/design/scripts/file-design-oos.sh annotate
```

**Files:**
- `skills/design/SKILL.md` Step 5b — recovery docs.
- `skills/design/scripts/design-step5b-annotate.sh` — sentinel gate (see 2a above).

## Test plan
(no test plan section in plan-file)
