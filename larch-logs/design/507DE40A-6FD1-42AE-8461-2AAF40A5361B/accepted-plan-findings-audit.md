# Accepted plan-review findings audit — /triage (#7080)

Corpus: accepted-plan-findings-all.md (cumulative, rounds 1+2).
End-state diff: plan-before-review.txt -> plan.txt; all accepted findings trace to applied plan changes.

## Classification: all agree, except one strong-disagree on application

### agree (faithfully applied, no Round 1 / outline conflict)
- R1 FINDING_1 (security gates): plan adds both /bug-style gates (SKILL.md line 18). Applied.
- R1 FINDING_3 + R2 FINDING_8 (snapshot freshness / CAS): updatedAt pinning, per-mutation CAS, advance-on-read-back (lines 48, 70-72, 85, 87). Applied.
- R1 FINDING_4 (agent-lint exclusion): agent-lint.toml entry (line 161). Applied.
- R1 FINDING_5 (foreign-repo bound): foreign-repo restriction (line 20). Applied.
- R1 FINDING_7 + R2 FINDING_7 (dependency postcondition / inspect CLI): fail-closed edge read-back; triage inspect verb (lines 49, 60-66, 87). Applied.
- R1 FINDING_8 (neutralize larch markers): outbound marker neutralization (lines 42, 69). Applied.
- R1 FINDING_11 (operator auth): --operator-invoked + check_live_mutation_auth (lines 48, 67). Applied.
- R1 FINDING_13 (constrain refs/paths): validated refs/paths, reject traversal/symlinks (lines 33, 61-66). Applied.
- R1 FINDING_14 (multi-step CAS): advance expected timestamp per mutation (line 72). Applied.
- R1 FINDING_15 (inconclusive verdict): inconclusive no-mutation verdict (lines 47, 53). Applied.
- R1 FINDING_16 + R2 FINDING_10 (safe repro / narrow external probes): safe-probe runner, fixed-destination external probes (lines 36-39, 78). Applied.
- R1 FINDING_17 (--repo to deps): repo threaded to block-issue (line 49). Applied.
- R1 FINDING_19 (report-only analysis rendered): rendered before terminal keys (lines 10, 52). Applied.
- R1 FINDING_20 (complete redaction): full outbound sanitation modeled on deps_audit (lines 42, 69). Applied.
- R1 FINDING_23 (wrap all evidence untrusted): all evidence wrapped (line 17). Applied.
- R2 FINDING_4 (anti-halt wiring): banner, subskill-invocation, harness (lines 15, 142-150). Applied.
- R2 FINDING_6 (immutable main snapshot): immutable-main evidence (lines 19, 62-66). Applied.
- R2 FINDING_9 (title restoration on close): stale-prefix close restoration (lines 27, 45, 71). Applied.

### strong-disagree (application contradicts explicit Round 1 Decision 1)
- R1 FINDING_9 application + valid-verdict body-write mechanism: Decision 1 chose "rewrite the body unified and coherent, original folded in/superseded, NOT a marked section." The final plan instead "preserves the original report and all non-triage body content byte-for-byte" and only "appends or replaces a helper-owned triage section" (lines 41, 44). That reverts the operator's body-rewrite decision to the section-append approach Decision 1 rejected. FINDING_9's core (refuse mutation on active lifecycle state) is agree and correctly applied; the over-broad preserve-original-byte-for-byte extension is the divergence. STRONG_AUDIT_DISSENT=true.
