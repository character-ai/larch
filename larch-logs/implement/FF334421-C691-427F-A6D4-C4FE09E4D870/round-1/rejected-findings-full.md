### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `_write_ship_state` preserves unknown state keys
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: Python state refreshes preserve arbitrary existing `ship-pr-state.sh` keys, widening the durable trust surface for same-UID or prompt-side key injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict merged keys to a documented allowlist matching finalize _FINALIZE_KEY_RE plus orchestrator-seeded fields; drop unknown keys on write.
  - From dyn-prompt-safety-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Stale handoff keys can survive Python state refreshes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Preserved `RESUME_PHASE`, `CALLER_KIND`, and related keys can linger across terminal success or user-input boundaries and mis-route later Exit 4/Step 18a handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Clear handoff keys on terminal success and NEEDS_USER_INPUT boundaries,or overwrite them whenever terminal_outcome is written.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Exit 0 fallback can route default Python runs back to `ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: The Exit 0 fallback still says to re-invoke `ship-pr.sh` without an explicit bash-only qualifier, contradicting the Python-default selector contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add bash-only qualifier or Python selector wording.
  - From cursor-specialist-plan-fidelity-output.txt: Qualify bash-only; add Python selector re-invoke for default path
  - From dyn-ship-state-output.txt: Split Exit 0 into explicit bash vs Python branches (mirror the OOS re-entry wording on the same line), or qualify the “Otherwise” clause with “when `LARCH_SHIP_PR_IMPL=bash`” and add a parallel “on the default Python path, re-invoke the Python selector argv (including `--state-file`); never the fenced `ship-pr.sh` block.”
  - From dyn-plan-voting-output.txt: Qualify the else branch explicitly (“when `LARCH_SHIP_PR_IMPL=bash` …; on the default Python path re-invoke `python3 …/python/ship.py` per the selector”) or move the entire exit-matrix bullet list under a single bash-only wrapper.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Terminal finalize writers can diverge or double-write state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_write_terminal_finalize_if_terminal` and `_persist_stall_metadata_if_needed` both write terminal state; future key drift or duplicate writes could leave Step 18/stall recovery with inconsistent metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate to one terminal writer or narrow the main() backstop to paths that skip the primary writer with a shared field map.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Unconditional post-matrix state-file reads are easy to misinterpret as Python continuation parsing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-plan-voting-output.txt
- **Severity**: latent
- **Concern**: Step 8+ tells the default path not to parse `ship-pr-state.sh` for continuation, but nearby text still instructs state-file reads; reviewers flagged this as either ambiguous or intentional-but-easy-to-misread.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Gate read behind bash or clarify scoped-read-only default path
  - From dyn-plan-voting-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Restore/finalize and implement prose retain stale bash-only writer breadcrumbs
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `restore-finalize-state.md` and several `SKILL.md` passages still name only `ship-pr.sh` for driver/finalize behavior, conflicting with Python-default execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Rewrite the Purpose paragraph to name both writers (`python/ship.py` on terminal outcomes by default; `ship-pr.sh` when `LARCH_SHIP_PR_IMPL=bash`) and reference the Step 18 conditional-restore gate in `skills/implement/SKILL.md`.
  - From dyn-contract-drift-output.txt: Align all three passages with the Step 8+ “active Step 8+ driver (default Python; bash opt-in)” wording used elsewhere in the same file.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Step 8+ prose is overly long and internally fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: Step 8+ mixes Python selector routing, bash matrix prose, and state-file reads in a way that is hard to maintain and can create contradictory routing authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider extracting normative selector contract to a reference file.
  - From dyn-ship-state-output.txt: Restructure Step 8+ into two clearly separated subsections (“Python selector routing” vs “Bash exit matrix”), move all shared Exit 0/3/4/6 handling under the Python selector with bash-only cross-refs, and keep the legacy matrix byte-stable behind an explicit `LARCH_SHIP_PR_IMPL=bash` fence only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

