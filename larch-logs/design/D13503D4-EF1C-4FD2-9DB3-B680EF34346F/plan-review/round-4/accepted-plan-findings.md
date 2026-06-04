### FINDING_1: Duplicate WARN= in thin-fence display echo
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned thin-fence display pass echoes captured lines outside the 12-key allowlist while WARN= is also replayed in the parse loop. WARN= matches KEY=value shape but is not allowlisted, so both paths emit the same line and operators see duplicate WARN breadcrumbs when a safe `.step3-review-result.env` was loaded (typical rc=0 path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the SKILL.md thin fence, run one pre-parse loop over _plan_review_out that printf display lines only when the key is not in the 12-key set and is not WARN; mirror the same exclusion in test-step3-orchestrator-fence.sh apply_step3_handoff


### FINDING_3: Missing argv reject test for conflicting preview flags
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned mutually exclusive `--preview-only` / `--no-preview` contract has no planned reject-path assertion. Per repo argv-coverage rules, an implementation could silently pick one mode when both flags are passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one argv test in test-run-step3-review.sh asserting --preview-only --no-preview exits 2 with the pinned conflict message, alongside the existing missing/unknown option tests


### FINDING_6: rc!=0 stdout override must not trump safe file-first env
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: The plan says a safely read result env stays authoritative, but also keeps the existing rc!=0 behavior where stdout overwrites a safe file value, creating conflicting precedence rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-protocol-fidelity: Qualify the rc!=0 LOOP_STATUS/TALLY override so it runs only when no safe result env was loaded; move the retained rc case to missing/symlink env and keep a safe-env case proving file wins.


### FINDING_7: exit 2 must short-circuit before LOOP_STATUS normalization
- **Reviewer(s)**: Codex-dyn-kv-protocol-fidelity
- **Severity**: important
- **Concern**: SKILL spec says warn on exit 2 then normalize invalid `LOOP_STATUS` to panel-failed, while the harness short-circuits rc=2 before normalization. A config error could be treated as panel-failed instead of aborting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-protocol-fidelity: State that _plan_review_rc==2 prints the configuration warning and exits/returns before LOOP_STATUS normalization; keep normalization only for non-2 handoffs and mirror that order in the harness.

---

**Merge notes (for voters, not part of machine output):** FINDING_5–7 share the Step 3 KV handoff theme but differ in scenario (stdout-only vs safe file vs rc=2), fix, and test surface — kept separate per aggregator rules. FINDING_3 and FINDING_4 both touch `--preview-only` but one is argv testing and one is control-flow exit — kept separate. No `[OUT_OF_SCOPE]` inputs; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` (non-empty merge).

