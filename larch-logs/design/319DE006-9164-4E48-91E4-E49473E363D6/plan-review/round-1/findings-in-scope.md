Verifying key code locations to normalize merged concerns accurately.
Structured aggregator output from the supplied reviewer findings (plain text; no empty-merge attestation).

### FINDING_1: Implement Part A nit exclusion can miscount or never subtract nits
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Concern**: The planned `/implement` Part A change derives `NON_NIT_ACCEPTED` from `ACCEPTED_COUNT` (accepted-only) but counts nits from the wrong population and/or the wrong marker. Code-review aggregator output uses `- **Severity**: nit` in `findings.md` / `accepted-findings.md`, not `**Nit**` headings. Counting nits in full-round `findings.md` includes rejected/exonerated nits, which can inflate `nit_count`, floor `non_nit_accepted` to 0, and allow premature `converged-small-changes` (e.g. six accepted latent plus many rejected nits). A `**Nit**`-only matcher can yield `nit_count=0`, so nits are never excluded and the ≤5 bound applies to all accepted findings including nits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Count nit markers in `$round_dir/accepted-findings.md` (same population as `ACCEPTED_COUNT`); add a harness case with many rejected nits plus six accepted latent that must not converge
  - From Cursor-Edge: Count nit accepted findings in the round accepted_file (same block-aware - **Severity**: nit awk as design accepted-plan-findings.md), not findings.md
  - From Cursor-Innovation: Mirror plan-review-loop _count_nit_findings: awk on ### FINDING_ blocks for /^- \*\*Severity\*\*: nit/ in round-N/findings.md (optionally add title-line fallbacks only if tests need them)
  - From Cursor-Pragmatic: Mirror design: block-aware awk on `round-N/accepted-findings.md` with `^- **Severity**: nit` (or resolve `ACCEPTED_FINDINGS_FILE` from review-core.env); derive NON_NIT from accepted findings only
  - From unknown-slot: Mirror `_count_important_findings` / design: awk or grep on `- **Severity**: nit` inside each `### FINDING_N:` block
  - From unknown-slot: Count nit severity only in `round-N/accepted-findings.md` (same path as `ACCEPTED_COUNT`), not the merged ballot `findings.md`
  - From unknown-slot: Specify ^- \*\*Severity\*\*: nit as the /implement nit marker, identical to the /design _count_nit_findings helper; both loops' findings.md files are produced by the orchestrator-aggregator which outputs `- **Severity**: important|latent|nit` (lowercase) — not **Nit** bold prose.
  - From unknown-slot: Count nit findings from the round's accepted-findings.md (accepted-only), matching /design's pattern of scanning accepted-plan-findings.md; the accepted-findings.md per-round file already exists at $IMPLEMENT_TMPDIR/round-N/accepted-findings.md.
  - From unknown-slot: Count nit-severity findings from `accepted_file` (accepted-findings.md), mirroring `count_high_severity_accepted` which already scans `accepted_file` — not `findings.md`. The nit marker `**Nit**` is correct; only the source file must change.

### FINDING_2: Removing design convergence-threshold flag/env breaks callers
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The feature description calls for bumping the convergence threshold default from 3 to 5 via the named env var and `--convergence-threshold` mechanism. The plan removes `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and `--convergence-threshold` entirely and hardcodes 5, so stale callers passing `--convergence-threshold` hit exit 2 ("unknown option") instead of the new default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Keep --convergence-threshold and LARCH_DESIGN_CONVERGENCE_THRESHOLD but change the default to 5; remove them only if the feature description is revised to say "remove configurability"

### FINDING_3: Design nit-exclusion diverges from stated feature description
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The feature description specifies convergence as ≤5 accepted and 0 important accepted (simple `ACCEPTED_COUNT`). The plan uses ≤5 non-nit accepted, so a round with 3 latent + 10 nit (13 total) converges under the plan but not under the stated requirement. This adds `_count_nit_findings` and extra KV fields beyond the request.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Drop nit-exclusion; use ACCEPTED_COUNT ≤ 5 as stated in the feature description. Accept the simpler formula the requester specified.

### FINDING_4: `/implement` loop changes extend beyond feature scope
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Concern**: The feature description limits scope to `plan-review-loop.sh` and documentation for threshold/streak. Adding `review-and-fix.sh` pulls nit-exclusion and related convergence changes into a second loop not covered by the stated requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Defer /implement loop changes to a separate issue, or confirm the feature description should be widened before landing both together

### FINDING_5: `CONVERGENCE_STREAK` remains in per-round `round-summary.env`
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan removes `CONVERGENCE_STREAK` from stdout and `.step3-plan-review-result.env` but not from `_write_round_summary`. Each `plan-review/round-N/round-summary.env` can still carry `CONVERGENCE_STREAK` (or `${CONVERGENCE_STREAK:-0}` after assignments are removed), contradicting the grep sweep and new KV contract and confusing harnesses or operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Remove `CONVERGENCE_STREAK` from `_write_round_summary`; update `skills/design/scripts/plan-review-loop.md` round-summary key list (~line 52) if still documented
  - From unknown-slot: Add `skills/design/scripts/plan-review-loop.sh:389` to the explicit change list: replace `printf 'CONVERGENCE_STREAK=%s\n' "${CONVERGENCE_STREAK:-0}"` with `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` lines (mirroring the treatment at lines 147 and 165), and note `plan-review-loop.md:52` (round-summary.env schema) as a companion update.

### FINDING_6: `review-and-fix.md` convergence prose still describes old behavior
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan only rewrites the `--convergence-threshold` argv bullet. Other lines still describe two consecutive rounds and `convergence-threshold`, disagreeing with the planned single-round hardcoded ≤5 non-nit rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Replace argv bullet with hardcoded rule; update lines 48-50 and the `converged-small-changes` exit `0` bullet to single non-degraded round, ≤5 non-nit accepted, 0 important, nits excluded

### FINDING_7: `NIT_ACCEPTED_COUNT` not cleared on design error exit paths
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Concern**: On `panel-failed` and `tally-error` paths the plan sets `IMPORTANT_ACCEPTED_COUNT=0` but not `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT`, so round 2+ error exits can emit stale nit counts from the prior round. No downstream decision reads them on those paths, but emitted values are wrong and may confuse new test assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Alongside the `IMPORTANT_ACCEPTED_COUNT=0` assignments at lines 1258 and 1274, add `NIT_ACCEPTED_COUNT=0` and `NON_NIT_ACCEPTED_COUNT=0`, matching the parallel treatment already prescribed for `IMPORTANT_ACCEPTED_COUNT` on those paths.
