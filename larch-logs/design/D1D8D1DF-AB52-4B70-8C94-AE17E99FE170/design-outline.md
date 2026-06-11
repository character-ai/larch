## Proposed Design Outline

### Goals
- Replace first-detection filing with terminal-only filing; add escalation-on-success filing for runs that succeed after script-to-main-agent handoffs.
- Require Main Claude root-cause investigation before any issue is filed; verdict (`larch-defect | environment | operator-action`) gates filing.
- Implement two-tier content policy: Tier A (dev clone) gets full unrestricted body; Tier B (consumer) gets expanded-but-bounded machine-composed body.

### Non-goals
- No /design escalation wiring (that's #3992).
- No change to retry caps, classifier logic, or resume-hint routing.
- No cross-repo filing (that's #3991).

### Approach sketch
- Delete `root_cause_template`/`mitigation_template` and first-detection filing from `stall-recovery-report.sh` and `stall-recovery.md`.
- Add `record-escalation` subcommand to `stall-recovery-report.sh`; instrument `lint-fix-loop.sh`, `run-step5-review.sh`, and `ship-pr.sh` to call it at their main-agent-required bail sites.
- Rewrite `cmd_bug_body_like` into Tier A / Tier B composition paths; Tier A accepts a `--root-cause-file` written by Main Claude; Tier B accepts a `--bounded-root-cause-file`.
- Update `stall-recovery.md` procedure: insert escalation-ledger init + escalation-on-success path (steps 7a–7b); replace step 4 first-detection with "skip" and step 8 with new investigation-then-file body.
- Update SECURITY.md to describe two-tier contract; expand Tier B allowlist in TSV/code/doc.

### Surfaces in scope
- `skills/implement/scripts/stall-recovery-report.sh`
- `skills/implement/scripts/stall-recovery-report.md`
- `skills/implement/scripts/stall-recovery-report-allowlists.tsv`
- `skills/implement/scripts/test-stall-recovery-report.sh`
- `skills/implement/scripts/test-stall-recovery-report.md`
- `skills/implement/references/stall-recovery.md`
- `scripts/lint-fix-loop.sh`, `scripts/lint-fix-loop.md`
- `scripts/run-step5-review.sh`, `scripts/run-step5-review.md`
- `scripts/ship-pr.sh`, `scripts/ship-pr.md`
- `SECURITY.md`
- `skills/implement/SKILL.md` (Step 18a helper surface reference)

### Open questions
- None.
