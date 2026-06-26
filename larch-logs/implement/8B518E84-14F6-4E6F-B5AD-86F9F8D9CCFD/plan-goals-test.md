## Goal
Implement issue #5422: [IMPLEMENTING] [BUG] /design Step 5c fails with PUBLISH_RC=4 when composed-plan.md not written before driver launch.

## Implementation Plan
## Summary

`/design` Step 5c consistently fails with `PUBLISH_RC=4` / `VALIDATE_STATUS=defects-found` because `$DESIGN_TMPDIR/composed-plan.md` is missing when `design-step5c.sh` is invoked. The composition step — which is the orchestrator's responsibility — is documented only in `skills/design/references/finalize-step5.md`, while `skills/design/SKILL.md` Step 5c shows the driver Bash fence immediately after a vague "Follow `finalize-step5.md` for composing..." sentence. An orchestrator reading SKILL.md interprets that sentence as describing something the driver does internally, launches the driver, and the driver fails closed because `composed-plan.md` is absent.

## Original report

The orchestrator skipped Step 5c item 1 (compose `composed-plan.md`) before invoking `design-step5c.sh`. Root cause traced to a gap between SKILL.md Step 5c wording and the actual pre-call requirement in `finalize-step5.md`. Suggestion: add explicit composition before the driver fence in SKILL.md, or have the Python driver auto-compose when the file is missing.

## Reproduction scenario

1. Run `/design <issue>` through to Gate C approval.
2. At Step 5c, the orchestrator reads `SKILL.md` Step 5c line 827: "Follow `finalize-step5.md` for composing the final plan block...".
3. The orchestrator interprets this as "follow the reference for context", not "compose a file before launching the driver".
4. The orchestrator launches `design-step5c.sh` via `run_in_background: true` without first writing `$DESIGN_TMPDIR/composed-plan.md`.
5. `python/cli.py design step5c` calls `design_publish.publish_core`, which checks for `composed-plan.md` at line 238–244 of `python/design_publish.py` and returns exit 4 with `VALIDATE_STATUS=defects-found` / `VALIDATE_DEFECT_COUNT=1`.
6. `PLAN_WRITE_OK=false` is emitted; the issue is never updated.

## Expected behavior

`composed-plan.md` is present before `design-step5c.sh` is launched, or the driver auto-composes it. The publish succeeds and the `larch:plan` block is written to GitHub.

## Observed behavior

`design-step5c.sh` exits with `PUBLISH_RC=4`, `PLAN_WRITE_OK=false`, `VALIDATE_STATUS=defects-found`, `VALIDATE_DEFECT_COUNT=1`. The `validate-plan-commands.log` shows `VALIDATE_STATUS=ok DEFECT_COUNT=0` because the driver never reached validation — it exited on the missing-file precondition check before running the validator.

## Root cause analysis

Two-part root cause:

**1. SKILL.md Step 5c does not make composition explicit as a pre-launch step.**

`SKILL.md` line 827 (`### 5c`): "Follow `finalize-step5.md` for composing the final plan block..." is immediately followed by the `design-step5c.sh` background Bash fence. There is no explicit numbered item, Write-tool call, or BEFORE-LAUNCH guard for `composed-plan.md` in SKILL.md itself. The anti-halt transition list mentions `5c.1` but those sub-items are only defined in `finalize-step5.md`, which an orchestrator may not load until after the fence.

**2. `python/cli.py design step5c` does not auto-compose when the file is missing.**

`design_publish.publish_core` (lines 238–244 of `python/design_publish.py`) exits 4 on a missing or empty `composed-plan.md` rather than composing it. The driver treats a missing file as a validator defect rather than auto-recovering.

The missing-composition special case is documented in SKILL.md (`### Plan command validator failure (shared)`, Step 5c missing-composition special case), but an orchestrator only reaches that error-recovery path after the driver has already failed — not before launch.

## Evidence

- `SKILL.md` Step 5c (lines 825–846 of installed `52.0.3/skills/design/SKILL.md`): no explicit Write or composition step before the `design-step5c.sh` fence.
- `finalize-step5.md` line 72: "Compose `$DESIGN_TMPDIR/composed-plan.md` containing `## Plan`, `## Acceptance`, and a trailing `diff_lines: <N>` line" — the actual composition instruction, buried in a reference file.
- `python/design_publish.py` lines 238–244: `if not composed_plan.is_file() or composed_plan.stat().st_size == 0: ... return 4`.
- SKILL.md anti-halt transition list (line 29): `5c.1→5c.5→5c.7→5c.8→6` — references sub-items but does not define them inline.
- Session run C9ED4659: `PUBLISH_RC=4`, `PLAN_WRITE_OK=false`, `validate-plan-commands.log` shows `VALIDATE_STATUS=ok DEFECT_COUNT=0` (validator never ran; file was absent).

## Affected files

- `skills/design/SKILL.md` — Step 5c section lacks an explicit pre-launch composition step.
- `skills/design/references/finalize-step5.md` — owns the composition instruction but not surfaced in SKILL.md before the fence.
- `python/design_publish.py` — `publish_core` exits 4 on missing file without auto-composing.
- `python/design_lifecycle.py` — `step5c_core` does not compose before calling `publish_core`.

## Suggested fix(es)

**Option A (preferred): auto-compose in the driver.**

In `step5c_core` (or `publish_core`), when `composed-plan.md` is missing, auto-compose it from `plan.txt`:
- `## Plan` = full `plan.txt` body up to the optional-trailer block.
- `## Acceptance` = derive from the plan's `## Testing strategy` section, or use a minimal "See Testing strategy in plan." one-liner.
- Append `diff_added:`, `diff_deleted:`, `mechanical_churn:`, and `diff_lines:` trailers from `plan.txt`.

This removes orchestrator ambiguity entirely and matches how other driver steps self-complete prerequisites.

**Option B: make the SKILL.md Step 5c composition step explicit.**

Before the `design-step5c.sh` background fence in SKILL.md, add an explicit numbered item 1:

```
#### Step 5c item 1 — Compose `$DESIGN_TMPDIR/composed-plan.md`

Using the Write tool, write `$DESIGN_TMPDIR/composed-plan.md` with:
- `## Plan` header followed by the body of `plan.txt` (excluding diff trailers).
- `## Acceptance` section with acceptance criteria derived from the plan.
- The same `diff_added:`, `diff_deleted:`, `mechanical_churn:`, and `diff_lines:` trailers as `plan.txt`.

**This step MUST complete before launching `design-step5c.sh`.**
```

Option A is preferred because it removes the LLM-authored intermediate artifact from the orchestrator hot path.

## Open questions

- Should `## Acceptance` in the auto-composed fallback be derived from the Testing Strategy section, or should it be a fixed placeholder referencing the plan?
- Is there a harness in `skills/design/scripts/test-design-step5c.sh` that should cover the missing-file auto-compose path?

## Test plan
(no test plan section in plan-file)
