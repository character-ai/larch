## Decision 1: Incorporate the determinism-aligned rejected findings (FINDING_1/2/3)
- **Question**: Plan review round 3 raised three rejected findings about preserving always-loaded determinism tokens during the dedup. Should the plan fold them in, given the governing "no determinism regression" constraint?
- **Resolution**: Yes (operator chose "Discuss further" per the orchestrator recommendation). Revise `plan.txt` to make three determinism tokens explicit must-preserve items, each pinned in `test-design-structure.sh`:
  - FINDING_1: keep the always-loaded visible-output continuation trigger `after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue` inline next to the `#anti-halt` cite (the shared `#anti-halt` covers child-Skill returns and Bash-step boundaries, not visible-output continuation). Without it, an implementer could restore halts after a plan print, a voting tally, or a skip breadcrumb.
  - FINDING_2: keep the operative recap-ban trigger verbatim in the preamble stub (`_publish_rc` in {0, 1, 3} plus the non-empty cancellation summary file), not vaguer "after Step 5c" wording.
  - FINDING_3: preserve the Step 5d intra-step ordering token forbidding free-form recap between the mandatory marker-first emit and warning replay/footer, or fold that boundary into the preamble no-recap rule.
- **Source**: user (Gate C "Discuss further") + plan-review reviewers (Cursor archetypes, round 3)

Rationale: these three findings directly serve the operator's stated constraint [[larch-dedup-determinism]] — eliminate duplication, but never trade it for an increase in main-agent non-determinism. The vote did not adopt them (brevity bias), but the operator's principle tips the balance toward explicit, harness-pinned preservation.
