### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **`skills/design/references/approval-gates.md`**: Pure documentation-only instruction change to the LLM orchestrator. The dedup-sweep step reads a local file (`plan.txt`) in `$DESIGN_TMPDIR` and uses LLM reasoning — no user-controlled data flows into shell commands, SQL, or templates; no new external communication paths; no auth/secret/crypto surfaces touched. The `plan.txt` content is user-generated and could theoretically contain adversarial prompt-injection content, but this attack surface is pre-existing and identical to all other Gate B plan-processing steps — the dedup sweep does not meaningfully expand it.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`skills/design/references/approval-gates.md`**: Pure documentation-only instruction change to the LLM orchestrator. The dedup-sweep step reads a local file (`plan.txt`) in `$DESIGN_TMPDIR` and uses LLM reasoning — no user-controlled data flows into shell commands, SQL, or templates; no new external communication paths; no auth/secret/crypto surfaces touched. The `plan.txt` content is user-generated and could theoretically contain adversarial prompt-injection content, but this attack surface is pre-existing and identical to all other Gate B plan-processing steps — the dedup sweep does not meaningfully expand it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **`skills/design/scripts/test-read-design-review-budget-invoke.sh`**: Test-harness-only code. PATH manipulation for fakebins is intentional and bounded. The `ln -sf "$(command -v jq)"` symlink is safe. No hard-coded credentials, no untrusted input flowing into shell metacharacter-sensitive contexts, no SSRF, no path traversal with user-supplied paths. The `$RANDOM`-based `missing_rp` name collision risk is negligible in a temp directory.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`skills/design/scripts/test-read-design-review-budget-invoke.sh`**: Test-harness-only code. PATH manipulation for fakebins is intentional and bounded. The `ln -sf "$(command -v jq)"` symlink is safe. No hard-coded credentials, no untrusted input flowing into shell metacharacter-sensitive contexts, no SSRF, no path traversal with user-supplied paths. The `$RANDOM`-based `missing_rp` name collision risk is negligible in a temp directory. The `larch-logs/implement/3D982BC8...` directory is an intentional `/implement` run-log flush per `docs/run-logs.md` and carries no security-relevant code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:38-41` — The three new `mktemp -d` calls (`fakebin`, `fakebin_pyonly`, `fakebin_jqonly`) are created in a batch before the EXIT trap is updated on line 41; under `set -euo pipefail`, if `fakebin_pyonly` mktemp succeeds but `fakebin_jqonly` fails, both `fakebin` and `fakebin_pyonly` are created but not covered by any active trap (the current trap at that point is the line 18 `rm -f "$tmp"` only). The second batch at lines 73-77 (`dt`, `full_dt`, `dt_norp`, `defects_dt`) has the same structure with an even larger window. The original code immediately re-trapped after `fakebin` creation; the new code delays the trap update, amplifying the pre-existing two-directory window to three- and four-directory windows respectively. **Suggested fix:** Update or extend the EXIT trap immediately after each `mktemp -d` call, or create one parent tmpdir once and use subdirectories under it, so a single `rm -rf` in the trap covers all children.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:38-41` — The three new `mktemp -d` calls (`fakebin`, `fakebin_pyonly`, `fakebin_jqonly`) are created in a batch before the EXIT trap is updated on line 41; under `set -euo pipefail`, if `fakebin_pyonly` mktemp succeeds but `fakebin_jqonly` fails, both `fakebin` and `fakebin_pyonly` are created but not covered by any active trap (the current trap at that point is the line 18 `rm -f "$tmp"` only). The second batch at lines 73-77 (`dt`, `full_dt`, `dt_norp`, `defects_dt`) has the same structure with an even larger window. The original code immediately re-trapped after `fakebin` creation; the new code delays the trap update, amplifying the pre-existing two-directory window to three- and four-directory windows respectively. **Suggested fix:** Update or extend the EXIT trap immediately after each `mktemp -d` call, or create one parent tmpdir once and use subdirectories under it, so a single `rm -rf` in the trap covers all children.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: `approval-gates.md` — All three Gate B insertion spots are present and correctly placed: Apply-all bullet (~line 86), Go-through-each batch bullet (~line 87), One-by-one iteration section (~line 100). Each insertion sits textually between the revise step and the `ACTION=EMIT_PLAN` re-emit step, satisfying the plan's position contract.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `approval-gates.md` — All three Gate B insertion spots are present and correctly placed: Apply-all bullet (~line 86), Go-through-each batch bullet (~line 87), One-by-one iteration section (~line 100). Each insertion sits textually between the revise step and the `ACTION=EMIT_PLAN` re-emit step, satisfying the plan's position contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Canonical wording — All four required contract points are present at each spot: re-read freshly revised `plan.txt`, semantic LLM judgment, distinct-context carve-out, breadcrumb of shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` with unconditional firing.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Canonical wording — All four required contract points are present at each spot: re-read freshly revised `plan.txt`, semantic LLM judgment, distinct-context carve-out, breadcrumb of shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` with unconditional firing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: Scope gate — The instruction is absent from Step 2b initial writes, Gate A discussion sub-round revisions, and Gate C; strictly Gate B only.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Scope gate — The instruction is absent from Step 2b initial writes, Gate A discussion sub-round revisions, and Gate C; strictly Gate B only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: `ec_noroot` test (`test-read-design-review-budget-invoke.sh`) — The concern that `dt_norp` (no `run-params.json`) might cause the script to exit-0 before checking `CLAUDE_PLUGIN_ROOT` is not a bug: `invoke-plan-validator-if-not-quick.sh` lines 9–10 check `DESIGN_TMPDIR` and `CLAUDE_PLUGIN_ROOT` via `: "${VAR:?}"` before the `[[ -r "$rp" ]]` check at line 15.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `ec_noroot` test (`test-read-design-review-budget-invoke.sh`) — The concern that `dt_norp` (no `run-params.json`) might cause the script to exit-0 before checking `CLAUDE_PLUGIN_ROOT` is not a bug: `invoke-plan-validator-if-not-quick.sh` lines 9–10 check `DESIGN_TMPDIR` and `CLAUDE_PLUGIN_ROOT` via `: "${VAR:?}"` before the `[[ -r "$rp" ]]` check at line 15.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: New test assertions (unreadable path, sketch\_budget heuristic, jq path, grep-full, all-fallbacks-exhausted, argv/env guards, no-run-params quick skip, defects-found fixture run) — all correctly exercise the intended branches.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - New test assertions (unreadable path, sketch\_budget heuristic, jq path, grep-full, all-fallbacks-exhausted, argv/env guards, no-run-params quick skip, defects-found fixture run) — all correctly exercise the intended branches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:38-41` — Three `mktemp -d` calls (`fakebin`, `fakebin_pyonly`, `fakebin_jqonly`) are created sequentially before the EXIT trap covering them is installed at line 41; under `set -euo pipefail`, a `mktemp -d` failure at line 39 or 40 leaves the already-created dirs unregistered for cleanup and leaking on disk. **Suggested fix:** Re-install the trap immediately after each `mktemp -d` call (e.g., `fakebin=$(mktemp ...); trap '... rm -rf "$fakebin"' EXIT`), or create a single parent dir and use subdirectories beneath it so one `rm -rf` in the trap covers all.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:38-41` — Three `mktemp -d` calls (`fakebin`, `fakebin_pyonly`, `fakebin_jqonly`) are created sequentially before the EXIT trap covering them is installed at line 41; under `set -euo pipefail`, a `mktemp -d` failure at line 39 or 40 leaves the already-created dirs unregistered for cleanup and leaking on disk. **Suggested fix:** Re-install the trap immediately after each `mktemp -d` call (e.g., `fakebin=$(mktemp ...); trap '... rm -rf "$fakebin"' EXIT`), or create a single parent dir and use subdirectories beneath it so one `rm -rf` in the trap covers all.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:73-77` — The same sequential-mktemp-before-trap pattern repeats for `dt`, `full_dt`, `dt_norp`, and `defects_dt` (lines 73–76), with the trap updated only after all four succeed (line 77). The gap for `dt`/`full_dt` was pre-existing, but adding `dt_norp` and `defects_dt` to the unguarded window amplifies it — if either new `mktemp -d` fails, `dt` and `full_dt` leak even though they succeeded. **Suggested fix:** Same as above — update the trap after each creation, or collect all four under one parent tmpdir.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-read-design-review-budget-invoke.sh:73-77` — The same sequential-mktemp-before-trap pattern repeats for `dt`, `full_dt`, `dt_norp`, and `defects_dt` (lines 73–76), with the trap updated only after all four succeed (line 77). The gap for `dt`/`full_dt` was pre-existing, but adding `dt_norp` and `defects_dt` to the unguarded window amplifies it — if either new `mktemp -d` fails, `dt` and `full_dt` leak even though they succeeded. **Suggested fix:** Same as above — update the trap after each creation, or collect all four under one parent tmpdir.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

