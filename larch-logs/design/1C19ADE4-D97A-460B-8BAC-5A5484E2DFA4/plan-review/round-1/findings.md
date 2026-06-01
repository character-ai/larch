### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:300-1498
- **Concern**: Makefile-only harness not listed in agent-lint exclude. Scenario: `scripts/test-step-telemetry-mark.sh` is only reachable from the new Makefile target; agent-lint G004 does not follow Makefile edges, so `make lint` / `bash scripts/relevant-checks.sh` can fail with a false dead-script on the new harness
- **Proposed resolution**: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml` `exclude =` with the same Makefile-only comment pattern as `scripts/test-lib-quiet.sh` (runtime `scripts/step-telemetry-mark.sh` should stay off exclude — it is referenced from `skills/implement/SKILL.md`)

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/step-telemetry-mark.sh (proposed)
- **Concern**: Plan promises exit 0 when --implement-tmpdir is omitted but does not require pre-parse IMPLEMENT_TMPDIR="" / LABEL="" before set -u references; harness omits that case. Scenario: With set -uo pipefail, an omitted --implement-tmpdir leaves IMPLEMENT_TMPDIR unset; the first "$IMPLEMENT_TMPDIR/session-env.sh" expansion aborts (non-zero), contradicting plan Edge cases and the never-fatal contract; CI would not catch it because test-step-telemetry-mark.sh only covers bad tmpdir paths
- **Proposed resolution**: Initialize IMPLEMENT_TMPDIR="" and LABEL="" before the arg loop; use "${IMPLEMENT_TMPDIR:-}" only where needed; add a harness case that invokes the helper with no --implement-tmpdir and asserts exit 0

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:300,1058-1063,1410
- **Concern**: Plan adds a Makefile-only test harness but omits agent-lint exclusions for the new harness and sibling doc. Scenario: `bash scripts/relevant-checks.sh` runs agent-lint; its dead-script/orphan rules do not follow Makefile-only harness edges, so `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` can fail lint despite the Makefile target
- **Proposed resolution**: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml`'s exclude list with the same Makefile-only comment pattern as `scripts/test-implement-timing-rehydration.sh`/`.md`

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1058-1063
- **Concern**: Makefile-only harness lacks dead-script exclusion entry. Scenario: `scripts/test-step-telemetry-mark.sh` is only invoked from the new Makefile target; without an `agent-lint.toml` dead-script exclusion (same pattern as `scripts/test-implement-timing-rehydration.sh`), `make lint` / agent-lint G004 can fail on a newly dead script
- **Proposed resolution**: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to the `agent-lint.toml` dead-script exclude list with a Makefile-only comment, mirroring `test-implement-timing-rehydration`

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:894-900; scripts/test-step-telemetry-mark.sh:1
- **Concern**: Converted call sites execute step-telemetry-mark.sh directly and swallow 126, but the new harness plan does not require the helper to be executable. Scenario: A new helper added without +x would pass if tests invoke it via bash, while all converted Step 5/16/17/18 telemetry marks silently disappear at runtime
- **Proposed resolution**: Add a minimal harness assertion like [[ -x "$HELPER" ]] and run the happy path through "$HELPER" rather than bash "$HELPER"; ensure the new file is committed executable

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/step-telemetry-mark.sh:1
- **Concern**: New runtime helper is called directly but the plan does not require executable mode. Scenario: If the new file lands as 0644, each converted SKILL.md call returns 126 and is swallowed by || true, silently losing Step 5/16/17/18-cleanup telemetry
- **Proposed resolution**: Make the helper executable in git and have test-step-telemetry-mark invoke it directly by path, not only via bash

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1058-1063
- **Concern**: New Makefile-only harness is not added to agent-lint dead-script excludes. Scenario: agent-lint does not model Makefile-only test targets, so relevant-checks can fail on scripts/test-step-telemetry-mark.sh and its sibling md despite Makefile wiring
- **Proposed resolution**: Add scripts/test-step-telemetry-mark.sh and scripts/test-step-telemetry-mark.md to the same Makefile-only allowlist near test-implement-timing-rehydration

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:300-330
- **Concern**: Plan adds a Makefile-only harness but does not update agent-lint exclusions. Scenario: `bash scripts/relevant-checks.sh` includes agent-lint; this repo documents that agent-lint does not follow Makefile target chains, so `scripts/test-step-telemetry-mark.sh` and likely its sibling `.md` can be flagged as dead/orphan despite Makefile wiring
- **Proposed resolution**: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml` with the adjacent Makefile-only harness exclusions, or add another agent-lint-recognized structural reference

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-ledger-semantics
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:300-322,1058-1063,1405-1411
- **Concern**: F1 New helper and Makefile-only harness are not added to agent-lint exclusions. Scenario: The plan adds scripts/step-telemetry-mark.sh plus a Makefile-only test, but relevant-checks runs agent-lint; this file already excludes comparable Makefile-only harnesses and SKILL-fence helper paths because dead-script reachability does not follow those edges. The PR can fail lint even when the helper works.
- **Proposed resolution**: Add agent-lint.toml to the UPDATED files and exclude scripts/step-telemetry-mark.sh, scripts/step-telemetry-mark.md, scripts/test-step-telemetry-mark.sh, and scripts/test-step-telemetry-mark.md with the same Makefile-only/runtime-fence rationale.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-ledger-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:890-901,1311-1322,1353-1364,1429-1441
- **Concern**: F2 Direct helper call needs an executable-bit contract. Scenario: The proposed converted fences execute "${CLAUDE_PLUGIN_ROOT}/scripts/step-telemetry-mark.sh" directly. If the new file lands non-executable, the call returns 126 and || true silently drops all converted token and timing marks, changing telemetry semantics.
- **Proposed resolution**: Require scripts/step-telemetry-mark.sh to be committed executable and add a [ -x "$HELPER" ] assertion to scripts/test-step-telemetry-mark.sh, or switch the SKILL.md call sites to bash "$HELPER" consistently.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:729-733
- **Concern**: Plan omits agent-lint dead-script exclusions for new step-telemetry-mark and test-step-telemetry-mark siblings. Scenario: agent-lint G004 does not follow SKILL.md `${CLAUDE_PLUGIN_ROOT}/scripts/...` invocations (see the rebase-checkpoint-probe comment at agent-lint.toml:729-731); without exclusions, `make lint` / `agent-lint --pedantic` can false-flag the new primary and Makefile-only harness as dead scripts
- **Proposed resolution**: Add `scripts/step-telemetry-mark.sh`, `scripts/step-telemetry-mark.md`, `scripts/test-step-telemetry-mark.sh`, and `scripts/test-step-telemetry-mark.md` to the dead-script exclude list with the same Makefile-only / G004 comment pattern as `scripts/rebase-checkpoint-probe.sh` and `scripts/test-implement-timing-rehydration.sh`

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:729-737,830-850,1058-1063
- **Concern**: Plan adds scripts/step-telemetry-mark.sh and scripts/test-step-telemetry-mark.sh but does not update agent-lint.toml for the same reachability pattern used by sibling SKILL-fence helpers and Makefile-only harnesses. Scenario: relevant-checks.sh runs agent-lint unconditionally, and the new helper is only invoked from SKILL.md fences while the harness is only Makefile-wired, so agent-lint can fail the PR as dead/orphaned despite the Makefile shard wiring
- **Proposed resolution**: Add explicit agent-lint.toml exclusions for scripts/step-telemetry-mark.sh, scripts/step-telemetry-mark.md, scripts/test-step-telemetry-mark.sh, and scripts/test-step-telemetry-mark.md, or add an agent-lint-recognized structural reference

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:890-902,1311-1323,1353-1365,1429-1442
- **Concern**: The planned harness does not explicitly pin the new helper executable bit even though the proposed SKILL.md call sites execute it directly and mask failures with || true. Scenario: If scripts/step-telemetry-mark.sh lands as mode 0644 and the harness invokes it via bash, tests can pass while every converted runtime site exits 126 under || true and silently drops both ledger marks
- **Proposed resolution**: In scripts/test-step-telemetry-mark.sh, assert [ -x "$SCRIPT" ] and invoke "$SCRIPT" directly in the happy-path test before checking both ledger rows
