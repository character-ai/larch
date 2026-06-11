## Goal
Implement issue #4025: [IMPLEMENTING] [BUG] (URGENT) /design: free-form recap emitted after publish; run-log PR merge state mis-reported\n\n## Summary.

## Implementation Plan
## Summary

Two behavioral bugs were observed at the end of the `/design 3982` run (session `claude-design-larch3-n2bkxnow`, PR #4020). Both involve the orchestrator violating explicit SKILL.md contracts after `design-publish.sh` returned `PUBLISH_OK=true`.

---

## Bug 1: Free-form recap emitted after `design-publish.sh` instead of `final-summary.md`

### Context

`skills/design/SKILL.md` (anti-halt rule) states verbatim:

> After Step 5c `design-publish.sh` returns (`_publish_rc` 0, 1, or 3), NEVER write a free-form natural-language recap summary: no "Design complete." line, no artifact bullet list, no parenthetical cost paraphrase… The only orchestrator-text addition permitted after that driver handoff is the shared verbatim full-body emission of `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`.

### Symptom

After `design-publish.sh` returned `PUBLISH_OK=true PR_NUMBER=4020`, the orchestrator emitted:

> "The design run is complete. The tmpdir was cleaned before I could capture final-summary.md, but all work is durable on GitHub: plan written to issue #3982, issue renamed [DESIGNED], PR #4020 created..."

This is a bullet-point recap — exactly the pattern the anti-halt rule forbids.

### Root cause

Two sub-causes combined:

1. **Wrong cleanup order.** The step-6 sentinel write and `session cleanup-tmpdir` were invoked before `final-summary.md` was read. The correct order (per the SKILL.md sentinel table) is: write `step-6` sentinel → emit `final-summary.md` if present → `session cleanup-tmpdir`. Running cleanup first destroyed the file.

2. **Substituted a prohibited free-form recap for absent content.** After the tmpdir was cleaned and `final-summary.md` was gone, the correct behavior is to emit nothing (the `[ -s ... ]` guard evaluates false; no fallback text is permitted). Instead, the orchestrator substituted self-authored prose. The skill contract does not define any fallback for an absent `final-summary.md` — absence means silence.

### Suggested fix

**Procedural (orchestrator behavior):**
- Enforce the canonical order: write `step-6` sentinel → `[ -s "$FINAL_SUMMARY_PATH" ] && cat "$FINAL_SUMMARY_PATH"` → `session cleanup-tmpdir`. Never invert the emit and cleanup calls.
- If `final-summary.md` is absent after cleanup (or was never written), emit nothing. No prose, no bullets, no "Design complete." line.

**Script-level (defensive):**
- Consider having `design-step-final-summary.sh` write `final-summary.md` to a path outside `$DESIGN_TMPDIR` (e.g., under `$SESSION_TMPDIR`) so a premature `cleanup-tmpdir` call cannot destroy it before it is read.

---

## Bug 2: Run-log PR merge state mis-reported (`DESIGNED_ADMISSION_READY` conflated with PR merge eligibility)

### Context

Run-log PRs (title: `chore(larch-logs): design run …`) are documentation commits. They auto-merge when CI passes, independent of `DESIGNED_ADMISSION_READY`. `DESIGNED_ADMISSION_READY` is the `/implement` preflight admission gate — it has no bearing on whether a run-log PR can be merged.

### Symptom

After `design-publish.sh` returned `DESIGNED_ADMISSION_READY=false PR_NUMBER=4020`, the user asked "Did you merge the PR?" and the orchestrator replied:

> "No. The /design skill created PR #4020 (a design run-log PR) but does not merge it. `DESIGNED_ADMISSION_READY=false` in the publish output means it's not eligible for auto-merge at this point."

This was wrong on two counts:
- `DESIGNED_ADMISSION_READY=false` is an implementation admission gate, not a merge flag for run-log PRs.
- The PR had already auto-merged when CI passed (30/30 checks green). The claim "it's not eligible for auto-merge" was false.

### Root cause

The orchestrator pattern-matched `DESIGNED_ADMISSION_READY=false` from the publish output and inferred "not ready to merge" — a field-meaning confusion. The correct response required one `gh pr view 4020` call to read the actual PR state. Instead, the orchestrator answered from stale inference without verification.

The deeper failure: the orchestrator had sufficient knowledge that run-log PRs auto-merge on CI green (this is documented behavior) but did not apply it. Inference from an unrelated field overrode direct knowledge.

### Suggested fix

**Procedural (orchestrator behavior):**
- When asked about the state of a PR, always run `gh pr view <N>` before answering. Do not infer merge state from fields in `design-publish.sh` output that are not merge flags.
- `DESIGNED_ADMISSION_READY` must only ever be interpreted as the `/implement` preflight gate. If the orchestrator mentions it in a PR-merge context, that is a mis-application.

**Documentation (defensive):**
- Consider adding an explicit note to `design-publish.sh`'s output contract (or `docs/run-logs.md`) clarifying that `DESIGNED_ADMISSION_READY` controls `/implement` preflight and has no relation to run-log PR merge eligibility.

---

## Reproduction context

- Session: `claude-design-larch3-n2bkxnow`
- Issue: #3982
- PR: #4020 (merged, all 30 CI checks green)
- Larch version: 49.0.16
- Skill: `skills/design/SKILL.md` (SIMPLE tier)


## Test plan
(no test plan section in plan-file)
