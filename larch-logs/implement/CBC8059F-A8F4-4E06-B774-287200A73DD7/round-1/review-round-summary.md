# Review Round 1

- Mode: `diff`
- Accepted findings: 12
- Rejected findings: 4
- Exonerated findings: 0
- Neutral findings: 5

## Accepted Findings

### FINDING_1: **Important** `correctness` `skills/review/scripts/review-core.sh:342`: The new nested review breadcrumbs are emitted from scripts whose stdout is redirected into capture files, so they are not operator-visible. `review-and-fix.sh` invokes review-core with `> "$core_out"` at `skills/review-and-fix/scripts/review-and-fix.sh:986`, and review-core invokes dispatch-panel with `> "$dispatch_out"` at `skills/review/scripts/review-core.sh:290`; because `larch_quiet_init` binds FD 3 to the child’s current stdout, breadcrumbs at `skills/review/scripts/review-core.sh:342` and `skills/review/scripts/dispatch-panel.sh:409-411` land in `round-N/review-core.env` / `review-core-dispatch.env` instead of the terminal. Concrete failing scenario: during a long Step 5 reviewer launch or collection phase with `LARCH_QUIET_BREADCRUMBS=1`, the operator still sees no `→ review: launching ...` or `→ review: consolidating findings` progress line. Fix by passing a dedicated inherited progress FD that `larch_quiet_init` does not rebind, or move these breadcrumbs to the non-captured parent layer before the long child calls.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review/scripts/review-core.sh:342`: The new nested review breadcrumbs are emitted from scripts whose stdout is redirected into capture files, so they are not operator-visible. `review-and-fix.sh` invokes review-core with `> "$core_out"` at `skills/review-and-fix/scripts/review-and-fix.sh:986`, and review-core invokes dispatch-panel with `> "$dispatch_out"` at `skills/review/scripts/review-core.sh:290`; because `larch_quiet_init` binds FD 3 to the child’s current stdout, breadcrumbs at `skills/review/scripts/review-core.sh:342` and `skills/review/scripts/dispatch-panel.sh:409-411` land in `round-N/review-core.env` / `review-core-dispatch.env` instead of the terminal. Concrete failing scenario: during a long Step 5 reviewer launch or collection phase with `LARCH_QUIET_BREADCRUMBS=1`, the operator still sees no `→ review: launching ...` or `→ review: consolidating findings` progress line. Fix by passing a dedicated inherited progress FD that `larch_quiet_init` does not rebind, or move these breadcrumbs to the non-captured parent layer before the long child calls.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/ship-pr.sh:1526-1530 scripts/ship-pr.sh:1571-1575
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] merged breadcrumb omitted on alternate merge-completion paths version_already_published branch when pr_state is MERGED, and ci-wait ACTION=already_merged, finish merge without the new merged line operators see on merged|admin_merged. Mirror emit_breadcrumb before rename_done_best_effort or narrow ship-pr.md wording.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/ship-pr.md:111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc references non-existent make target `test-ship-pr`. Contributors or automation following ship-pr.md run `make test-ship-pr` and get a Makefile error. Point to `test-ship-pr-state` (etc.) or `bash scripts/test-ship-pr.sh` without `--section`, or add a phony aggregate target.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: scripts/ship-pr.sh:1296-1337
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Merge-conflict breadcrumb only on one rebase failure branch; vendor second-rebase stall omits it. Doc promises "merge conflict on rebase" for that class; operator on vendor conflict path can hit exit_stall after failed second rebase-push with only generic stall line. Emit the conflict breadcrumb before exit_stall when the second rebase-push fails, or narrow ship-pr.md wording to match code.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/ship-pr.sh:merge handling for version_already_published
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Merged breadcrumb not emitted on already_merged completion path. Grepping or dashboards for "merged" miss the path that still finalizes post-merge work. Mirror merged breadcrumb (or equivalent label) when treating version_already_published as merged.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Nit** `code-quality` `skills/review-and-fix/scripts/review-and-fix.sh:231`: The new coder-dispatch failure breadcrumb is skipped when Cursor setup fails before the Cursor agent is launched. If Codex fails and `cursor_launcher_load_model_args` or `cursor_launcher_setup_auth_argv` returns nonzero at `skills/review-and-fix/scripts/review-and-fix.sh:231-232`, the function returns before the breadcrumb at line 247; emit the failure breadcrumb on those early-return paths too.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/review-and-fix/scripts/review-and-fix.sh:231`: The new coder-dispatch failure breadcrumb is skipped when Cursor setup fails before the Cursor agent is launched. If Codex fails and `cursor_launcher_load_model_args` or `cursor_launcher_setup_auth_argv` returns nonzero at `skills/review-and-fix/scripts/review-and-fix.sh:231-232`, the function returns before the breadcrumb at line 247; emit the failure breadcrumb on those early-return paths too.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-ship-pr.sh:520-532
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Phase-entry breadcrumb test omits exit-code assertion A stall after early phases could still print expected substrings and pass greps. Add assert_rc on tmp/rc for the stubbed scenario.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/review-and-fix/scripts/review-and-fix.md:122-129
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb bullet list omits the no-changes halting breadcrumb emitted by review-and-fix.sh. Operators rely on the sibling .md for grep-able contracts; the halting path is undocumented vs code. Add a bullet for the `coder dispatch exited 0 but did not modify the working tree` line (and any other new emits in the same change).
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:231-232
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] run_coder_dispatch returns before failure breadcrumb Codex fails then Cursor launcher setup returns 1 at lines 231-232; no emit_breadcrumb runs so Step 5 shows no FD3 failure crumb despite coder dispatch failing. Add early-return breadcrumbs or a single generic failure emit before each return 1 in run_coder_dispatch.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/review/scripts/dispatch-panel.sh skills/review/scripts/review-core.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New review breadcrumb strings have no harness grep coverage. A regression removes or breaks breadcrumbs in dispatch-panel or review-core without failing CI. Add minimal LARCH_QUIET_BREADCRUMBS=1 string assertions to test-dispatch-panel.sh and test-review-core.sh.
- **Suggested revision**: Address the concern above.


### FINDING_6: architecture: scripts/ship-pr.sh:1520-1536
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] CI watch breadcrumb emitted before early-return skips that never call ci-wait.sh. Stream shows CI watch while run immediately skips waiting (no PR / unavailable / merge-skipped), confusing progress interpretation. Move breadcrumb after skip logic or emit an explicit skipped breadcrumb on those returns.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: skills/review-and-fix/scripts/review-and-fix.md:breadcrumb subsection
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New doc list omits existing no-changes halting breadcrumb. Operators reading only the new subsection underestimate total breadcrumb traffic. Add the halting no-changes bullet to match review-and-fix.sh behavior.
- **Suggested revision**: Address the concern above.


