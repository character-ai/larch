### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:60-70,180-183
- **Concern**: A1/A2 omit scripts/launch-claude-ci.sh while covering codex-ci and cursor-ci. Scenario: Third /implement CI-fix launcher keeps unpinned record-vendor-task at scripts/launch-claude-ci.sh:192; ambient LARCH_TIMING_SKILL=design can mis-tag Claude CI vendor rows and the A1 scanner never enforces a pin
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 scanned set; apply the same A2 inline prefix on its record-vendor-task line; extend the testing strategy to shellcheck/test-launch-claude-ci.sh parity with the other CI launchers

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192
- **Concern**: A2/A1 omit the Claude CI-fix launcher even though it is an /implement CI-fix timing emitter. Scenario: With ambient LARCH_TIMING_SKILL=design, Claude CI-fix vendor rows can still be tagged as design, and the proposed scanner will not catch it
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A2 pin set and A1 scanner file list; pin its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement like the Codex/Cursor CI launchers

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192; scripts/ship-pr.sh:1774
- **Concern**: Plan pins Codex/Cursor CI timing but omits the Claude CI launcher. Scenario: launch-claude-ci.sh is an /implement CI waterfall tier; with inherited LARCH_TIMING_SKILL=design, its record-vendor-task line can still write a design-tagged vendor row, and the A1 scanner will not fail because the file is absent from the scan set
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to A2 and A1: prefix its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement and include it in the scanner list.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:77-80
- **Concern**: python/test_ci_monitor.py B candidate expects consecutive status-gather bail → Outcome.STALLED. Scenario: poll_ci bail reason "ci-status.sh returned no valid output 3 times consecutively" matches retry.is_transient_net_signature (python/retry.py:53-54; python/test_retry.py:44) so monitor() maps bail to Outcome.TRANSIENT (python/ci_monitor.py:1536-1544), not STALLED
- **Proposed resolution**: Revise the B candidate to assert Outcome.TRANSIENT for three consecutive gather errors, or drop it as redundant with test_poll_ci_three_consecutive_errors_bail plus test_monitor_transient_bail_maps_to_transient

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:61-70
- **Concern**: A2 pin sites for launch-codex-ci.sh and launch-cursor-ci.sh cite emit_timing_record() but those scripts have no such helper; record-vendor-task is a single inline call at EOF (scripts/launch-codex-ci.sh:247-254; scripts/launch-cursor-ci.sh:230-237). Scenario: Implementer grepping emit_timing_record may miss or mis-edit the real timing line; A2 CI pins may not land
- **Proposed resolution**: A2 for codex-ci/cursor-ci should name the inline record-vendor-task line (same prefix shape as implement launchers), not emit_timing_record()

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:19-27,61-70,180-183
- **Concern**: A1 scanner list and A2 pins cover codex/cursor CI launchers but omit scripts/launch-claude-ci.sh, which is an /implement CI-fix emitter with unpinned record-vendor-task (scripts/launch-claude-ci.sh:192-199; wired from scripts/ship-pr.sh and python/ci_monitor.py). Scenario: Ambient LARCH_TIMING_SKILL=design can still mis-tag Claude CI-fix vendor rows as design; A1 "no known production timing surface silently missed" contract is incomplete for the third CI-fix tier
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 scanned set and apply the same one-line DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement record-vendor-task pin in A2 (mirror codex/cursor CI, still exclude launch-review.sh)

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192
- **Concern**: The plan pins Codex/Cursor CI record-vendor-task calls but leaves the Claude CI-fix launcher unpinned and outside the A1 scanner.. Scenario: A polluted ambient LARCH_TIMING_SKILL=design can still tag Claude CI-fix vendor rows as design; the new scanner would also miss this known /implement timing surface.
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 scanned set and pin its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement, in the same A1/A2 commit.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-ci.sh:192-199; scripts/ship-pr.sh:1771-1775
- **Concern**: Plan pins Codex/Cursor CI vendor timing rows but omits the implement-only Claude CI launcher, which is part of the ship-pr CI-fix tier waterfall and also records vendor timing.. Scenario: A polluted ambient LARCH_TIMING_SKILL=design can still tag Claude CI-fix vendor rows as design, and the proposed A1 scanner would not catch it because launch-claude-ci.sh is absent from the scanned set.
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 timing scanner set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to its record-vendor-task call.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-timing-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192-199
- **Concern**: A1/A2 omit the third /implement CI-fix launcher that emits record-vendor-task. Scenario: ship-pr.sh rotates launch-cursor-ci.sh launch-codex-ci.sh and launch-claude-ci.sh for CI-fix subwork; only the Claude launcher stays unpinned and outside the A1 scanned set so polluted LARCH_TIMING_SKILL=design can tag claude-ci-fix vendor rows as design and the new scanner never fails
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 scanned set and mirror the A2 one-line DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix on its record-vendor-task call; keep launch-review.sh and launch-claude-subprocess.sh excluded

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-timing-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192-199 scripts/ship-pr.sh:1760-1786 scripts/ship-pr.sh:2508-2524
- **Concern**: A1/A2 omit the Claude CI-fix production launcher from the implement timing pin set. Scenario: ship-pr.sh runs launch-claude-ci.sh as the Claude tier for /implement CI recovery, but its record-vendor-task line is not in the planned scanner or A2 pin list; the new invariant would still miss this production implement timing call
- **Proposed resolution**: Add scripts/launch-claude-ci.sh to the A1 scanned set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to its record-vendor-task call, or explicitly document a deliberate exclusion if Claude vendor rows remain non-emitting by design

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-monitor-outcomes
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:78-79
- **Concern**: Consecutive status-gather bail is specified as Outcome.STALLED but monitor() classifies that bail_reason as transient. Scenario: poll_ci emits bail_reason "ci-status.sh returned no valid output 3 times consecutively" (python/ci_monitor.py:414-416); monitor() routes bail through retry.is_transient_net_signature() (python/ci_monitor.py:1537-1544); python/retry.py:53-54 and python/test_retry.py:44 treat the substring "no valid output 3 times" as transient. A test asserting Outcome.STALLED fails; an implementer might wrongly change monitor() instead of the assertion
- **Proposed resolution**: In plan section B, change the consecutive-error candidate to assert Outcome.TRANSIENT with detail containing "3 times consecutively". Reuse the RecordingRunner stub from python/test_ci_monitor.py:330-351 (gh pr view rc=1). Optionally note this is intentional bash parity (scripts/lib-net.sh), not a stall path

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:192-199
- **Concern**: A1 scanner and A2 pins omit the third implement CI-fix launcher. Scenario: `launch-claude-ci.sh` records vendor timing without `LARCH_TIMING_SKILL=implement` (same pollution class as unpinned Codex/Cursor CI launchers); after `/design`, Claude CI-fix rows can be tagged `design`, and the new A1 guard will never scan this file
- **Proposed resolution**: Add `scripts/launch-claude-ci.sh` to the A1 production-script set; pin `emit_timing_record`/`record-vendor-task` with `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` mirroring `launch-codex-ci.sh`/`launch-cursor-ci.sh`; keep `launch-review.sh` excluded; extend the A2 testing note to cover `test-launch-claude-ci.sh` if shellcheck/lint is run on that launcher

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:246; scripts/larch-log.sh:85-99
- **Concern**: Planned SECURITY.md wording uses broad dyn-*-codex-output* terminology that includes retry shapes which larch-log.sh explicitly denies. Scenario: A literal cross-reference copied from the plan would tell readers that retry transcripts are published under the redaction posture, contradicting round_artifact_included retry exclusion
- **Proposed resolution**: Narrow the SECURITY.md sentence to the exact retained families dyn-*-codex-output.txt and dyn-*-codex-output-phase*.txt plus sidecars, or explicitly say retry outputs remain excluded

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-log-publication
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:283-291
- **Concern**: D4 spec may understate pattern-scrubber residual risk for retained dynamic-Codex artifacts. Scenario: As written, D4 only requires a short cross-reference that dyn-*-codex-output* families share the same pattern-based redact-secrets/scrub-log-secrets posture. SECURITY.md today documents structural trimming only for .meta CMD_JSON and .json .result (283-285); dyn-*-codex-output*.txt and .cap-hit sidecars are copied without structural trim (scripts/larch-log.sh:132-136) and rely solely on pattern redactors whose limits are spelled out at 291 (no PII/internal-URL scrub). A minimal D4 sentence can read like full coverage and understate by-design leakage.
- **Proposed resolution**: Extend the D4 bullet to require naming untrimmed classes (raw .txt and .cap-hit), cite write-round vs commit stages (redact at stage_round_artifact; scrub-log-secrets at commit), and explicitly inherit 291 coverage gaps; anchor the edit at SECURITY.md:283-285 rather than a nonexistent run-log redaction heading.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-log-publication
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:218
- **Concern**: D4 adds a residual-risk cross-reference but leaves existing prose saying consumer repos need no third-party scanner for run-log flush to be safe. Scenario: After the plan lands, SECURITY.md would both frame dynamic Codex logs as pattern-redacted residual risk and still imply the scrub gate makes run-log flushes broadly safe; that understates uncovered-token, PII, private-host, and domain-specific residual risk
- **Proposed resolution**: Soften the existing safe sentence in the same D4 SECURITY.md edit: say no third-party scanner is required for covered secret-shaped families, but run logs remain sensitive and non-matching secrets or PII still require operator discipline.
