# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Renderer payload-accounting test coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The renderer lacks CI coverage for greater-than-12000-byte ledger truncation, calibration feedback, plan-exclusion/specialist inline-diff paths, and stale sidecar reads after failed writes, so payload_bytes regressions could silently clamp scaffold_bytes to zero or distort rankings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Add tests for emitted truncated ledger sections and non-empty calibration feedback payload bytes
  - From cursor-specialist-testing: Add focused rendering tests with explicit byte expectations including a greater-than-12000-byte ledger truncation pin and a pre-seeded stale sidecar failed-write case.
  - From codex-specialist-testing: Add the omitted focused renderer tests


### FINDING_4: Sidecar cleanup must stay best-effort
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Reviewer-launcher sidecar cleanup can abort dispatch on non-ENOENT unlink errors even though telemetry should not block launch, so cleanup needs to suppress best-effort OSError failures and remain covered by an unlink-failure test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Suppress OSError for pre/post payload sidecar cleanup in _review_launcher.py and _claude_runner.py
  - From codex-specialist-testing: Suppress OSError for launcher sidecar cleanup and test unlink failure after successful render


### FINDING_5: Launch and waterfall payload routing need coverage
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Per-tool payload values, prompt-file env fallback, dynamic-slot folding, and skip-invalid payload drop behavior are not fully exercised in launch_review/waterfall paths, so payload metadata can drift or malformed rows can break strict runs without CI noticing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add tests that differing per-tool payload values reach child env and TSV for waterfall, voters, prompt-file launches, and dynamic slots
  - From cursor-specialist-testing: Add launch_review prompt-file test reading LARCH_PANEL_PAYLOAD_BYTES; add waterfall skip-invalid fixtures for bad payload_bytes and payload_files.


### FINDING_6: Voter payload-files routing is only lightly tested
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Code-review voter tests only check payload_files keys, so distinct per-tool payload counts or active-tool env threading could regress while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Stub per-tool renders with distinct sidecar counts; assert manifest payload_files values and dispatched env LARCH_PANEL_PAYLOAD_BYTES match the selected tool.
  - From codex-specialist-testing: Write distinct sidecar counts per tool and assert manifest values plus active-tool env threading


### FINDING_7: Aggregator payload composition is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The aggregate path does not assert that initial payload_bytes equals the UTF-8 byte sum of the findings anchor and required reviewer inventory, so missing components could silently inflate scaffold_bytes for aggregator slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add single-attempt aggregate test asserting initial manifest payload_bytes equals sum of findings anchor and inventory section UTF-8 lengths.
