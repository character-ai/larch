### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:105-113
- **Concern**: Harness grep inventory for the `/design` contract rename is incomplete.. Scenario: The plan retitles callsite greps at ~124-127 but does not list `grep -Fq '`/design` marker-first' "$shared_final_summary"'` (~105) or the anti-halt `marker-first profile` pointer (~113). Those pins still require the retired strings, so `make test-harnesses-2` fails after the shared-doc and SKILL anti-halt edits land.
- **Proposed resolution**: Extend `### UPDATED: scripts/test-render-cost-line-callsites.sh` to explicitly replace ~105 with a `/design` Read-always row pin and ~113 with a Read-always readiness-profile anti-halt pin (keep implement marker-first greps at ~106-107 unchanged).

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/final-summary-emit.md
- **Concern**: Read-always profile omits authoritative `FINAL_SUMMARY_PATH` selection when Step 5c stdout carries multiple rows.. Scenario: `step5c_core` emits `FINAL_SUMMARY_PATH` in `_emit_core_kvs` before render; `result_env` can leave that value empty while `_emit_final_summary_marked_from_disk` later emits the real path plus empty readiness markers. An orchestrator that binds the first `FINAL_SUMMARY_PATH=` row skips Read and shows no summary despite a rendered disk file.
- **Proposed resolution**: In the new Read-always section, require: after empty `LARCH_FINAL_SUMMARY_BEGIN/END` markers are present, bind the last non-empty `FINAL_SUMMARY_PATH` from completed notification stdout (or treat empty early rows as non-authoritative); mirror the rule at SKILL.md / `finalize-step5.md` callsites.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:29
- **Concern**: Anti-halt still says "shared verbatim final-summary emit" while markers become empty readiness signals.. Scenario: The plan swaps the profile pointer to Read-always but does not retarget the operative emit phrase. Orchestrators can treat empty marker pairs as a completed verbatim emit and never Read `FINAL_SUMMARY_PATH`, reproducing empty chat after Python stops streaming bodies.
- **Proposed resolution**: At ~line 29 (and the Step 5d "verbatim full-body emit" sibling at ~720), replace marker-body emit language with: parse `FINAL_SUMMARY_PATH` from completed stdout, confirm empty readiness markers, then Read and emit the disk file verbatim.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:105-113
- **Concern**: Harness grep inventory under ### UPDATED scripts/test-render-cost-line-callsites.sh lists only ~124-127 but still-hard-pins at lines 105 and 113 require `/design` marker-first and anti-halt marker-first profile literals that the shared-doc row rename and SKILL anti-halt rewrite will remove. Scenario: An implementer can update the four cited callsite greps and still leave lines 105/113 unchanged; bash scripts/test-render-cost-line-callsites.sh then fails in CI even when runtime and SKILL/shared prose are correct
- **Proposed resolution**: Extend the harness subsection to explicitly replace line 105 with a `/design` Read-always shared-row pin and line 113 with the new anti-halt Read-always readiness cite substring (or retire both with a comment) alongside the 124-127 updates

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:105-113
- **Concern**: Harness grep updates omit anti-halt and shared-binding pins that still require marker-first literals. Scenario: After SKILL.md and final-summary-emit.md switch to Read-always wording, greps at lines 105 (`/design` marker-first` in shared file) and 113 (anti-halt `marker-first profile`) still fail even if lines 124-127 are updated; `make test-harnesses-2` / `test-render-cost-line-callsites.sh` blocks merge
- **Proposed resolution**: Extend `### UPDATED: scripts/test-render-cost-line-callsites.sh` to explicitly replace lines 105 and 113 with Read-always readiness pins (e.g. shared row label and anti-halt pointer substring), not only the four callsite greps at 124-127

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:105-107
- **Concern**: The plan updates the `/design` callsite wording in the skill and reference files, but it does not update the harness assertion that still greps the shared contract for the literal `/design` marker-first row.. Scenario: After the contract row is renamed to the new Read-always readiness wording, this grep will fail CI even if the runtime change is otherwise correct.
- **Proposed resolution**: Update the `shared_final_summary` grep to match the new `/design` readiness-row text, and keep the harness pin on the renamed callsite row.
