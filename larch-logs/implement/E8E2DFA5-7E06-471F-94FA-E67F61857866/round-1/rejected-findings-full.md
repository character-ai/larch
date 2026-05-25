### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: `6624f0e5` — Remove FILES_COUNT and soft-trigger machinery from `/design` plan-size check (8 files; functional change)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `6624f0e5` — Remove FILES_COUNT and soft-trigger machinery from `/design` plan-size check (8 files; functional change)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: `5aca7759` — `chore(larch-logs)` design run flush (excluded per review scope rules)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `5aca7759` — `chore(larch-logs)` design run flush (excluded per review scope rules) Security review focuses on commit `6624f0e5`. ## Summary This change removes soft plan-size metrics (`FILES_COUNT`, `SOFT_TRIGGER_FIRED`, soft thresholds) from `check-plan-size.sh`, drops orchestrator-only semantic-soft branching in Step 2b.5, and routes `--partition` / `partition_requested` directly to Split-path without a Step 2b.5 `AskUserQuestion`. The shell helper still only reads a plan file with fixed `awk`/`grep` patterns and emits fixed KV tokens; no new shell interpolation, deserialization, network, or secret-handling paths were added.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **Plan-content influence reduced:** Removing `SEMANTIC_SOFT_ESTIMATE` and mechanical soft triggers means plan text can no longer nudge Step 2b.5 toward a sprawl prompt via file-count or orchestrator discretion at this step. That is a security-positive workflow hardening, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Plan-content influence reduced:** Removing `SEMANTIC_SOFT_ESTIMATE` and mechanical soft triggers means plan text can no longer nudge Step 2b.5 toward a sprawl prompt via file-count or orchestrator discretion at this step. That is a security-positive workflow hardening, not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **`--partition` auto-Split-path:** The new partition branch (`skills/design/SKILL.md` item 5) skips the former soft-branch `AskUserQuestion`, but `partition_requested` is still sourced only from argv → `write-run-params.sh` / jq merge into `$DESIGN_TMPDIR/run-params.json`, not from plan body parsing. Hard triggers still require Split/Cancel confirmation. Residual risk is limited to a session where an attacker can already pass `-p` or tamper with `run-params.json` inside `DESIGN_TMPDIR`—the same trust boundary that existed before this diff, now with one fewer confirmation gate when `-p` was explicitly chosen.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--partition` auto-Split-path:** The new partition branch (`skills/design/SKILL.md` item 5) skips the former soft-branch `AskUserQuestion`, but `partition_requested` is still sourced only from argv → `write-run-params.sh` / jq merge into `$DESIGN_TMPDIR/run-params.json`, not from plan body parsing. Hard triggers still require Split/Cancel confirmation. Residual risk is limited to a session where an attacker can already pass `-p` or tamper with `run-params.json` inside `DESIGN_TMPDIR`—the same trust boundary that existed before this diff, now with one fewer confirmation gate when `-p` was explicitly chosen.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **`check-plan-size.sh`:** `--plan-file` / `$DESIGN_TMPDIR/plan.txt` arbitrary read is unchanged from main; not introduced by this branch.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`check-plan-size.sh`:** `--plan-file` / `$DESIGN_TMPDIR/plan.txt` arbitrary read is unchanged from main; not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

