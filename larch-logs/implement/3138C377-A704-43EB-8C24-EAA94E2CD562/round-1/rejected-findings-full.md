### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: correctness: scripts/launch-codex-implement.sh:328-344
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Inline # comment between \ and codex exec splits the continued run-external-agent invocation from codex exec. Codex runs outside run-external-agent timeout/PID monitoring; empty-wrapper side effects; auth-retry/exit semantics differ from review/review-and-fix launchers. Move comment outside the continued argv (line above run-external-agent or end-of-line on --add-dir); verify wrapper receives full codex argv in test-codex-implementer.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:367-511
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No integration assertion that review-and-fix.sh chmods pre-coder snapshot files after a real round. Removing harden_pre_coder_snapshot_perms or clear_stale in review-and-fix.sh still passes dispatch CI while unit helper tests pass. After run_orchestrator_case / carryover-orchestrator success assert mode_of 444 on relocated pre-coder-head (and tracked artifacts when present).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/review-and-fix/scripts/review-implement-step5-loop.sh:397-411
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] MAV uses inline chmod 0444 instead of harden_pre_coder_snapshot_perms. Future hardening changes to patches or cached.patch apply to main path only; MAV telemetry head hardening diverges silently. Reuse harden_pre_coder_snapshot_perms after MAV head write or add a focused MAV test that fails on drift.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: risk-integration: scripts/launch-codex-implement.sh:333-344
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Full-line shell comment between `\`-continued `--` and `codex exec` likely terminates the `run-external-agent.sh` argv at `--`, running Codex outside the monitored wrapper. Step 2 can lose timeout/kill and wrapper completion semantics while stub harness tests still pass via direct `codex` on PATH. Move the comment above the invocation; keep `-- \` immediately followed by `codex exec` on the continued argv.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: security: skills/review-and-fix/scripts/review-and-fix.sh:1560-1562
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] `post-coder-head.txt` remains under Codex-granted `round_dir`; `chmod 0444` does not stop a granted writer from tampering before telemetry reads. A hostile or over-permissive Step 5 coder can skew `structural_loc`/bulk-skip gates without affecting carryover commit guards. Relocate post-coder head to the relocated snapshot dir or document as an explicit non-integrity telemetry surface.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: security: skills/review-and-fix/scripts/review-and-fix.sh:352-363
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Relocated snapshot path assumes `$TMPDIR` is outside `$PWD`; no runtime assertion. `TMPDIR=$PWD/.tmp` places snapshots back inside `--add-dir "$PWD"`, silently negating relocation. Assert relocated `snap_dir` is outside `pwd_abs` when the in-repo branch fires; fail closed or warn loudly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1559-1562
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Post-coder-head clear/write/chmod duplicated in review-implement-step5-loop.sh Future hardening or guard changes must be edited in two places or MAV and orchestrator paths diverge Extract write_hardened_post_coder_head helper in review-and-fix.sh and call from both writers
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: architecture: skills/review-and-fix/scripts/review-and-fix.sh:352-368
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] pre_coder_snapshot_dir branches on pwd -P not git toplevel Step 5 invoked from a subdirectory with in-repo IMPLEMENT_TMPDIR leaves snapshots under .pre-coder-snapshots inside the repo grant Compare parent_abs to git rev-parse --show-toplevel or document/enforce cwd at grant root
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:358-363
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No runtime check that TMPDIR is outside PWD TMPDIR under repo root places relocated snapshots inside --add-dir PWD Fail closed when relocation target t is under pwd_abs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1349-1354
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Coder dispatch continues when pre-coder-head write fails rev-parse failure drops snapshots but still runs Codex carryover logic blind Fail round or skip coder when pre-coder-head is missing after write attempt
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/review-and-fix/scripts/review-and-fix.sh:371-375
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Relocated snapshot dirs not session-reaped crash leaves 0444 files under larch-pre-coder-snapshots until manual cleanup Document ops policy or add session-scoped cleanup hook
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: code-quality: scripts/launch-codex-implement.sh:333-335
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment embedded in line-continued argv future edit may split run-external-agent from codex exec on another shell Move comment above the run-external-agent invocation block
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/launch-codex-implement.sh:333-335
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comment placed between line continuation and codex exec instead of above SESSION_TMPDIR grant Harder to maintain; diverges from plan placement and repo argv-comment conventions Move comment above --add-dir "$SESSION_TMPDIR" or above the run-external-agent invocation
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

