### OOS_1: [OUT_OF_SCOPE] waterfall panel instrumentation via inherited `LARCH_PANEL_ARTIFACT_DIR`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-panel-env
- **Severity**: latent
- **Concern**: `agent_waterfall` instruments slots when `LARCH_PANEL_ARTIFACT_DIR` is inherited from parent env without `--panel-artifact-dir`. A stale panel env in a dev shell could instrument non-panel waterfall callers (e.g. decompose) whose slot names satisfy `_panel_slot_kind_from_env`. With current subprocess isolation and empty parent `LARCH_PANEL_SLOT`, main paths stay clean, but the gate is environment-sensitive rather than flag-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-panel-env: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] flock lock timeout silently skips panel prompt-size rows
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Flock acquisition uses a 5s timeout and silently skips the row on failure (stderr warning only). Under heavy parallel panel dispatch a committed log could miss slots without failing dispatch. Operators relying on complete per-slot coverage should watch for `flock lock acquisition failed` warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] panel TSV test coverage gaps (negative paths and row counts)
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-panel-env
- **Severity**: latent
- **Concern**: The branch adds env-forwarding coverage but does not add the plan's explicit regressions that non-panel `launch-review` callers leave `panel-prompt-sizes.tsv` absent and that panel dispatch produces count-based TSV rows. Current tests mostly verify `--panel-artifact-dir` / env forwarding, not end-to-end row creation or negative paths. Helpful hardening against the stated opt-in contract, not a confirmed production defect on the happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-panel-env: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] `review_dispatch_panel` round-subdir fallback latent for today's main paths
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: latent
- **Concern**: `review_dispatch_panel`'s missing round-subdir fallback is latent for today's main paths: `/implement` Step 5 already passes a `round-<N>` tmpdir via `round_runner.py`, so implement acceptance paths are covered; the gap matters mainly for future or alternate review tmpdir layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: Address the concern above.
