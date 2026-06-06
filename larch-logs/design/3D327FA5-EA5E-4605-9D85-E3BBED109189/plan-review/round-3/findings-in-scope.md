### FINDING_1: A1/A2 omit Claude CI-fix timing launcher
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Cursor-dyn-timing-surface, Codex-dyn-timing-surface, Cursor-dyn-contract-sync
- **Severity**: important
- **Concern**: The plan covers Codex/Cursor CI launchers but omits `scripts/launch-claude-ci.sh`, a production `/implement` CI-fix launcher that emits `record-vendor-task`. With inherited `LARCH_TIMING_SKILL=design`, Claude CI-fix vendor rows can still be mis-tagged as design, and the proposed A1 scanner would not catch the unpinned timing surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add scripts/launch-claude-ci.sh to the A1 scanned set; apply the same A2 inline prefix on its record-vendor-task line; extend the testing strategy to shellcheck/test-launch-claude-ci.sh parity with the other CI launchers
  - From Codex-Arch: Add scripts/launch-claude-ci.sh to the A2 pin set and A1 scanner file list; pin its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement like the Codex/Cursor CI launchers
  - From Codex-Edge: Add scripts/launch-claude-ci.sh to A2 and A1: prefix its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement and include it in the scanner list.
  - From Cursor-Innovation: Add scripts/launch-claude-ci.sh to the A1 scanned set and apply the same one-line DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement record-vendor-task pin in A2 (mirror codex/cursor CI, still exclude launch-review.sh)
  - From Codex-Innovation: Add scripts/launch-claude-ci.sh to the A1 scanned set and pin its record-vendor-task line with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement, in the same A1/A2 commit.
  - From Codex-Requirements: Add scripts/launch-claude-ci.sh to the A1 timing scanner set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to its record-vendor-task call.
  - From Cursor-dyn-timing-surface: Add scripts/launch-claude-ci.sh to the A1 scanned set and mirror the A2 one-line DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix on its record-vendor-task call; keep launch-review.sh and launch-claude-subprocess.sh excluded
  - From Codex-dyn-timing-surface: Add scripts/launch-claude-ci.sh to the A1 scanned set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to its record-vendor-task call, or explicitly document a deliberate exclusion if Claude vendor rows remain non-emitting by design
  - From Cursor-dyn-contract-sync: Add `scripts/launch-claude-ci.sh` to the A1 production-script set; pin `emit_timing_record`/`record-vendor-task` with `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` mirroring `launch-codex-ci.sh`/`launch-cursor-ci.sh`; keep `launch-review.sh` excluded; extend the A2 testing note to cover `test-launch-claude-ci.sh` if shellcheck/lint is run on that launcher

### FINDING_2: Consecutive CI status-gather bail should expect TRANSIENT, not STALLED
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-monitor-outcomes
- **Severity**: important
- **Concern**: The plan’s B candidate expects consecutive `ci-status.sh` no-output bailouts to map to `Outcome.STALLED`, but `monitor()` routes that bail reason through transient-network signature matching, which classifies “no valid output 3 times” as `Outcome.TRANSIENT`. A test asserting `STALLED` would fail or push implementers toward changing intended monitor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Revise the B candidate to assert Outcome.TRANSIENT for three consecutive gather errors, or drop it as redundant with test_poll_ci_three_consecutive_errors_bail plus test_monitor_transient_bail_maps_to_transient
  - From Cursor-dyn-monitor-outcomes: In plan section B, change the consecutive-error candidate to assert Outcome.TRANSIENT with detail containing "3 times consecutively". Reuse the RecordingRunner stub from python/test_ci_monitor.py:330-351 (gh pr view rc=1). Optionally note this is intentional bash parity (scripts/lib-net.sh), not a stall path

### FINDING_3: A2 names nonexistent emit_timing_record helper for Codex/Cursor CI launchers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The A2 pin sites for `launch-codex-ci.sh` and `launch-cursor-ci.sh` refer to `emit_timing_record()`, but those scripts use a single inline `record-vendor-task` call near EOF. An implementer following the helper name may miss or mis-edit the actual timing line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: A2 for codex-ci/cursor-ci should name the inline record-vendor-task line (same prefix shape as implement launchers), not emit_timing_record()

### FINDING_4: SECURITY.md wording may imply retry transcripts are retained/redacted
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Concern**: Planned `SECURITY.md` wording uses broad `dyn-*-codex-output*` terminology that could include retry transcript shapes, even though `larch-log.sh` explicitly excludes retry artifacts. Copying that wording would contradict the artifact inclusion contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-sync: Narrow the SECURITY.md sentence to the exact retained families dyn-*-codex-output.txt and dyn-*-codex-output-phase*.txt plus sidecars, or explicitly say retry outputs remain excluded

### FINDING_5: D4 may understate residual risk for retained dynamic Codex artifacts
- **Reviewer(s)**: Cursor-dyn-log-publication
- **Severity**: important
- **Concern**: The D4 security-doc update may read like comprehensive protection even though retained dynamic Codex `.txt` and `.cap-hit` artifacts are copied without structural trimming and rely on pattern redactors with known coverage gaps such as PII and internal URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-log-publication: Extend the D4 bullet to require naming untrimmed classes (raw .txt and .cap-hit), cite write-round vs commit stages (redact at stage_round_artifact; scrub-log-secrets at commit), and explicitly inherit 291 coverage gaps; anchor the edit at SECURITY.md:283-285 rather than a nonexistent run-log redaction heading.

### FINDING_6: D4 should soften existing “safe without scanner” run-log wording
- **Reviewer(s)**: Codex-dyn-log-publication
- **Severity**: important
- **Concern**: The planned residual-risk cross-reference would coexist with existing prose suggesting consumer repos need no third-party scanner for run-log flushes to be safe. That combination could understate risks from uncovered tokens, PII, private hosts, and domain-specific sensitive data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-log-publication: Soften the existing safe sentence in the same D4 SECURITY.md edit: say no third-party scanner is required for covered secret-shaped families, but run logs remain sensitive and non-matching secrets or PII still require operator discipline.
