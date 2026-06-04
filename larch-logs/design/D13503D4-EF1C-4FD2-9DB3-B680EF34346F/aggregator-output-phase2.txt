Normalizing the seven reviewer inputs into a structured finding list. Checking the codebase only to tighten titles and concerns—not to re-review.
Structured aggregator output (seven distinct findings; no merges — different fixes and code paths).

### FINDING_1: Duplicate WARN= in thin-fence display echo
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned thin-fence display pass echoes captured lines outside the 12-key allowlist while WARN= is also replayed in the parse loop. WARN= matches KEY=value shape but is not allowlisted, so both paths emit the same line and operators see duplicate WARN breadcrumbs when a safe `.step3-review-result.env` was loaded (typical rc=0 path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the SKILL.md thin fence, run one pre-parse loop over _plan_review_out that printf display lines only when the key is not in the 12-key set and is not WARN; mirror the same exclusion in test-step3-orchestrator-fence.sh apply_step3_handoff

### FINDING_2: Phase 2 scope bundles preview migration without turn reduction
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Phase 2 combines driver preview mode, sentinel migration, and a new test seam while deferring the original per–Step-3-entry turn-reduction goal. The plan still replaces the live uncaptured `emit-design-plan-preview.sh` fence with `run-step3-review.sh --preview-only` plus a second captured `--no-preview` call, adding mode flags, allowlist-gated sentinel logic, `RUN_STEP3_EMIT_PREVIEW_SH`, and eight new driver harness cases without reducing fence count or operator-visible turns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For a SIMPLE minimum-change Phase 2, collapse only the captured review handoff to the thin-fence shape and keep the existing live emit-design-plan-preview.sh --variant step3 fence and renderer-owned sentinel until a later phase when preview ownership can be paired with an actual turn win

### FINDING_3: Missing argv reject test for conflicting preview flags
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned mutually exclusive `--preview-only` / `--no-preview` contract has no planned reject-path assertion. Per repo argv-coverage rules, an implementation could silently pick one mode when both flags are passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one argv test in test-run-step3-review.sh asserting --preview-only --no-preview exits 2 with the pinned conflict message, alongside the existing missing/unknown option tests

### FINDING_4: `--preview-only` must exit before `--round-cap` validation
- **Reviewer(s)**: Cursor-dyn-migration-completeness
- **Severity**: important
- **Concern**: The plan adds `--preview-only` but does not require the preview branch to terminate before the existing `--round-cap` requirement and review driver body. As written, `run-step3-review.sh --preview-only --design-tmpdir "$TMP"` would still hit `[[ -n "$ROUND_CAP" ]] || fail '--round-cap is required'` and exit 2, so the live preview fence prints nothing and Step 3 never reaches review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-migration-completeness: After handling preview capture/emit/sentinel touch, end the `--preview-only` branch with `exit 0` before `--round-cap` validation, tmpdir `cd`, cap guard, `plan-review-loop.sh`, and `.step3-review-result.env` writes

### FINDING_5: Harness must split safe-env file-first vs stdout-only later-wins
- **Reviewer(s)**: Cursor-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: The harness spec conflates fill-missing stdout merge with later-wins without a safe-env-loaded branch. An implementer might apply `[[ -n ${!_key:-} ]]` fill-missing on every stdout-only path so an early fake `LOOP_STATUS=` wins over the driver terminal KV when no result env exists, regressing the later-wins case the plan is meant to fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-protocol-fidelity: Split harness instructions: when [[ -f … && ! -L … ]] load succeeds use file-first plus stdout fill-missing only; when no safe env was loaded assign allowlisted stdout KVs in stream order (later wins). Track _safe_env_loaded explicitly in apply_step3_handoff

### FINDING_6: rc!=0 stdout override must not trump safe file-first env
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: The plan says a safely read result env stays authoritative, but also keeps the existing rc!=0 behavior where stdout overwrites a safe file value, creating conflicting precedence rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-protocol-fidelity: Qualify the rc!=0 LOOP_STATUS/TALLY override so it runs only when no safe result env was loaded; move the retained rc case to missing/symlink env and keep a safe-env case proving file wins.

### FINDING_7: exit 2 must short-circuit before LOOP_STATUS normalization
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: SKILL spec says warn on exit 2 then normalize invalid `LOOP_STATUS` to panel-failed, while the harness short-circuits rc=2 before normalization. A config error could be treated as panel-failed instead of aborting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-protocol-fidelity: State that _plan_review_rc==2 prints the configuration warning and exits/returns before LOOP_STATUS normalization; keep normalization only for non-2 handoffs and mirror that order in the harness.

---

**Merge notes (for voters, not part of machine output):** FINDING_5–7 share the Step 3 KV handoff theme but differ in scenario (stdout-only vs safe file vs rc=2), fix, and test surface — kept separate per aggregator rules. FINDING_3 and FINDING_4 both touch `--preview-only` but one is argv testing and one is control-flow exit — kept separate. No `[OUT_OF_SCOPE]` inputs; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` (non-empty merge).
