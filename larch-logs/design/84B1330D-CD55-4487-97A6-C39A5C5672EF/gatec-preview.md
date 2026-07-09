## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

Add mechanical completeness enforcement around the design publish path so approved runs with present architectural guidelines cannot silently ship without `architectural-guideline-assessment.md`. Use a dedicated refusal envelope, fail-closed Step 5c orchestration that routes operators back to Gate C (not validator-autofix or Step 3), and commit-time completeness verification that receives the real consumer repo root.

## Approach

1. Reuse `larch.core.architectural_guidelines.read_guidelines()` and the existing `DESIGN_ASSESSMENT` artifact name.
2. Add `_check_guideline_assessment_completeness(...)` that returns a frozen result with `guidelines_status`, `required`, `present`, `artifact`, and `reason`. Treat `absent` and `invalid` as not required; treat symlink or non-regular files as missing.
3. Add `_emit_missing_guideline_assessment_refusal(...)` as a **dedicated** refusal emitter. Do **not** route through `_emit_publish_refusal`. Emit only `ARCH_GUIDE_*` rows plus `PUBLISH_REFUSE_REASON=missing-guideline-assessment`; leave `VALIDATE_STATUS=not-run` and do not stamp validator-defect shape (`VALIDATE_DEFECT_COUNT`, empty-log review-provenance routing).
4. In `publish_core()`, call the completeness helper **after** the validate / `--skip-validate` block and **before** redaction, plan-block write, rename, diagram upsert, or log-publish — regardless of `--skip-validate`.
5. On normal Step 5c absence when `required` and not `present`: call the dedicated emitter, write `.design-publish-result.env`, return rc `4`, and print a Gate C–directed operator warning naming `architectural-guideline-assessment.md`.
6. Wire a Step 5c special case in `skills/design/SKILL.md` and `skills/design/references/finalize-step5.md` **before** review-provenance (after missing-composition and plan-size cases) keyed on `PUBLISH_REFUSE_REASON=missing-guideline-assessment`: skip validator-autofix and Override; offer only **Return to Gate C** and **Cancel**. **Return to Gate C** resumes Gate C presentation and `persist-design-assessment` (`resume@4b` / Step 4b), then re-runs `design-step5c.sh`. **Cancel** preserves `$DESIGN_TMPDIR` and skips publish/rename/cleanup.
7. Add a degraded direct log-publish path for noninteractive or resume-style publishing when Gate C cannot re-run: append a `Warnings` execution issue naming `architectural-guideline-assessment.md`, write `.missing-guideline-assessment-warning`, stamp `final-summary.md`, and continue.
8. Emit machine lines from `architectural-guidelines persist-design-assessment` on every attempted call so audits can distinguish helper-not-called from helper-failed.
9. Extend design run-log completeness verification: require the assessment artifact only when the run outcome is approved (`approved` or `approved-partition`) **and** `read_guidelines(repo_root).status == "present"`, using a real consumer repo root and the existing execution-issue waiver mechanism. Thread `repo_root` through commit-time verification so ephemeral tmpdir staging cannot skip the check.
10. On `missing-guideline-assessment` refusal, do not write `.completed/step-5c`; classify rc `4` outside the `validator-defects` bucket so lifecycle tests and orchestration stay fail-closed.

## Files to modify/create

### UPDATED: python/larch/design/design_publish.py

Add:

- `@dataclass(frozen=True) GuidelineAssessmentCompleteness` (or equivalent frozen result) with `guidelines_status`, `required`, `present`, `artifact`, `reason`.
- `_check_guideline_assessment_completeness(*, design_tmpdir: Path, repo_root: Path, outcome: str = "approved")` using `consumer_repo_root() or plugin_root` for publish, matching the existing validator root. `required` is true only when outcome is approved and guidelines status is `present`; `present` requires `$DESIGN_TMPDIR/architectural-guideline-assessment.md` to be a regular, non-symlink file.
- `_emit_missing_guideline_assessment_refusal(*, design_tmpdir: Path, result: GuidelineAssessmentCompleteness, kvs: list[tuple[str, str]], result_env: Path) -> None` that:
  - prints an operator-visible warning directed at Gate C re-entry, naming `architectural-guideline-assessment.md` (not review-provenance text)
  - sets `ARCH_GUIDE_ASSESSMENT_REQUIRED=true`, `ARCH_GUIDE_ASSESSMENT_PRESENT=false`, `ARCH_GUIDE_ASSESSMENT_STATUS=missing`, `ARCH_GUIDE_ASSESSMENT_ARTIFACT=architectural-guideline-assessment.md`, `PUBLISH_REFUSE_REASON=missing-guideline-assessment`
  - leaves `VALIDATE_STATUS=not-run` (does not mutate to `defects-found`)
  - writes `.design-publish-result.env` and returns via caller rc `4`

In `publish_core()`, after review-provenance, pause, diagram, difficulty, and the validate / `--skip-validate` block, and before `redact secrets` / `named-block write`:

```python
completeness = _check_guideline_assessment_completeness(...)
if completeness.required and not completeness.present:
    _emit_missing_guideline_assessment_refusal(...)
    return 4
```

Do not gate this call on validate success or `skip_validate`.

### UPDATED: python/larch/design/design_step5c.py

Add `ARCH_GUIDE_ASSESSMENT_REQUIRED`, `ARCH_GUIDE_ASSESSMENT_PRESENT`, `ARCH_GUIDE_ASSESSMENT_STATUS`, and `ARCH_GUIDE_ASSESSMENT_ARTIFACT` to `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`.

Thread those values into `.design-step5c-status.env` and bgjob result envs.

**Fail-closed sentinel ordering (FINDING_7).** Do not write `.completed/step-5c` before refusal handling. After parsing `publish_rc` and `result_env`, branch on `PUBLISH_REFUSE_REASON` **before** touching `.completed/step-5c`:

- When `publish_rc == 4` and `PUBLISH_REFUSE_REASON=missing-guideline-assessment`: emit a distinct status (for example `STEP5C_STATUS=missing-guideline-assessment` or omit `STEP5C_STATUS` entirely), never `validator-defects`; do **not** write `.completed/step-5c`; return fail-closed with `CLEANUP_ELIGIBLE=false`.
- When `publish_rc == 4` and `PUBLISH_REFUSE_REASON=validator-defects`: keep existing `STEP5C_STATUS=validator-defects` behavior; still do not write `.completed/step-5c` when `PLAN_WRITE_OK=false`.
- Write `.completed/step-5c` only after the refusal branches, and only when `plan_write_ok == "true"` on a non-refusal success path.

### UPDATED: python/larch/design/design_log_publish_flow.py

Before `_render_final_summary_before_copy()` on approved outcomes in the final publish path (and on `--dry-run` only when it renders a final summary), run `_check_guideline_assessment_completeness(..., outcome=outcome)` in degraded mode.

When the artifact is required but missing:

- append a `Warnings` execution issue whose body names `architectural-guideline-assessment.md` (and slug `guideline-assessment` if helpful for waiver matching)
- write `$DESIGN_TMPDIR/.missing-guideline-assessment-warning`
- continue to render and commit logs

Pause publishes with non-approved outcomes skip the requirement. Present artifact suppresses the warning.

### UPDATED: python/larch/design/design_summary.py

When `.missing-guideline-assessment-warning` exists, prefix rendered summary (including fallback summary) with a short visible line:

`**⚠ Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**`

### UPDATED: python/larch/core/architectural_guidelines.py

Update `persist_design_assessment_main()` to emit machine-readable lines on every attempted call without changing the existing exit contract:

- `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ATTEMPTED=true`
- `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_GUIDELINES_STATUS=present|absent|invalid`
- `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT=ok|failed`
- `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON=<token>`
- `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ARTIFACT=architectural-guideline-assessment.md`

Present guidelines still require exactly one assessment source. Absent or invalid guidelines still remove stale assessment files.

### UPDATED: python/larch/report/run_log_manifest.py

Add helpers:

- `_design_run_approved(run_dir: Path) -> bool` — parse `final-summary.md` for an approved terminal outcome (`: approved` or `: approved-partition` in the `## /design run ...` header, aligned with `design_summary._VALID_OUTCOMES`)
- `_derive_consumer_repo_root_from_run_dir(run_dir: Path) -> Path | None` — derive consumer repo root from the run-directory tree (for example parent of `larch-logs/design/<run-id>`)

Extend `_required_design_artifacts(run_dir, *, repo_root: Path | None = None)` so it appends:

RequiredArtifact(
    slug="guideline-assessment",
    relative_path="architectural-guideline-assessment.md",
    skill="design",
    condition="design-guideline-assessment",
)

only when **all** hold:

- `_design_run_approved(run_dir)`
- resolved `repo_root` is non-empty
- `read_guidelines(repo_root).status == "present"`

Add optional `repo_root: Path | None = None` to `required_artifacts_for_run()` and `verify_run_log_completeness()`. When the caller supplies `repo_root`, use it directly; otherwise derive via `_derive_consumer_repo_root_from_run_dir`. Keep old logs tolerant: non-approved outcomes and absent/invalid guidelines do not add the row.

Pin degraded waiver body format in tests so `artifact_present_or_waived()` recognizes committed `Warnings` entries naming `architectural-guideline-assessment.md` or slug `guideline-assessment`, mirroring `test_artifact_present_or_waived_matches_design_capture_warning`.

### UPDATED: python/larch/report/run_log_commit.py

In `_copy_tree_to_repo_after_completeness()`, pass the already-resolved `repo_root` into `verify_run_log_completeness(run_dir=src, skill=skill, repo_root=repo_root)` so the approved design guideline-assessment check runs against the real consumer repo **before** the tree copy from the ephemeral tmpdir source. Keep derive-only fallback for audit callers without cwd context.

### UPDATED: skills/design/references/finalize-step5.md

Add a Step 5c special case **before** review-provenance (after missing-composition and plan-size branches):

When `--site` is `design Step 5c` and `PUBLISH_REFUSE_REASON=missing-guideline-assessment`:

- skip `python/cli.py plan validator-autofix` and Override
- preserve `$DESIGN_TMPDIR`
- offer exactly **Return to Gate C** and **Cancel**
- **Return to Gate C**: resume Gate C at Step 4b (`resume@4b`), run `architectural-guidelines present-note` then `persist-design-assessment`, then re-run `design-step5c.sh`
- **Cancel**: preserve tmpdir; skip redact, plan-block write, publish, rename, and Step 6 cleanup

Pin the operator-visible refusal warning text naming `architectural-guideline-assessment.md` and directing Gate C re-entry.

### UPDATED: skills/design/SKILL.md

Mirror the same Step 5c special case in the shared **Plan command validator failure** section, ordered before review-provenance:

**Step 5c missing-guideline-assessment special case.** If `--site` is `design Step 5c` and `PUBLISH_REFUSE_REASON=missing-guideline-assessment`, treat this as a publish precondition refusal, not review-provenance or validator-defect. Skip autofix and Override. Offer **Return to Gate C** and **Cancel** only. **Return to Gate C** resumes Step 4b Gate C presentation and assessment persistence, then re-runs `design-step5c.sh`. **Cancel** preserves `$DESIGN_TMPDIR`.

### UPDATED: python/tests/design/test_design_publish.py

Add publish-core tests:

- guidelines present, approved publish, missing assessment: rc `4`, no plan-block write, `PUBLISH_REFUSE_REASON=missing-guideline-assessment`, `VALIDATE_STATUS=not-run` (not `defects-found`), dedicated `ARCH_GUIDE_*` rows emitted, Gate C–directed warning printed
- guidelines present with regular `architectural-guideline-assessment.md`: publish proceeds
- guidelines absent or invalid: artifact not required
- `--skip-validate` with guidelines present and missing assessment: still rc `4` with `missing-guideline-assessment`

### UPDATED: python/tests/design/test_design_lifecycle.py

Extend Step 5c rc `4` contract coverage (FINDING_3):

- keep `test_step5c_core_rc4_emits_validator_status_sidecars_and_no_markers` for `PUBLISH_REFUSE_REASON=validator-defects` / `STEP5C_STATUS=validator-defects`
- add sibling `test_step5c_core_rc4_missing_guideline_assessment_not_validator_defects`: fake `publish_core` returns rc `4` with `PUBLISH_REFUSE_REASON=missing-guideline-assessment`, `VALIDATE_STATUS=not-run`, and `ARCH_GUIDE_ASSESSMENT_REQUIRED=true`; assert contract never contains `STEP5C_STATUS=validator-defects`, assert distinct status (for example `missing-guideline-assessment`) or absence of `STEP5C_STATUS`, assert `.completed/step-5c` is absent, and assert `CLEANUP_ELIGIBLE=false`

### UPDATED: python/tests/design/test_design_log_publish_flow.py

Add degraded publish tests:

- direct approved log-publish with guidelines present and missing artifact records a `Warnings` entry naming `architectural-guideline-assessment.md`, writes `.missing-guideline-assessment-warning`, and still reaches publish
- rendered or committed summary contains the visible warning prefix
- present artifact suppresses warning and marker

### UPDATED: python/tests/design/test_design_summary.py

Add coverage that `.missing-guideline-assessment-warning` is included in final summary and fallback summary rendering.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add persist machine-line tests:

- present guidelines plus clean assessment: `PERSIST_ATTEMPTED=true`, `PERSIST_RESULT=ok`
- absent or invalid guidelines: `PERSIST_RESULT=ok` with not-required reason
- invalid flags or missing assessment source: `PERSIST_ATTEMPTED=true`, `PERSIST_RESULT=failed`

### UPDATED: python/tests/report/test_run_logs.py

Add run-log completeness tests with pinned fixtures (FINDING_6):

- seed `final-summary.md` with `## /design run <id>: approved` (or `: approved-partition`)
- place a valid `ARCHITECTURAL_GUIDELINES.md` at the derived consumer repo root before asserting the `guideline-assessment` row is required
- approved design run with guidelines present and missing assessment reports missing `guideline-assessment:architectural-guideline-assessment.md`
- same run with artifact present passes
- same run with committed `Warnings` issue naming `architectural-guideline-assessment.md` passes as recorded degradation
- `failed-plan-write` or other non-approved outcomes do not require the artifact
- absent/invalid guidelines do not require the artifact
- waiver body format matches `artifact_present_or_waived` token rules
- commit-path test: `_copy_tree_to_repo_after_completeness()` with resolved `repo_root` fails before copy when assessment is required but missing

### MAY_UPDATE: skills/design/references/approval-gates.md

Only update if implementer decides Gate C persist machine lines need prompt-side documentation beyond `finalize-step5.md`. Do not use prose as the mechanical fix.

### MAY_UPDATE: scripts/test-design-structure.sh

Only update if `approval-gates.md` changes. Pin any changed Gate C prose per repo convention.

## Edge cases

- Guidelines `absent` or `invalid`: no artifact required; stale cleanup remains helper-owned.
- Missing artifact in normal Step 5c: fail before plan-block write, rename, diagram upsert, final-summary publish, or run-log commit; route through dedicated refusal envelope and Gate C special case, not review-provenance.
- Missing artifact in degraded direct log-publish: never silent; record execution issue and stamp summary.
- Symlink or non-regular assessment file: treat as missing.
- Execution-issue waiver must name `architectural-guideline-assessment.md` or slug `guideline-assessment`.
- `--skip-validate` does not bypass the completeness gate.
- `missing-guideline-assessment` refusal must not leave `.completed/step-5c`.
- Commit-time completeness without caller `repo_root` falls back to derive; commit path must pass the resolved consumer root.
- Companion invariant assessment remains out of scope.

## Failure modes

- If guideline status cannot be read, rely on `read_guidelines()` status; `invalid` means no artifact expected.
- If result-env write fails after refusal, keep existing rc/result-env fallback behavior.
- If degraded warning append fails, summary stamping should still attempt the visible warning.
- If summary rendering fails, fallback summary still shows the warning marker when present.
- If run-log repo root cannot be derived, skip adding the guideline-assessment required row rather than false-positive on placeholder roots.
- If `.completed/step-5c` were written before refusal parsing, Step 6 and pause/resume could treat the run as cleanly finalized; sentinel write must follow refusal classification.

## Testing strategy

Run focused tests only:

- `python3 -m pytest -q python/tests/design/test_design_publish.py -k 'guideline or publish'`
- `python3 -m pytest -q python/tests/design/test_design_lifecycle.py -k 'step5c_core_rc4 or missing_guideline'`
- `python3 -m pytest -q python/tests/design/test_design_log_publish_flow.py -k guideline`
- `python3 -m pytest -q python/tests/design/test_design_summary.py -k guideline`
- `python3 -m pytest -q python/tests/core/test_architectural_guidelines.py -k persist_design_assessment`
- `python3 -m pytest -q python/tests/report/test_run_logs.py -k 'design and guideline'`
- If Gate C prose changes: `make test-design-structure`

difficulty: HARD
diff_lines: 595
