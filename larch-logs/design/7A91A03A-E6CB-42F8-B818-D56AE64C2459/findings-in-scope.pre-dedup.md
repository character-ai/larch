### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:6-73
- **Concern**: [SCOPE-REDUCTION] Plan still removes the hardcoded SKILL matrix and expands plan-review.md reconcile while binding scope requires leaving the matrix in loaded SKILL prose.. Scenario: Round 3 added Contract-tail replacement, static-slugs enumeration, Consumer/When-to-load/Contract parity greps, and failure-mode checks on top of SKILL stripping. Binding OOS scope records registry dispatch made SKILL duplication optional and rejected dedup as in-scope churn. Implementing this plan ships the opposite plus extra two-file doc churn.
- **Proposed resolution**: Re-scope or close the leave-matrix tracking issue first. Minimum-change path per binding scope: no-op (leave skills/design/SKILL.md matrix prose unchanged; skip plan-review.md topology reconcile).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:10-14
- **Concern**: skills/design/references/plan-review.md:9. Scenario: Opening-summary topology pointer lacks Step-3 load deferral.
- **Proposed resolution**: Plan directs line-10 readers to plan-review.md for panel topology at SKILL load (Steps 0-2b). plan-review.md When to load still forbids loads before Step 3 and Consumer still frames the file as Step-3-loaded. Orchestrators can treat the pointer as an early-load mandate and violate the reference load contract. In the opening-summary edit, state topology detail is normative only at Step 3 via the existing MANDATORY read (not before Step 3). Optionally add one When-to-load sentence that early SKILL pointer is informational and does not authorize pre-Step-3 full-file load.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:51-59
- **Concern**: Static-slots subsection delegates round-1 full static diagonal to Dispatch/Panel pruning without defining the term.. Scenario: After SKILL removes the only full static diagonal prose, plan-review.md still never uses that phrase. Dispatch item 2 and Panel pruning scatter round rules but do not name round-1 all-static-per-vendor shape. Readers following the SKILL deferral lack a single topology anchor for round 1.
- **Proposed resolution**: In Static plan-review slots, add one sentence defining round-1 shape in plain language (four static slugs, Cursor row per slug, Codex row per slug when Codex is present, per existing dispatch). Keep pointers to Dispatch and Panel pruning for round 2+ and prune behavior.



