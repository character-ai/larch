### [Plan Review] FINDING_2

### FINDING_2: Phase 2 scope bundles preview migration without turn reduction
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Phase 2 combines driver preview mode, sentinel migration, and a new test seam while deferring the original per–Step-3-entry turn-reduction goal. The plan still replaces the live uncaptured `emit-design-plan-preview.sh` fence with `run-step3-review.sh --preview-only` plus a second captured `--no-preview` call, adding mode flags, allowlist-gated sentinel logic, `RUN_STEP3_EMIT_PREVIEW_SH`, and eight new driver harness cases without reducing fence count or operator-visible turns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For a SIMPLE minimum-change Phase 2, collapse only the captured review handoff to the thin-fence shape and keep the existing live emit-design-plan-preview.sh --variant step3 fence and renderer-owned sentinel until a later phase when preview ownership can be paired with an actual turn win


### [Plan Review] FINDING_4

### FINDING_4: `--preview-only` must exit before `--round-cap` validation
- **Reviewer(s)**: Cursor-dyn-migration-completeness
- **Severity**: important
- **Concern**: The plan adds `--preview-only` but does not require the preview branch to terminate before the existing `--round-cap` requirement and review driver body. As written, `run-step3-review.sh --preview-only --design-tmpdir "$TMP"` would still hit `[[ -n "$ROUND_CAP" ]] || fail '--round-cap is required'` and exit 2, so the live preview fence prints nothing and Step 3 never reaches review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-migration-completeness: After handling preview capture/emit/sentinel touch, end the `--preview-only` branch with `exit 0` before `--round-cap` validation, tmpdir `cd`, cap guard, `plan-review-loop.sh`, and `.step3-review-result.env` writes


### [Plan Review] FINDING_5

### FINDING_5: Harness must split safe-env file-first vs stdout-only later-wins
- **Reviewer(s)**: Cursor-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: The harness spec conflates fill-missing stdout merge with later-wins without a safe-env-loaded branch. An implementer might apply `[[ -n ${!_key:-} ]]` fill-missing on every stdout-only path so an early fake `LOOP_STATUS=` wins over the driver terminal KV when no result env exists, regressing the later-wins case the plan is meant to fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-protocol-fidelity: Split harness instructions: when [[ -f … && ! -L … ]] load succeeds use file-first plus stdout fill-missing only; when no safe env was loaded assign allowlisted stdout KVs in stream order (later wins). Track _safe_env_loaded explicitly in apply_step3_handoff


