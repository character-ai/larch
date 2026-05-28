### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1005-1012; skills/design/scripts/plan-review-loop.sh:98-107
- **Concern**: Plan documents env-var fallback/clamping that the launcher does not implement. Scenario: SKILL.md forwards LARCH_DESIGN_ROUND_CAP and LARCH_DESIGN_CONVERGENCE_THRESHOLD directly; plan-review-loop hard-errors invalid values, permits round caps above 5, and permits convergence threshold 0. Operators reading the new docs would expect fallback/default or SIMPLE clamping that will not happen.
- **Proposed resolution**: For this docs-only PR, revise the proposed docs to match current behavior: default 5/3, invalid argv/env values fail the plan-review-loop validation, convergence threshold is non-negative, and the Gate C review-run cap is separate from the loop-internal round cap. Only document fallback/clamping if the plan also adds the code change.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-design-round-artifacts.sh:17-30
- **Concern**: docs/run-logs.md plan says it will enumerate allowlisted per-round artifacts but omits several allowlisted names and patterns. Scenario: The authoritative allowlist also includes plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, *-vote-output.txt, *-vote-output-first-pass.txt, and voter*-diag.txt. The proposed docs would drift from the actual publish contract immediately.
- **Proposed resolution**: Add those top-level basenames and patterns to the planned docs/run-logs.md section, or narrow the prose so it explicitly says the list is representative and points to scripts/lib-design-round-artifacts.md for the complete allowlist.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lib-design-round-artifacts.sh:17-30
- **Concern**: Per-round artifact doc plan omits allowlisted artifacts while claiming to enumerate the allowlist. Scenario: The proposed docs/run-logs.md section would omit plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, vote output files, and voter diagnostics, so operators cannot reconcile committed design logs with the documented artifact list.
- **Proposed resolution**: Add the omitted allowlisted basenames/patterns, or narrow the prose to say it lists selected artifacts and point to scripts/lib-design-round-artifacts.sh as the mechanical authority.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:99-107
- **Concern**: Env-var docs would promise fallback and caps that the launcher does not enforce. Scenario: SKILL.md passes LARCH_DESIGN_ROUND_CAP and LARCH_DESIGN_CONVERGENCE_THRESHOLD directly to plan-review-loop.sh; invalid values exit 2, threshold 0 is accepted, and round-cap has no upper clamp
- **Proposed resolution**: Keep the docs-only scope by documenting the actual argv validation semantics, or expand the plan to add script fallback/clamping plus tests

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-design-round-artifacts.sh:17-30
- **Concern**: The proposed run-log artifact enumeration omits allowlisted round artifacts. Scenario: The plan says docs/run-logs.md will enumerate artifacts allowlisted by scripts/lib-design-round-artifacts.sh, but its proposed list excludes plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, *-vote-output.txt, *-vote-output-first-pass.txt, and voter*-diag.txt
- **Proposed resolution**: Either include every allowlisted artifact/pattern in the new docs/run-logs.md section or narrow the wording to say the section lists common artifacts and points to the allowlist for the full set

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1005-1012; skills/design/scripts/plan-review-loop.sh:98-107
- **Concern**: Plan documents fallback/clamp semantics for multi-round env vars that the code does not implement. Scenario: An operator sets LARCH_DESIGN_ROUND_CAP or LARCH_DESIGN_CONVERGENCE_THRESHOLD to a malformed value expecting the documented default fallback, but Step 3 forwards it raw and plan-review-loop.sh exits 2; docs also say positive integer for convergence even though zero is accepted, and imply a SIMPLE/tier clamp that is separate from the inner loop cap
- **Proposed resolution**: Document the actual current behavior, or explicitly add a code change if fallback/clamping is intended; minimum-change path is to say empty uses defaults, invalid values hard-error, convergence threshold is non-negative, and Step 3 tier entry caps are distinct from --round-cap

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-design-round-artifacts.sh:17-30
- **Concern**: The run-log artifact enumeration proposed for docs/run-logs.md omits allowlisted per-round files. Scenario: The plan says to enumerate artifacts allowlisted by scripts/lib-design-round-artifacts.sh, but leaves out plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, *-vote-output.txt, *-vote-output-first-pass.txt, and voter*-diag.txt; the new docs would still be incomplete against the named source of truth
- **Proposed resolution**: Add a small "Manifests and voter diagnostics" group with those allowlisted names, or narrow the prose so it does not claim complete enumeration

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:935-1012; skills/design/scripts/plan-review-loop.sh:98-107
- **Concern**: Env-var docs in the plan promise fallback and SIMPLE clamping that the driver does not implement. Scenario: The plan asks docs/configuration-and-permissions.md to say both env vars fall back on invalid/empty/non-numeric and flags.md to say SIMPLE clamps LARCH_DESIGN_ROUND_CAP above the tier cap, but plan-review-loop exits 2 for invalid --round-cap/--convergence-threshold, accepts convergence threshold 0, and SKILL.md passes LARCH_DESIGN_ROUND_CAP directly to the inner loop
- **Proposed resolution**: Keep the PR docs-only by documenting actual behavior: empty shell expansion defaults, invalid round cap/threshold rejected by the driver, convergence threshold is non-negative, and Step 3 re-entry cap is separate from inner LARCH_DESIGN_ROUND_CAP; add code and tests only if clamping/fallback is intended

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:17-80
- **Concern**: Mixed-severity fallback rule contradicts the proposed Gate B prompt rule and adds unnecessary complexity. Scenario: The plan says structured H/M/L counts are used only when every accepted finding has a Severity field and otherwise falls back to Concern-text C/H/M/L counts, but the edge case later says mixed files use per-finding hybrid counts; implementers could document incompatible Gate B behavior
- **Proposed resolution**: Use the all-or-nothing rule from the acceptance criterion, or explicitly define a hybrid question text including Critical; for this SIMPLE lane, remove the per-finding hybrid edge case and fall back to Concern-text when any accepted finding lacks Severity

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:98-107; skills/design/SKILL.md:935-1012; <TMPDIR>/plan.txt:27-34
- **Concern**: Planned env-var docs describe fallback and tier clamping that the scripts do not implement. Scenario: With LARCH_DESIGN_ROUND_CAP or LARCH_DESIGN_CONVERGENCE_THRESHOLD set to a non-numeric value, SKILL.md passes that value as explicit argv and plan-review-loop.sh exits 2 instead of falling back; values above 5 are not clamped by the loop; convergence threshold 0 is accepted though the plan calls it positive
- **Proposed resolution**: Document the current script contract: round cap argv must be positive, convergence threshold argv must be non-negative, invalid explicit values exit 2, and no max-5 clamp exists unless this docs-only plan is expanded to change code

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-design-round-artifacts.sh:17-30; docs/run-logs.md:130-172; <TMPDIR>/plan.txt:45-53
- **Concern**: The planned run-log section says it enumerates allowlisted per-round artifacts but omits several allowlisted basenames. Scenario: The proposed docs would miss plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, *-vote-output.txt, *-vote-output-first-pass.txt, and voter*-diag.txt even though lib-design-round-artifacts.sh allows them
- **Proposed resolution**: Either add the missing allowlisted names to docs/run-logs.md or narrow the prose from exhaustive enumeration to selected common artifacts

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-script-ground-truth, Codex-dyn-script-ground-truth
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:108-124; skills/design/scripts/revise-plan-with-waterfall.sh:365-390; <TMPDIR>/plan.txt:36-43
- **Concern**: The planned SECURITY.md paragraph says outputs are confined to the revise directory while the script also creates a sibling snapshot outside that directory. Scenario: On failed-no-patch, failed-validation, or failed-apply, plan.txt.before-revise remains beside DESIGN_TMPDIR/plan.txt, so broad output-confinement prose would be inaccurate
- **Proposed resolution**: Narrow the sentence to say launcher outputs, prompts, and candidate patches are confined to plan-review/round-<N>/revise/, and explicitly note that the rollback snapshot is intentionally plan.txt.before-revise outside that subtree on failure

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-cross-doc-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md (planned); skills/design/scripts/plan-review-loop.sh:98-107; skills/design/SKILL.md:1011-1012
- **Concern**: Planned env-var docs promise invalid/empty values fall back to defaults. Scenario: Non-numeric LARCH_DESIGN_ROUND_CAP or LARCH_DESIGN_CONVERGENCE_THRESHOLD is passed through SKILL as --round-cap/--convergence-threshold and plan-review-loop.sh exits 2; Step 3 fails instead of using 5/3
- **Proposed resolution**: Document exit-2 behavior to match plan-review-loop.sh, or add the same normalization pattern as LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD in emit-design-plan-preview.sh before argv is built

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-cross-doc-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:27-30; docs/configuration-and-permissions.md:32-35; skills/design/SKILL.md:1005-1012; skills/design/scripts/plan-review-loop.sh:98-107
- **Concern**: Planned env-var docs describe fallback and cap behavior that the code does not implement. Scenario: The plan says invalid or non-numeric values fall back to defaults and implies caps are clamped, but Step 3 passes env values directly and plan-review-loop exits 2 on invalid --round-cap or --convergence-threshold; convergence threshold also accepts 0
- **Proposed resolution**: Keep the PR docs-only: document the current behavior exactly, including empty unset defaulting, invalid non-numeric values failing, positive ROUND_CAP, and non-negative CONVERGENCE_THRESHOLD

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-cross-doc-integrity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/run-logs.md:130-172; scripts/lib-design-round-artifacts.sh:17-31
- **Concern**: Per-round artifact enumeration is planned as exhaustive but omits allowlisted artifacts. Scenario: The plan says docs/run-logs.md will enumerate artifacts allowlisted by scripts/lib-design-round-artifacts.sh, but the proposed list omits plan-review-slots.ndjson, plan-voter-slots.ndjson, scout-plan-manifest.json, plan.txt, *-vote-output.txt, *-vote-output-first-pass.txt, and voter*-diag.txt
- **Proposed resolution**: Add the omitted allowlisted names or explicitly state the section is a summary and that scripts/lib-design-round-artifacts.md is exhaustive

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-cross-doc-integrity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:101-117
- **Concern**: The structured-severity fallback rule is inconsistent for mixed findings. Scenario: The plan says structured bucket counts are used only when every finding has - **Severity**:, but its edge case says mixed files use structured severity per finding and Concern-text fallback for the rest
- **Proposed resolution**: Choose one rule; the least invasive fix is to document per-finding fallback consistently and specify that mixed counts keep the Critical column if any Concern-text fallback can produce Critical

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-test-pin-adequacy, Codex-dyn-test-pin-adequacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:63-67
- **Concern**: FINDING_N structure-test pin omits two required template fields. Scenario: The plan requires the template to keep Concern and Proposed resolution (plan.txt:9,102), and Gate B consumes Concern for presentation (skills/design/references/approval-gates.md:95-105), but the planned assertion checks only Reviewer(s), Severity, Focus area, and Location; removing or renaming Concern or Proposed resolution in skills/design/references/plan-review.md would still pass
- **Proposed resolution**: Extend the planned Accepted FINDING_N template-block assertion to check all required field labels exactly: - **Reviewer(s)**:, - **Severity**:, - **Focus area**:, - **Location**:, - **Concern**:, and - **Proposed resolution**:
