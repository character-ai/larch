### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:63
- **Concern**: NEVER #17 list bullet still mandates Step 18 Read fallback while the plan switches Step 18 to marker-only emission from captured finalize stdout. Scenario: The NEVER list item at line 63 still says Step 18 may emit via Read fallback when EMIT_BODY=true; the plan’s Step 18 subsection forbids Read after teardown. An implementer can leave both contracts in place and the orchestrator may follow the stale Read path after tmpdir deletion
- **Proposed resolution**: In the ### UPDATED: skills/implement/SKILL.md section, explicitly replace NEVER list item 17 (~line 63) to match the new Step 18 marker-extraction contract and remove the Read-fallback carve-out for Step 18

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:860-892
- **Concern**: SKILL update omits explicit removal of stale Step 18 orchestrator prose that contradicts the consolidated wrapper. Scenario: The plan preserves three prose blocks but does not require deleting live instructions: orchestrator-owned skip breadcrumb at 860 (wrapper now prints it), Read-based Step 18 body emission at 892, and step18b cleanup smoke-check claim at 880. An implementer can follow dead/conflicting SKILL text and either duplicate breadcrumbs or Read after teardown when tmpdir is gone
- **Proposed resolution**: Add an explicit deletions checklist under ### UPDATED: skills/implement/SKILL.md: drop 860 skip print, replace 880-892 Step 18b emit contract with marker-only finalize stdout parsing, and align NEVER #17 Step 18 bullets with wrapper-owned .step17-emitted

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:77-78
- **Concern**: No-stall skip breadcrumb moved to gate wrapper stdout without orchestrator relay obligation. Scenario: `skills/implement/SKILL.md:860` today prints `⏩ 18a: stall recovery — no stall detected` as operator-visible orchestrator text. The plan prints it only inside `--phase gate` captured Bash stdout and does not list it in the teardown-tail relay contract. Operators lose the skip breadcrumb inside collapsed tool output.
- **Proposed resolution**: Keep prompt-side skip print in `SKILL.md` when `STALL_RECOVERY_REQUIRED=false`, or add the skip line to the gate stdout relay list alongside `RENAME_*` / `ISSUE_URL`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:93-110
- **Concern**: Finalize marker emission not isolated from `set -e` abort path. Scenario: `--phase finalize` folds marker printing with closing marks and `implement-finalize teardown` under the same `set -euo pipefail` script as retirees. A failed `cat` of `summary-final.md` (mirroring `step-16-17.sh` `print_summary_markers`) can exit before token/timing marks and teardown, leaving `$IMPLEMENT_TMPDIR` and session pointers uncleared (#3425 violation).
- **Proposed resolution**: Wrap marker printing in `set +e` (or `cat ... || true`) and always run closing marks, `_restore_finalize`, and teardown afterward, matching `step-16-17.sh` non-aborting marker behavior.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:63-68
- **Concern**: Memory stall layer resolution left ambiguous vs `_stall_layer_active`. Scenario: Plan applies `_stall_layer_active` to decide `STALL_RECOVERY_REQUIRED` but says memory comes from `step-18a-gate.sh` sources. The retiree only accepts `true|false` in `--stall-tracking-memory` (`step-18a-gate.sh:65-68`); other non-empty values silently stay `false` in the emitted KV while disk/finalize/session use broader activation. A non-canonical in-memory `STALL_TRACKING` value can be dropped and skip recovery.
- **Proposed resolution**: Pin memory resolution as: use the `--stall-tracking-memory` arg when non-empty, else `${STALL_TRACKING:-false}`, with no `true|false`-only case filter; run `_stall_layer_active` on the emitted `STALL_TRACKING_MEMORY` value.

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:7-19,127,140-155
- **Concern**: The plan changes the accepted no-stall contract from one Bash call to two Bash calls. Scenario: The binding issue acceptance requires one `step-18.sh` no-stall Bash call, but the proposed SKILL flow still requires prompt-side orchestration between `--phase gate` and `--phase finalize`
- **Proposed resolution**: Restore the one-call no-stall wrapper contract, or return for explicit rescoping before implementing this plan if Step 18a.5 must remain prompt-side

