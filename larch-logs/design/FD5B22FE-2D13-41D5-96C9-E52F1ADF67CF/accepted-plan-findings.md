### FINDING_1: Design panel_verdict must bind from round-local plan-review markdown
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Design `panel_verdict` must bind from round-local plan-review markdown, not run-root cumulative files. Committed design runs can store different finding sets under `plan-review/round-N/accepted-plan-findings.md` vs run-root `accepted-plan-findings.md` (same `FINDING_<n>` id, different concerns). Step 5 says read same-round markdown first but never pins `plan-review/round-{round_num}/` ahead of run-root files. An implementer can membership-test run-root markdown for a `plan-review/round-N/findings-classification.tsv` row, mis-bind `panel_verdict`, and poison prose join plus the gated later accepted-finding index; on a large committed corpus this can invert decisive YES/NO alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step 5 (and Ground-truth semantics panel-verdict binding), require design verdict membership from `plan-review/round-{round_num}/accepted-plan-findings.md` and `rejected-findings.md` derived from the classification TSV path; consult run-root markdown only when that round-local pair is absent. Treat run-root vs round-local disagreement as weak/non-decisive. Add a regression fixture where round-1 TSV `FINDING_1` is accepted in round-local markdown but absent or different at run root.
  - From Cursor-Pragmatic: In step 5 Design prose binding, require path order: for a TSV at `.../plan-review/round-N/findings-classification.tsv`, read `.../plan-review/round-N/accepted-plan-findings.md` and `.../rejected-findings.md` first (index `### FINDING_<n>:` membership), then fall back to run-root markdown only when round-local files are absent; treat run-root vs round-local disagreement as weak/non-decisive.


### FINDING_3: OOS rows need explicit accepted/rejected panel verdict binding before scoring
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: OOS routed rows have no pinned accepted/rejected panel verdict source before scoring. Committed implement JSONL stores OOS records with `outcome=out_of_scope` for both accepted and rejected OOS rows, while the TSV/prose vote tally carries accepted vs rejected. The plan says implement `panel_verdict` comes from JSONL outcome and TSV `voting_result` is only for parsing, then step 8 scores each OOS classification row. An implementer can drop accepted OOS rows as non-accepted or score rejected OOS rows against docked filed issues, corrupting `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: In the OOS branch, bind OOS acceptedness explicitly from the classification TSV voting_result after eligibility plus MAV checks or from the parsed Vote tally Result, and restrict decisive OOS fate scoring to OOS rows whose bound OOS panel result is accepted; rejected, neutral, exonerated, or disagreement rows stay non-decisive.
```


