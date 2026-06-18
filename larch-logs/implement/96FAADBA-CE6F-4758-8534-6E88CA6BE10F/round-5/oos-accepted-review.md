### OOS_6: [OUT_OF_SCOPE] risk-integration: `stall-recovery.md` Step 3 omits `--attempts-file` for `classify`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-parity-output.txt
- **Severity**: nit
- **Concern**: Step 3 classify prose omits `--attempts-file` even though same-cause-repeat requires it. An operator who `init-attempts` then classifies without `--attempts-file` never gets same-cause-repeat promotion; the alternate retry strategy from #3592 stays dormant despite a populated attempts file. Runtime behavior matches retired bash (same-cause only when `--attempts-file` is set); the orchestrator must pass it explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add explicit classify example: `python3 ... stall-recovery classify --implement-tmpdir ... --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"`.
  - From dyn-parity-output.txt: **Pre-existing doc gap:** `skills/implement/references/stall-recovery.md` step 2 pins `--attempts-file` for `init-attempts`, but step 3 does not require passing the same path to `classify`. Runtime behavior now matches retired bash (same-cause only when `--attempts-file` is set); the orchestrator must pass it explicitly.


