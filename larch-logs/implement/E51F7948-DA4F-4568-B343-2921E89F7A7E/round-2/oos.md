### FINDING_10: [OUT_OF_SCOPE] decompose-panel-dispatch.md ties DEGRADED_PANEL to obsolete COMBINED_FALLBACK_COUNT rule
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Doc still ties `DEGRADED_PANEL` to `COMBINED_FALLBACK_COUNT > floor(8/2)` instead of `STATIC_DISPATCH_OK` and parse-status semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update to STATIC_DISPATCH_OK and parse-status semantics


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] plan-review.md still documents phase-2/phase-3 paths in design paths-file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reference still states Phase 3 Claude outputs appear in paths-file alongside Phase 1/2; `/design` plan-review now uses `--no-fallback` and omits dropped slots. Phase 2/3 apply only to legacy multi-phase callers (e.g. `/review`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword to state that `/design` paths-files list only succeeded phase-1 outputs and that phase-2/phase-3 paths apply only to the legacy multi-phase waterfall (e.g. `/review` code panel).


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] decompose-aggregator still invokes waterfall without --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `decompose-aggregator.sh` can still cross-tool/Claude-pad failed Codex slots per legacy waterfall, unlike decomposition panel `--no-fallback` profile (plan-intentional but different recovery behavior).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] degraded-tools-gate env fallbacks inherit stale CODEX_PRESENT / CURSOR_PRESENT
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New env fallbacks honor inherited `CODEX_PRESENT` / `CURSOR_PRESENT` when CLI flags omitted; stale exported values in long-lived shell/CI could skew degraded classification and panel sizing (stderr warnings only). Same-UID trust boundary; explicit-flag orchestrators unaffected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: If this becomes painful in shared CI, document “clear probe env between jobs” (as the new harness case does) or gate env reads behind an explicit opt-in.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] test-no-grouped-reuse-guard REUSED_INDICES substring is brittle
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Guard greps `REUSED_INDICES`, which would also match a reintroduced `REUSED_INDICES_FILE` symbol.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] assessor.md describes positional ALL_OUTPUT_TOOLS identity
- **Reviewer(s)**: dyn-caller-output-contracts-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/assessor.md` still describes tool identity from positional `ALL_OUTPUT_TOOLS`; `dispatch-plan-assessors.sh` now uses stable manifest paths and presence/`[[ -s ]]` checks.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] decompose-panel-dispatch.sh paths sidecar comment misdocuments compact matching
- **Reviewer(s)**: dyn-caller-output-contracts-output.txt
- **Severity**: nit
- **Concern**: Inline comment at 296–298 says paths sidecar is one-per-slot manifest order reflecting phase-2/phase-3 fallback; under `--no-fallback` it is a compact succeeded-path set matched by `_match_resolved_output`, not line index.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] review/research SKILL.md gate invocation wording lags external-reviewers.md
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: nit
- **Concern**: `skills/review/SKILL.md` and `skills/research/SKILL.md` still describe env-value invocation without explicit “pass `--codex-*` / `--cursor-*` flags” wording added elsewhere; may keep agents on env-prefix calls (stderr-only warnings).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] degraded-tools-gate /design explanation else branch predates env change
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: nit
- **Concern**: `/design` branch of degraded explanation still documents backup waterfall for non-design skills in `else` branch; unrelated to env-var integration, stale operator text.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] dispatch-plan-review-panel.md still documents PHASE2_RELAUNCH_COUNT
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Contract/docs still reference `PHASE2_RELAUNCH_COUNT` and grouped phase-2 relaunches; not updated in branch. Operators may mis-debug degraded rounds vs `--no-fallback` / `COMBINED_FALLBACK_COUNT` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Sync with --no-fallback availability-gated behavior
  - From cursor-specialist-testing-output.txt: Sync the `.md` with `dispatch-with-waterfall.md` (`COMBINED_FALLBACK_COUNT` only, no grouped reuse).


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

