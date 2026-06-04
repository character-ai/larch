## Decision 1: Scope is Phase 2 only
- **Question**: Which fences/files are in scope?
- **Resolution**: Only the Step 3 preview fold + Step 3 consumption-fence thinning. In scope: `run-step3-review.{sh,md}`, `emit-design-plan-preview.{sh,md}`, the SKILL.md Step 3 fence, `test-step3-orchestrator-fence.sh`, `test-design-structure.sh` (+ any harness made stale, e.g. `test-emit-design-plan-preview.sh`/`test-run-step3-review.sh`). Out of scope: the other Round II phases (3–7) and any non-Step-3 fence.
- **Source**: feature-description (issue #3417)

## Decision 2: Preview visibility must be preserved
- **Question**: Must the plan preview still reach chat, and when?
- **Resolution**: The plan preview must still be shown before the long-running review, on first Step 3 entry only (current `.step3-entry-plan-printed` sentinel-gated behavior). Re-entries (Gate C re-run, Gate B(c)/Gate C(b) → Gate A → Step 3) still suppress it. The folded preview routes through the captured FD-3 display stream so it survives `larch_quiet_init`.
- **Source**: feature-description (issue #3417) + codebase (`emit-design-plan-preview.sh`, `lib-quiet.sh`)

## Decision 3: No behavior change beyond the fold/thin
- **Question**: Any behavior change to the review panel or tier semantics?
- **Resolution**: None. The review panel, cap guard, round-cursor, result-env contract keys, branch matrix, and SIMPLE/HARD semantics are preserved. The change is mechanical: move the preview into the driver and collapse the orchestrator parse to the thin-fence shape.
- **Source**: feature-description (issue #3417)

## Decision 4: Green gates
- **Question**: What must pass?
- **Resolution**: `make lint` plus the named/affected harnesses (`test-step3-orchestrator-fence.sh`, `test-design-structure.sh`, and any touched `test-*-step3*`/`test-emit-design-plan-preview.sh`) green.
- **Source**: feature-description (issue #3417)
