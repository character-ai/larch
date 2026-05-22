Producing the merged structured finding list from the supplied reviewer inputs (read-only aggregation; no file or git mutations).

### FINDING_1: AGENTS.md single-/design wording vs PID-keyed symlink rationale
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: The single-/design-per-repo guidance still reads like the old global-symlink story; operators may over-serialize concurrent `/design` across clones or think the rule is symlink-collision-driven rather than workflow hygiene plus per-Claude PID-keyed paths. Acceptance asked reframing the invariant scope to match the new mechanism.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split bullets or add explicit note that per-repo rule is workflow hygiene not symlink collision.
  - From cursor-specialist-correctness-output.txt: Retitle or split operational single-runner rationale from per-Claude symlink safety so acceptance 3/AGENTS wording match the new mechanism.

### FINDING_2: Independence harness is sequential, not concurrent race simulation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Tests prove two-PID isolation in sequence, not interleaved `ln -sfn` timing or subshell races described in acceptance; less confidence against true parallel behavior unless contract or harness is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use parallel subshells or reword harness contract to match what is tested.
  - From cursor-specialist-correctness-output.txt: Add concurrent race reproducer or document explicit deferral of strict race sim.
  - From cursor-specialist-testing-output.txt: Add parallel race harness later or document explicit non-goal in test-write-design-current-env.md

### FINDING_3: Seven-digit `--claude-pid` cap vs large `pid_max`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Validation caps decimal PID length (e.g. pattern allowing at most seven digits); on hosts where `kernel.pid_max` exceeds that range, legitimate PIDs can be rejected and Step 0 / symlink refresh fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Widen allowed digits or document and test host ceiling.
  - From cursor-specialist-correctness-output.txt: Remove or widen the digit cap after checking supported platforms or gate with explicit portability docs.
  - From cursor-specialist-security-output.txt: Raise bound to match supported pid_max or probe pid_max
  - From cursor-specialist-edge-cases-output.txt: Align max PID width with platform reality or read pid_max; update tests and write-design-current-env.md accordingly.

### FINDING_4: PPID / Bash subshell prose overclaims Claude alignment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Docs/plan text imply `$PPID` always tracks the Claude Code parent across arbitrary Bash subshells; in nested `( )` or extra `bash` layers, PPID can be an intermediate shell, so a misplaced prelude may target the wrong PID-keyed file and skip `DESIGN_TMPDIR`. Archived plan copy can mislead maintainers the same way.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Limit the claim to verified top-level Bash-tool invocations or document forbidden nesting patterns.
  - From cursor-specialist-security-output.txt: Fix wording in future log/plan copies: note PPID is reliable on Claude Bash-tool root shells not arbitrary nested subshells
  - From cursor-specialist-edge-cases-output.txt: Document top-level Bash-tool only; warn not to wrap the prelude inside nested subshells or inner bash without explicit re-handoff.

### FINDING_5: Present-but-empty `--claude-pid` treated like omission; tests and plan text drift
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-pid-regex-completeness-output.txt
- **Concern**: Empty parsed `CLAUDE_PID` skips numeric validation and uses the legacy global `current-design-env.sh` path (same clobber class PID keying is meant to remove). Plan/run-log failure modes promised rejection for empty, but the harness does not assert `""`; tests and contract can drift on the empty-argv edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align tests and writer/docs on whether empty means invalid or legacy shim.
  - From cursor-specialist-testing-output.txt: Track flag presence vs value or reject empty when flag passed; only use legacy path when flag omitted
  - From cursor-specialist-testing-output.txt: Add loop entry or subtest for `--claude-pid ""` asserting exit 1 and Invalid --claude-pid before symlink writes
  - From cursor-specialist-plan-fidelity-output.txt: Parse `--claude-pid` presence distinctly; reject empty with Invalid --claude-pid; extend case 7 to cover ""
  - From dyn-pid-regex-completeness-output.txt: After parsing, treat a present-but-empty `--claude-pid` as invalid (same error path as `0` / non-numeric), or document and test that empty is intentionally an alias for omission; if rejecting empty, extend case7 to include `""` in the invalid loop.

### FINDING_6: [OUT_OF_SCOPE] Committed implement run-log directory under `larch-logs/implement/`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Committed implement run-log flush matches repo policy / `docs/run-logs.md`; not treated as a functional defect of PID-keyed design-env work for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: None
  - From cursor-specialist-edge-cases-output.txt: None per run-log policy.

### FINDING_7: `test-design-structure.sh` Check 11 scope — prelude / `--claude-pid` guard can be satisfied without protecting the real Step 0a invocation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ppid-bash-c-wrapping-output.txt
- **Concern**: Guard greps a broad Step 0 slice (or only Step 0 excerpt); the needle can match non-executable prose or a misleading `bash -c` pattern while the actual `"${_wdce_args[@]}"` / writer path regresses. Later-step prelude regressions may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add SKILL-wide grep guard for forbidden current-design-env.sh preludes or require PID form in all bash blocks
  - From cursor-specialist-edge-cases-output.txt: Add a whole-SKILL.md structural grep for the canonical prelude or legacy path allowlist.
  - From dyn-ppid-bash-c-wrapping-output.txt: Assert `--claude-pid "$PPID"` (and ideally the PID-keyed prelude token) only inside the first Step 0 fenced ```bash …``` block (or between `_wdce_args=(` and `"${_wdce_args[@]}"`), and/or add a negative probe that rejects `bash -c` adjacent to the writer invocation in that block.

### FINDING_8: Legacy singleton `current-design-env.sh` when `--claude-pid` is omitted
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Transition shim keeps a global legacy symlink without PID in the path; concurrent writers that omit `--claude-pid` can still race and clobber which session env later steps source; stderr warning may be ignored in automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Make `--claude-pid` mandatory after deprecation or gate legacy shim behind explicit opt-in for tests only
  - From cursor-specialist-edge-cases-output.txt: Keep shim if required but strengthen deprecation messaging or CI-visible severity; track removal milestone.

### FINDING_9: [OUT_OF_SCOPE] `SECURITY.md` same-UID symlink swap framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Same-UID attacker can repoint cache symlinks before source; same-user framing; not introduced by PID keying; no code change required for this review branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] `skills/design/SKILL.md` possible stale ISSUE_NUMBER / second-invocation guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Mentions follow-up writer call with issue number not present as a second invocation in SKILL; possible stale guidance for `ISSUE_NUMBER` in source-env; separate cleanup issue; not caused by PID symlink change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Committed plan / design run-log snapshots misstate `--claude-pid` regex vs “max 7 digits”
- **Reviewer(s)**: dyn-pid-regex-completeness-output.txt
- **Concern**: Archived plan bodies use acceptance text with `^[1-9][0-9]*$` alongside “max 7 digits,” which is internally inconsistent and does not match implemented grammar `^[1-9][0-9]{0,6}$` in writer and `scripts/write-design-current-env.md`, misleading future `/implement` pre-passes and humans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pid-regex-completeness-output.txt: Update those committed plan bodies to `^[1-9][0-9]{0,6}$` (or equivalent prose: positive integer, no leading zero, at most seven decimal digits) so future `/implement` pre-passes and humans are not misled about the real validator.

---

**Subsumed (no separate `### FINDING_N`):** Positive normative-alignment notes and defensive “not the `--claude-pid` contract” clarifications (input FINDING_28, FINDING_29, FINDING_31) — no distinct behavioral risk beyond what FINDING_3 / FINDING_7 already capture; FINDING_31 partially narrows false positives for FINDING_7 but does not remove the prose/`bash -c` needle concern.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this file.
