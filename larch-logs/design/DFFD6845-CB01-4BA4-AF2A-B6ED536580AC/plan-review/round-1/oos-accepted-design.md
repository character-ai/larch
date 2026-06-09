### OOS_1:
- **Description**: Proposed drafter launcher adds timing attribution but plan omits allow-list registration. Scenario: Plan mentions `TOKEN_RAW=claude_draft` / `*draft*` attribution and accepts `--timing-task-kind`, but does not add a kind (e.g. `claude-design-draft`) to `lib-timing-kinds.sh` or pass `--timing-task-kind` from the SKILL launch block. Timing rows will warn or mis-attribute without breaking drafting.
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lib-timing-kinds.sh:1-80
- **Phase**: design

### OOS_2:
- **Description**: Step 2b success display reinvents summary threshold logic instead of reusing `emit-design-plan-preview.sh`. Scenario: The new block hand-rolls `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` + `plan-summary.md` presentation while Step 3/Gate C already centralize summary/full rules in `emit-design-plan-preview.sh`. Two presentation paths can diverge on threshold, outline, and fallback behavior.
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:77-80
- **Phase**: design

### OOS_3:
- **Description**: scripts/test-launch-claude-drafter.sh is in Testing strategy but absent from Files to modify/create. Scenario: Implementer may ship launcher without harness or Makefile target despite plan testing prose
- **Reviewer**: Cursor-dyn-scope-omissions
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:175 vs plan.txt:12-144
- **Phase**: design

### OOS_1:
- **Description**: Plan extraction relies on prompt-described delimiters without a normative parser contract or fixture tests. Scenario: Malformed .result text passes rc=0 but fails PLAN_WRITTEN/status extraction and forces inline fallback even when the model produced usable prose
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-claude-drafter.sh:61-61
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] New launcher largely duplicates launch-claude-subprocess.sh JSON promotion, token/timing, and sidecar logic. Scenario: Two copies drift on security fixes (e.g. issue #3637 JSON rules) and increase maintenance surface
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-drafter.sh:16-57
- **Phase**: design

### OOS_3:
- **Description**: `TOKEN_RAW=claude_draft` attribution is pointed at `timing-ledger.sh` but that mapping lives in launcher subprocess code today (`launch-claude-subprocess.sh` ~119-122). Scenario: Following the plan literally may add a no-op change in `timing-ledger.sh` while `record-vendor` rows stay labeled `claude_review`, skewing design cost reports
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-drafter.sh:59
- **Phase**: design

### OOS_4:
- **Description**: New drafter harness is listed but not wired into `Makefile` / `agent-lint.toml` like `test-launch-claude-subprocess`. Scenario: The launcher regression may not run in CI shards unless manually invoked
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-claude-drafter.sh:225-230
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] New launcher largely duplicates launch-claude-subprocess.sh. Scenario: New script reimplements JSON .result promotion, token/timing sidecars, meta/done/diag handling already centralized in launch-claude-subprocess.sh. Maintenance cost grows without feature necessity.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-drafter.sh:1-76
- **Phase**: design

### OOS_2:
- **Description**: Drafter --repo-root uses $PWD instead of git toplevel. Scenario: /design uses --skip-repo-check; if a Bash fence runs outside repo root, --add-dir "$PWD" scopes read access to a subdirectory and dirty-tree probes may disagree with consumer-repo expectations.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:132
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] Dual large-plan summary pipelines plan-summary.md vs emit-design-plan-preview. Scenario: Step 2b success prints drafter prose summary while Step 3 and Gate C use mechanical outline logic from emit-design-plan-preview.sh; operators can see divergent summaries for the same plan
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/emit-design-plan-preview.sh:61-80
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] New launcher largely duplicates launch-claude-subprocess.sh JSON promotion token timing and sidecar patterns. Scenario: Future subprocess fixes must be ported twice increasing drift risk
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-drafter.sh:1-91
- **Phase**: design

### OOS_3:
- **Description**: Custom MODE=baseline-delta sidecar grammar diverges from check-mid-run-dirty-tree.sh. Scenario: The drafter invents MODE=baseline-delta and bespoke REASON tokens instead of reusing lib-dirty-tree-sidecar.sh / check-mid-run-dirty-tree.sh --mode baseline, increasing the chance orchestrator and harness parse drift from sketch/dialectic dirty-tree handling
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-drafter.sh:46-53
- **Phase**: design

### OOS_4:
- **Description**: No explicit Bash-tool timeout budget for the 1800s foreground drafter launch. Scenario: The launcher timeout is 1800s but the plan does not state the orchestrator Bash invocation must use a matching block_until_ms; a shorter harness default could kill the drafter early and spuriously trigger inline fallback
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:181-191
- **Phase**: design

### OOS_5:
- **Description**: [SCOPE-REDUCTION] New launcher reimplements launch-claude-subprocess.sh JSON promotion, timeout, token/timing, and sidecar behavior instead of extending the existing wrapper. Scenario: The issue only needs a strong-model Step 2b subprocess with launcher-owned writes. A parallel launcher duplicates ~200 lines of subprocess contract already centralized in scripts/launch-claude-subprocess.sh and scripts/launch-claude-review.sh, increasing drift risk (TOKEN_RAW arms, JSON fail-closed rules, sidecar semantics) beyond the minimum SIMPLE-tier change.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-drafter.sh:18-91
- **Phase**: design

### OOS_6:
- **Description**: voting-protocol.md "Launching Voters" still documents Agent-tool Claude voter launch after C2/C3 panel-line edits. Scenario: Component 3 updates Voter Panel Composition bullets, but lines such as "Claude voter: Launch via Agent tool" and the plan-review launch ordering prose still describe the retired in-process voter path. Operators reading only that section will misconfigure or debug voters incorrectly even though dispatch-plan-voters.sh and dispatch-code-voters.sh already use launch-claude-review.sh --role voter.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md:112-170
- **Phase**: design

### OOS_7:
- **Description**: `.meta` spec lists only `CMD_JSON`; subprocess contract also writes `OUTER_LAUNCHER`, `TOOL`, and `TIMEOUT`. Scenario: Drafter path likely still works because Step 2b reads status file + `.dirty-tree`, not `.meta`; gap is collector/tooling parity only
- **Reviewer**: Cursor-dyn-launcher-conformance
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:56 / scripts/launch-claude-subprocess.sh:208-213
- **Phase**: design

### OOS_8:
- **Description**: Plan introduces `raw=claude_draft` without updating `token-ledger.md` enum list. Scenario: Ledger accepts arbitrary `raw=` strings today; `/report-tokens` grouping may bucket draft spend under generic `claude_sub` until docs/reporting learn the label
- **Reviewer**: Cursor-dyn-launcher-conformance
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:83 / scripts/token-ledger.md:41
- **Phase**: design

### OOS_1:
- **Description**: C2 relies on dispatch voters passing --role voter without --model but plan verifies only test-launch-claude-review.sh not dispatch call sites. Scenario: A future edit could add --model to a dispatcher and silently bypass LARCH_VOTER_MODEL without a failing test
- **Reviewer**: Cursor-dyn-voter-caller-surface
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:97-105; scripts/dispatch-code-voters.sh:120-127; plan.txt:483-486
- **Phase**: design

