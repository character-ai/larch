### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:170-186
- **Concern**: Thin-fence display echo does not exclude WARN= lines from the non-KV echo pass. Scenario: The plan adds echoing captured lines that are not in the 12-key allowlist and separately replays WARN= via the parse loop. WARN= matches KEY=value shape but is not allowlisted, so both paths emit the same line and operators see duplicate WARN breadcrumbs whenever a safe .step3-review-result.env was loaded (common rc=0 path)
- **Proposed resolution**: In the SKILL.md thin fence, run one pre-parse loop over _plan_review_out that printf display lines only when the key is not in the 12-key set and is not WARN; mirror the same exclusion in test-step3-orchestrator-fence.sh apply_step3_handoff

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:4-17,76-116,297-325
- **Concern**: Phase 2 bundles driver preview mode, sentinel migration, and a new test seam while deferring turn reduction. Scenario: The plan admits the original per-Step-3-entry turn-reduction goal is deferred, yet still replaces the live uncaptured emit-design-plan-preview.sh fence with run-step3-review.sh --preview-only plus a second captured --no-preview call, adding mode flags, allowlist-gated sentinel logic, RUN_STEP3_EMIT_PREVIEW_SH, and eight new driver harness cases without reducing fence count or operator-visible turns
- **Proposed resolution**: For a SIMPLE minimum-change Phase 2, collapse only the captured review handoff to the thin-fence shape and keep the existing live emit-design-plan-preview.sh --variant step3 fence and renderer-owned sentinel until a later phase when preview ownership can be paired with an actual turn win

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-run-step3-review.sh:85-121
- **Concern**: New mutually exclusive --preview-only/--no-preview argv contract lacks a planned reject-path assertion. Scenario: The plan requires the flags to be mutually exclusive, and the repo argv-coverage rule requires same-PR tests for new reject paths; an implementation could silently choose one mode when both flags are passed
- **Proposed resolution**: Add one argv test in test-run-step3-review.sh asserting --preview-only --no-preview exits 2 with the pinned conflict message, alongside the existing missing/unknown option tests

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-migration-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:20-47
- **Concern**: Plan adds `--preview-only` but does not require the preview branch to terminate before the existing `--round-cap` requirement and review driver body. Scenario: `run-step3-review.sh --preview-only --design-tmpdir "$TMP"` (as in the planned harness) still hits `[[ -n "$ROUND_CAP" ]] || fail '--round-cap is required'` at lines 46-47 and exits 2, so the live preview fence prints nothing and Step 3 never reaches review
- **Proposed resolution**: After handling preview capture/emit/sentinel touch, end the `--preview-only` branch with `exit 0` before `--round-cap` validation, tmpdir `cd`, cap guard, `plan-review-loop.sh`, and `.step3-review-result.env` writes

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-kv-protocol-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:193-199
- **Concern**: Harness spec conflates fill-missing stdout merge with later-wins without a safe-env-loaded branch. Scenario: Implementer may apply [[ -n ${!_key:-} ]] fill-missing on every stdout-only path so an early fake LOOP_STATUS= wins over the driver terminal KV when no result env exists (regression the new later-wins case is meant to fix)
- **Proposed resolution**: Split harness instructions: when [[ -f … && ! -L … ]] load succeeds use file-first plus stdout fill-missing only; when no safe env was loaded assign allowlisted stdout KVs in stream order (later wins). Track _safe_env_loaded explicitly in apply_step3_handoff

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:50-53,170-186,191-206; skills/design/scripts/test-step3-orchestrator-fence.sh:176-187
- **Concern**: rc!=0 stdout override conflicts with file-first precedence. Scenario: The plan says a safely read result env stays authoritative, but it also keeps the existing rc!=0 case where stdout overwrites a safe file value.
- **Proposed resolution**: Qualify the rc!=0 LOOP_STATUS/TALLY override so it runs only when no safe result env was loaded; move the retained rc case to missing/symlink env and keep a safe-env case proving file wins.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:181-183,193-199,414-416; skills/design/SKILL.md:1097-1103; skills/design/scripts/test-step3-orchestrator-fence.sh:85-90,200-210
- **Concern**: exit-2 handling is not aligned with normalization. Scenario: The SKILL spec says warn on exit 2 then normalize invalid LOOP_STATUS to panel-failed, while the harness short-circuits rc=2 before normalization. A config error could fall through as panel-failed instead of aborting.
- **Proposed resolution**: State that _plan_review_rc==2 prints the configuration warning and exits/returns before LOOP_STATUS normalization; keep normalization only for non-2 handoffs and mirror that order in the harness.
