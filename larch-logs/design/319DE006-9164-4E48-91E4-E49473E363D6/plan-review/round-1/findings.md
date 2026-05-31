### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Part A nit exclusion is specified against round `findings.md` (full ballot) while `accepted_count` comes from `ACCEPTED_COUNT` on accepted findings only. Scenario: Rejected ballot nits inflate `NIT_ACCEPTED_COUNT`, so `NON_NIT_ACCEPTED` is understated and the loop can converge with more than five accepted non-nit findings (e.g. six accepted latent plus many rejected nits)
- **Proposed resolution**: Count nit markers in `$round_dir/accepted-findings.md` (same population as `ACCEPTED_COUNT`); add a harness case with many rejected nits plus six accepted latent that must not converge

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Part A nit subtraction is scoped to round findings.md while ACCEPTED_COUNT is accepted-only. Scenario: Collector findings.md includes rejected/exonerated nits; subtracting that count from accepted_count floors non_nit at 0, so a round with six accepted latent findings can still get converged-small-changes when many rejected nits appear in findings.md
- **Proposed resolution**: Count nit accepted findings in the round accepted_file (same block-aware - **Severity**: nit awk as design accepted-plan-findings.md), not findings.md

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Part A nit counter targets **Nit** but merged findings use - **Severity**: nit. Scenario: aggregate-findings.sh normalizes code-review findings to - **Severity**: nit (see skills/review/scripts/aggregate-findings.sh:249); a **Nit**-only matcher yields nit_count=0 so non_nit equals full ACCEPTED_COUNT and nit-heavy rounds never get exclusion
- **Proposed resolution**: Mirror plan-review-loop _count_nit_findings: awk on ### FINDING_ blocks for /^- \*\*Severity\*\*: nit/ in round-N/findings.md (optionally add title-line fallbacks only if tests need them)

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Implement nit counter targets wrong file and marker. Scenario: Aggregator output uses `- **Severity**: nit` in `round-N/findings.md` (and accepted blocks in `accepted-findings.md`), not `**Nit**` headings. Counting `**Nit**` in `findings.md` yields NIT_COUNT=0, so nits never subtract from ACCEPTED_COUNT; counting nits from the full ballot can also exceed ACCEPTED_COUNT and floor NON_NIT to 0, causing premature `converged-small-changes`
- **Proposed resolution**: Mirror design: block-aware awk on `round-N/accepted-findings.md` with `^- **Severity**: nit` (or resolve `ACCEPTED_FINDINGS_FILE` from review-core.env); derive NON_NIT from accepted findings only

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:51
- **Concern**: Plan removes LARCH_DESIGN_CONVERGENCE_THRESHOLD and --convergence-threshold entirely; feature description says only to bump the default from 3 to 5. Scenario: Feature description says "bump the convergence threshold default from 3 to 5" — the env var and flag are stated as the named mechanism. Plan deletes them entirely and hardcodes 5, making any stale caller passing --convergence-threshold hit exit 2 ("unknown option") rather than getting the new default
- **Proposed resolution**: Keep --convergence-threshold and LARCH_DESIGN_CONVERGENCE_THRESHOLD but change the default to 5; remove them only if the feature description is revised to say "remove configurability"

### FINDING_6:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:1366
- **Concern**: Nit-exclusion logic (NON_NIT_ACCEPTED_COUNT ≤ 5) is scope creep not present in the feature description. Scenario: Feature description says "≤5 accepted and 0 important accepted" — a simple total ACCEPTED_COUNT check. Plan changes this to ≤5 non-nit accepted, meaning a round with 3 latent + 10 nit (13 total) now converges where the feature description would not allow it. Adds a new _count_nit_findings helper and two new KV fields beyond what was asked
- **Proposed resolution**: Drop nit-exclusion; use ACCEPTED_COUNT ≤ 5 as stated in the feature description. Accept the simpler formula the requester specified.

### FINDING_7:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1372
- **Concern**: Scope expansion to /implement code-review loop not mentioned in the feature description. Scenario: Feature description explicitly limits scope to "plan-review-loop.sh and the documentation that states the threshold/streak." Adding review-and-fix.sh carries the nit-exclusion complexity (Finding 2) and flag-removal breaking change (Finding 1) into a second loop not covered by the stated requirements
- **Proposed resolution**: Defer /implement loop changes to a separate issue, or confirm the feature description should be widened before landing both together

### FINDING_8:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Plan specifies implement nit counting via `**Nit**` in `findings.md`. Scenario: Code-review findings use `- **Severity**: nit` (see `skills/review/scripts/aggregate-findings.sh`); a `**Nit**` grep counts zero nits so `non_nit_accepted` equals full `ACCEPTED_COUNT` and nit-heavy accepted rounds fail to get nit exclusion
- **Proposed resolution**: Mirror `_count_important_findings` / design: awk or grep on `- **Severity**: nit` inside each `### FINDING_N:` block

### FINDING_9:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1370-1405
- **Concern**: Plan counts nits in full `findings.md` while `ACCEPTED_COUNT` is accepted-only. Scenario: Rejected nits in `findings.md` inflate `NIT_ACCEPTED_COUNT` and floor `NON_NIT_ACCEPTED_COUNT` to 0, so a round with 6 accepted latent plus many rejected nits can converge when it should not
- **Proposed resolution**: Count nit severity only in `round-N/accepted-findings.md` (same path as `ACCEPTED_COUNT`), not the merged ballot `findings.md`

### FINDING_10:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:389-401
- **Concern**: Plan removes `CONVERGENCE_STREAK` from stdout and `.step3-plan-review-result.env` but not `_write_round_summary`. Scenario: Every `plan-review/round-N/round-summary.env` still carries `CONVERGENCE_STREAK`, contradicting the grep sweep and new KV contract; harnesses or operators reading per-round summaries see stale semantics
- **Proposed resolution**: Remove `CONVERGENCE_STREAK` from `_write_round_summary`; update `skills/design/scripts/plan-review-loop.md` round-summary key list (~line 52) if still documented

### FINDING_11:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.md:47-62
- **Concern**: Plan only rewrites the `--convergence-threshold` argv bullet, not remaining convergence prose. Scenario: Lines 48-50 and exit-code line 62 still describe two consecutive rounds and `convergence-threshold`; docs disagree with single-round hardcoded ≤5 non-nit behavior
- **Proposed resolution**: Replace argv bullet with hardcoded rule; update lines 48-50 and the `converged-small-changes` exit `0` bullet to single non-degraded round, ≤5 non-nit accepted, 0 important, nits excluded

### FINDING_12:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan §"UPDATED: skills/review-and-fix/scripts/review-and-fix.sh" → Nit counter bullet; plan §"Failure modes" → "Nit miscount" bullet
- **Concern**: Plan prescribes **Nit** as the /implement nit marker, but findings.md (aggregator output) uses `- **Severity**: nit` (lowercase, per agents/orchestrator-aggregator.md:30-37 and confirmed in larch-logs/implement/1446FF4C-B070-45B2-901C-4EAD31252CB9/round-3/findings.md:25). If the implementer mirrors important_findings_present (which uses **[Ii]mportant** patterns) for nit, no line in findings.md will match.. Scenario: NIT_ACCEPTED_COUNT=0 in every /implement round; nit findings are never subtracted from the convergence count; the ≤5 bound applies to all accepted findings including nits — directly contradicting the plan's stated nit-exclusion goal for /implement while /design (which specifies ^- \*\*Severity\*\*: nit) works correctly.
- **Proposed resolution**: Specify ^- \*\*Severity\*\*: nit as the /implement nit marker, identical to the /design _count_nit_findings helper; both loops' findings.md files are produced by the orchestrator-aggregator which outputs `- **Severity**: important|latent|nit` (lowercase) — not **Nit** bold prose.

### FINDING_13:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan §"UPDATED: skills/review-and-fix/scripts/review-and-fix.sh" → "Derive non-nit accepted = accepted_count − nit_count" sentence
- **Concern**: Plan counts nit findings from findings.md (all findings, including rejected) but subtracts from accepted_count (accepted-only). The /design parallel correctly scans accepted-plan-findings.md (accepted-only). When nit findings are rejected — common since nits are optional — nit_count > nit_accepted_count, making non_nit_accepted = accepted_count − nit_count_all undercount actual non-nit accepted.. Scenario: Round with 8 accepted non-nit + 4 rejected nit + 0 accepted nit: accepted_count=8, nit_count_from_findings_md=4, non_nit_accepted=max(0,8−4)=4 (≤5, converges). Actual non-nit accepted=8 (>5, should not converge). The loop terminates while 8 non-nit issues remain accepted.
- **Proposed resolution**: Count nit findings from the round's accepted-findings.md (accepted-only), matching /design's pattern of scanning accepted-plan-findings.md; the accepted-findings.md per-round file already exists at $IMPLEMENT_TMPDIR/round-N/accepted-findings.md.

### FINDING_14:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1372-1405
- **Concern**: Plan's nit counter scans `findings.md` (ALL findings) and subtracts from `accepted_count` (ACCEPTED only), mixing populations. Scenario: When rejected nit findings outnumber accepted nit findings, `nit_count` is inflated: e.g., 7 rejected nits + 6 accepted latent ⇒ accepted_count=6, nit_count=7, non_nit_accepted=max(0,6−7)=0 ≤5 → loop exits prematurely despite 6 actual non-nit accepted findings that should have blocked convergence (6>5)
- **Proposed resolution**: Count nit-severity findings from `accepted_file` (accepted-findings.md), mirroring `count_high_severity_accepted` which already scans `accepted_file` — not `findings.md`. The nit marker `**Nit**` is correct; only the source file must change.

### FINDING_15:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:389
- **Concern**: `_write_round_summary` still emits `CONVERGENCE_STREAK` but the plan removes all variable assignments to it. Scenario: After plan lands, `CONVERGENCE_STREAK` is unset everywhere; `_write_round_summary` falls through to `${CONVERGENCE_STREAK:-0}` and silently writes `CONVERGENCE_STREAK=0` to every `round-summary.env`. The plan's failure-modes section says "remove all `/design` references" but its explicit change list omits line 389 and the matching `round-summary.env` schema entry in `plan-review-loop.md:52`. An implementer following the explicit change list literally misses this site.
- **Proposed resolution**: Add `skills/design/scripts/plan-review-loop.sh:389` to the explicit change list: replace `printf 'CONVERGENCE_STREAK=%s\n' "${CONVERGENCE_STREAK:-0}"` with `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` lines (mirroring the treatment at lines 147 and 165), and note `plan-review-loop.md:52` (round-summary.env schema) as a companion update.

### FINDING_16:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1258,1274
- **Concern**: `NIT_ACCEPTED_COUNT` not set to 0 on `panel-failed` and `tally-error` early-exit paths. Scenario: Lines 1258 and 1274 explicitly set `IMPORTANT_ACCEPTED_COUNT=0` for rounds where the panel or tally failed, but the plan's NIT computation sites are only lines 1247 and 1285. On round 2+ exits via these error paths, `NIT_ACCEPTED_COUNT` carries the stale value from the previous round's computation at line 1285, so `emit_loop_kvs` and `write_step3_result_env` emit a non-zero stale value. No downstream decision reads `NIT_ACCEPTED_COUNT` on error exits, so there is no behavioral breakage, but the emitted value is wrong and could confuse test assertions added against these paths.
- **Proposed resolution**: Alongside the `IMPORTANT_ACCEPTED_COUNT=0` assignments at lines 1258 and 1274, add `NIT_ACCEPTED_COUNT=0` and `NON_NIT_ACCEPTED_COUNT=0`, matching the parallel treatment already prescribed for `IMPORTANT_ACCEPTED_COUNT` on those paths.

### OOS_1:
- **Description**: Prose names `LARCH_DESIGN_CONVERGENCE_THRESHOLD` alongside `LARCH_DESIGN_ROUND_CAP` in the Gate B apply contract note; this env var is fully removed by the plan but `approval-gates.md` is absent from the plan's update list. Scenario: After the PR lands `approval-gates.md:209` still references the removed env var; the drift-prone-prose-in-docs rule requires a grep sweep of docs/ for stale names, and the plan's own "Failure modes" section acknowledges a grep-sweep mitigation — but the file is not added to the explicit update list
- **Reviewer**: unknown-slot
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/references/approval-gates.md:209
- **Phase**: design
