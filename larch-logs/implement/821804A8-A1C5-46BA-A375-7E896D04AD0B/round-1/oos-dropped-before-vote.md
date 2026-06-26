### OOS_1: [OUT_OF_SCOPE] Preread failure does not abort launch (residual path after preflight)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `cursor_preread_service_token` logs on `-w` failure but does not abort launch, unlike plan fix option 2. Preflight now reads `-w` so divergence is unlikely; residual launch-without-key path remains if preread fails after preflight passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fold preread failure into preflight abort or short-circuit launch when CURSOR_API_KEY remains unset after preread.

### OOS_2: [OUT_OF_SCOPE] WI3 in-process auth failure detection before retry not implemented
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: latent
- **Concern**: WI3 fix #2 (detect in-process auth failure before the unclassified-empty retry) is not implemented; the branch relies entirely on `_review_cursor_write_result` postprocessing. That is a reasonable trade-off given the new backstop, but if a retry ever returns a canned sentinel with plausible non-zero `usage`, the collector could still score it clean until a separate guard exists.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Plan inlining introduces unbounded prompt growth risk
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: latent
- **Concern**: Plan inlining removes the workspace-scope failure mode but introduces unbounded prompt growth: `plan.txt` has no 64 KiB cap (unlike `--feature-file` / `--body-file`), so very large plans may hit Cursor context limits and produce shallow or sentinel-only output; operational risk is amplified by this change but not newly introduced as a size policy.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Duplicate keychain `-w` reads between preflight and preread
- **Reviewer(s)**: dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: nit
- **Concern**: Preflight and preread each invoke a separate keychain `-w` read (preflight discards stdout). A narrow TOCTOU window remains between the two calls; folding token capture into preflight and reusing the captured value in preread would remove the duplicate probe.
- **Suggested revisions (informational for voters; coder decides)**:

