### FINDING_1: A1 scanner omits live implement timing emitters
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-timing-env, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-timing-env
- **Severity**: important
- **Concern**: The A1 timing-pin scanner is described as a general guard over implement production timing calls, but its enumerated file set omits live implement timing emitters such as `skills/implement/scripts/step2-implement.sh`, `scripts/run-step5-review.sh`, and `scripts/run-relevant-checks-captured.sh`. Dropping or adding an unpinned `LARCH_TIMING_SKILL=implement` in those paths could still pass CI, giving false confidence that ambient timing pollution is guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/scripts/step2-implement.sh to the A1 scanned set (and keep the existing per-mark pins additive)
  - From Codex-Arch: Either narrow A1's stated contract to the listed surfaces, or add the omitted implement timing emitters to the scanner with explicit exclusions for shared lanes.
  - From Cursor-Edge: Add `skills/implement/scripts/step2-implement.sh` and `scripts/run-step5-review.sh` to the A1 scanned set (or an equivalent single glob over implement production emitters)
  - From Codex-Edge: Add the omitted implement timing emitters to the scanner; apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to the CI launchers, or explicitly narrow the invariant so it no longer claims every implement timing call is covered
  - From Cursor-Innovation: Add those three paths to the A1 file list (or bound discovery over skills/implement/scripts and implement-owned scripts/*.sh excluding test-*)
  - From Codex-Innovation: Extend the A1 scanned set to include these already-pinned implement timing emitters, or narrow the invariant text and keep separate literal pins for them.
  - From Cursor-Pragmatic, Cursor-dyn-timing-env: Add those three paths to the A1 scanned set (same awk/index() same-line rule as the other production scripts)
  - From Codex-Pragmatic: Keep the SIMPLE scope honest: either narrow A1 to focused assertions for the two A2 launcher record-vendor-task lines, or make the scanned file list complete for the implement timing surface and only add pins where the current contract requires them.
  - From Cursor-Requirements: Add skills/implement/scripts/step2-implement.sh to the A1 scanned set alongside the other implement timing emitters
  - From Codex-Requirements: Add those three files to the A1 scanner's explicit file set, or derive the scanner input from a grep of implement production timing callers while keeping the intentional scripts/launch-review.sh exclusion.
  - From Codex-dyn-timing-env: Add these three files to the explicit scanner set, or narrow the invariant text so it no longer claims every production mark is covered.


### FINDING_5: Dynamic Codex run-log contract doc is omitted from sync
- **Reviewer(s)**: Cursor-dyn-run-log-posture, Codex-dyn-run-log-posture
- **Severity**: important
- **Concern**: D2/D4 change the dynamic-Codex retention rationale, but `scripts/larch-log.md` restates that rationale and is not explicitly listed for update. The implementation could update code comments and `SECURITY.md` while leaving the primary write-round contract stale or inconsistent about known dynamic output shapes versus broad fallback output allows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-run-log-posture: Add `### UPDATED: scripts/larch-log.md` (comment/prose only): align lines 33-39 with the D2 wording — known `dyn-*-codex-output*` shapes are explicitly pinned; other shapes may fall through to the broad `*-output*` allow; frame retained families under the same pattern-based redaction posture cross-referenced in SECURITY.md
  - From Codex-dyn-run-log-posture: Add scripts/larch-log.md as an explicit UPDATED file and revise lines 30-38 to match the new known-shapes plus broad-fallback rationale


### FINDING_6: Python quiet logging docs overstate bash parity
- **Reviewer(s)**: Cursor-dyn-run-log-posture, Codex-dyn-run-log-posture
- **Severity**: important
- **Concern**: `python/README.md` says `quiet_init()` mirrors `scripts/lib-quiet.sh`, but D3 intentionally preserves Python append behavior for quiet logs while bash truncates per initialization. Without a clarification, operators and reviewers may infer incorrect bash/Python parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-run-log-posture: Add a one-line `python/README.md` clarification beside the `logging_util.py` bullet: routing mirrors lib-quiet, but log open uses append-for-forensics (per D3 comment), not bash truncate-per-run
  - From Codex-dyn-run-log-posture: Add a minimal python/README.md wording update noting that Python mirrors quiet stream routing but intentionally appends quiet logs for crash/retry forensics### OOS_1:
- **Description**: Fixed-path A1 scanner will drift when new implement timing call sites land outside the list. Scenario: The next timing-ledger.sh or timing-report.sh added under implement without updating the scanner array silently evades the general pin guard
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh:13-22
- **Phase**: design


