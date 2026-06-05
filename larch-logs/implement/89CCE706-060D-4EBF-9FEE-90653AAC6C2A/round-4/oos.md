### FINDING_13: [OUT_OF_SCOPE] Description-mode preamble embeds raw `DESCRIPTION_TEXT`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-specialist-prompt.sh` (≈289–295) interpolates `'${DESCRIPTION_TEXT}'` in trusted prose without `redact-secrets.sh` or markup escaping. Pre-existing prompt-injection surface; not introduced by this branch (`scout-dynamic-archetypes.sh` already uses `escape_prompt_data` for similar data).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Standalone `security` archetype preserved in static panel
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: standalone `security` remains in `static_specialists`; structure/plan-fidelity folded into other lenses without removing the dedicated security slot — aligns with the issue’s “security must stay standalone” decision.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] Generic-diff plan injection hardening (round 3)
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: Positive: generic-mode plan/feature embedding uses `redact-secrets.sh` plus `encoding="literal-redacted"` wrappers (`emit_untrusted_file_block`); regression coverage for tag escaping and token redaction exists in `scripts/test-render-specialist-prompt.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Codex phase-1 re-enable within documented read-only posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: `codex_present_for_waterfall="$CODEX_AVAILABLE"` stays within existing read-only Codex/Cursor review posture in `SECURITY.md`; conditional `--no-fallback` when both vendors are up avoids duplicate Codex fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] `static_archetype_coverage_ok` limits silent lens loss
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: per-archetype coverage fails the round if `security`, `correctness`, `edge-cases`, or `testing` has zero successful static peers, so a lone dropped Cursor peer cannot silently eliminate the security lens when Codex also failed.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] Dropped-slot logging uses redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: dropped-slot logging uses `append-tool-failure.sh` with `--redact`; dynamic scout still treats `prompt_body` as untrusted inside `<scout_notes>`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] Reviewer view: intentional raw Codex transcript reduction in run logs
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Some reviewers treat exclusion of static `codex-specialist-*` and `dyn-*-codex-output.txt` as documented intentional reduction (aggregate artifacts canonical). In-scope findings above treat dynamic Codex twin exclusion as contradicting stated acceptance — disposition is a product/acceptance choice, not a classic vulnerability.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] `--launched-slots` equals `--intended-slots` on production path
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt
- **Severity**: latent
- **Concern**: `review-core.sh` (≈611–616) sets `--launched-slots` to the same value as `--intended-slots`, so `NEVER_LAUNCHED` / `UNACCOUNTED_NEVER_LAUNCHED` in `check-reviewer-failure-threshold.sh` is unused; partial no-output accounting relies on `DROPPED_SLOTS_FILE`. Matches both-vendor behavior; differs from plan “launched vs intended” wording — document, not a functional bug given drop sidecars.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] Cross-layer both-vendor contracts largely align
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt, dyn-vendor-parity-output.txt
- **Severity**: nit
- **Concern**: Positive: `STATIC_SLOT_COUNT`, `DROPPED_SLOTS_FILE`, `--no-fallback`, deduped `count_static_status_once`, no short-circuit on `STATIC_DISPATCH_OK`, dynamic basename exclusion from static denominator, and harnesses for 1-of-8 pass, 5-of-8 fail, dropped-wire, and coverage-on-drops align with stated both-vendor design.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Code review vs plan-review slot naming divergence
- **Reviewer(s)**: dyn-vendor-parity-output.txt
- **Severity**: latent
- **Concern**: Code review reuses manifest `slot` slugs across vendors; plan review uses vendor-prefixed slots. Drop accounting disambiguates via `tool`; operators comparing manifests across skills should expect different naming.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Threshold counts finals, not all phase2 paths
- **Reviewer(s)**: dyn-vendor-parity-output.txt
- **Severity**: latent
- **Concern**: Threshold `--reviewer-output-files` uses dispatch final outputs only; differs from plan “count all phase2/phase3 static failures” wording. Failed finals plus `DROPPED_SLOTS_FILE` cover both-vendor `--no-fallback` paths in practice.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] `--competition-notice-file` still unredacted
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-specialist-prompt.sh` (≈354–357) still `cat`s competition notice without redaction/escaping; pre-existing, unchanged by plan/feature hardening.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] `test-larch-log.sh` lacks static Codex deny assertion
- **Reviewer(s)**: dyn-artifact-retention-output.txt
- **Severity**: latent
- **Concern**: Broader `test-larch-log.sh` write-round section still only asserts denial for `cursor-specialist-*-output.txt`, not static `codex-specialist-*-output.txt`. Predates branch; more material now that Codex static specialists are re-enabled.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] Stale timing kinds in `lib-timing-kinds.sh`
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Allowlist still includes `cursor-specialist-structure`, `cursor-specialist-plan-fidelity`, and matching `codex-specialist-*` kinds though the panel no longer dispatches those slugs. Mostly dead configuration.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Weakened `test-quick-mode-docs-sync.sh` markers
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `POS_MARKERS` no longer pins `5 rounds` or `--panel hard`, so public docs can drift on round-cap and panel argv without failing the harness (appears intentional per updated sibling `.md`).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Summary:** Twelve in-scope merged findings (two **important** clusters dominate: missing `reviewer-testing` plan injection plus doc/test/SECURITY drift, and `larch-log` denying `dyn-*-codex-output` with matching harness inversion). Four additional in-scope items cover coverage/`cap_hit`, scout escaping, threshold accounting, and two nits. Fifteen `[OUT_OF_SCOPE]` items capture pre-existing surfaces, positive notes, and operator-policy disagreements on log retention.

Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

