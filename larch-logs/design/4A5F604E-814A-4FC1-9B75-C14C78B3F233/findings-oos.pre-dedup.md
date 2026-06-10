### OOS_1:
- **Description**: Thirteen new step wrappers have no dedicated offline harnesses beyond structural fence-shape checks. Scenario: Behavior drift in `step-8-ship.sh` / `step-0-bootstrap.sh` / `step-5-resume.sh` is only caught by broad structure tests or a single e2e smoke run; regressions may surface late
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/
- **Phase**: design

### OOS_1:
- **Description**: Fence-shape check #2 only forbids consecutive fences separated by blank lines, while acceptance text says no “2+ consecutive script-call fences” without that qualifier. Scenario: Prose-separated back-to-back fences (e.g. current Step 5 checks + resume pair) could satisfy the new harness yet miss the ~6-turn savings goal
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:43
- **Phase**: design

### OOS_1:
- **Description**: Failure modes and test-implement-fence-shape.sh only assert four load-bearing KV families (OOS_CHECKPOINT_RC EMIT_BODY routing-envelope STALL_TRACKING_*) while nine other wrappers lack per-script relay inventories comparable to skills/implement/scripts/step-7a.md:18-29. Scenario: Regression risk is real but the feature can ship with correct sibling .md contracts per plan line 88 without a new cross-wrapper relay harness in this PR
- **Reviewer**: Cursor-dyn-stdout-relay-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:88,153-157
- **Phase**: design

