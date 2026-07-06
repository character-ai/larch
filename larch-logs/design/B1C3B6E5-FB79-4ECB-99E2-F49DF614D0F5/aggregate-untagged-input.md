### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md
- **Concern**: The Gate C audit does not pin which file is passed to `plan-review filter-gate-b-skipped --accepted`.. Scenario: Step 2 builds the classification set from `accepted-plan-findings-all.md`, but the helper contract only names a generic `--accepted` path. An implementer can pass `accepted-plan-findings.md` (Gate B apply set) and filter the wrong corpus, missing cumulative accepted findings or misclassifying one-by-one skips.
- **Proposed resolution**: In the Accepted plan-review findings audit section, add an explicit filter invocation: `--accepted "$DESIGN_TMPDIR/accepted-plan-findings-all.md"` when that file is non-empty, else `--accepted "$DESIGN_TMPDIR/accepted-plan-findings.md"` (mirror `compose_review.py` precedence), with `--rejected "$DESIGN_TMPDIR/rejected-findings.md"`. State that stdout replaces the classification set input.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md
- **Concern**: Edge case treats absent or empty `accepted-plan-findings-all.md` as no accepted findings.. Scenario: `compose_review.py` falls back to `accepted-plan-findings.md` when `-all` is missing or empty. On upgraded in-flight or post-reentry runs, Gate C can have a non-empty applied file but no cumulative file yet; the audit would persist a false clean note and allow `--skip-approve` despite real accepted findings.
- **Proposed resolution**: Change the edge-case and step-1/2 rules to mirror compose precedence: use non-empty `accepted-plan-findings-all.md`, else non-empty `accepted-plan-findings.md`, else no findings. Apply the same source when calling `filter-gate-b-skipped`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/cli.py
- **Concern**: The plan only conditionally adds `persist-accepted-audit` to `_MACHINE_STDOUT_KEYS`.. Scenario: `ACCEPTED_AUDIT_STATUS=ok` is the fail-closed success signal in step 10, but conditional registration can omit it from the machine-stdout contract and weaken CLI port enforcement (same class as prior neutral on guideline persist).
- **Proposed resolution**: In the `cli.py` update, require adding `("plan-review", "persist-accepted-audit")` to `_MACHINE_STDOUT_KEYS` unconditionally, and assert it in `test_design_cli_ports.py` alongside registry coverage.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:67-67
- **Concern**: Planned fidelity source uses only the active findings file instead of the cumulative applied set. Scenario: Automatic Step 3 can apply accepted findings in round 1, then finish after a later zero-finding round that leaves accepted-plan-findings.md empty or current-round-only. Gate C then compares plan-before-review.txt to final plan without the round-1 accepted findings as allowed sources, so application fidelity is false or unverifiable.
- **Proposed resolution**: Define the Gate C end-state fidelity source as the filtered cumulative accepted-plan-findings-all.md for all Step 3 changes, with accepted-plan-findings.md used only as the active/current Gate B apply file when needed.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md
- **Concern**: [ALREADY_ADDRESSED] Gate C audit step 2 lacks fail-closed handling when filter-gate-b-skipped fails. Scenario: Step 2 runs plan-review filter-gate-b-skipped when rejected-findings.md has the one-by-one marker. The plan does not require aborting on non-zero exit. compose_review already shows the hazard: falling through with unfiltered accepted-plan-findings-all.md misclassifies operator-skipped findings as missing fidelity or strong dissent, and can block --skip-approve.
- **Proposed resolution**: Add to audit step 2 and Failure modes: on filter non-zero, print a bounded warning, stop Gate C before persist/prompt/auto-approve (mirror persist-accepted-audit fail-closed). Optionally pin a structural or pytest case for filter failure at Gate C. ## Findings ### 1. [risk-integration] `python/larch/design/design_log_publish_flow.py:140-150` — [SCOPE-REDUCTION] Intermediate snapshot would land in committed design logs The plan adds `plan-before-review.txt` at Step 3 entry and documents `accepted-plan-findings-audit.md` for run logs, but it never updates the publish exclude list. Today `_PUBLISH_EXCLUDE_TOPLEVEL_NAMES` drops ephemeral snapshots like `issue-body.txt`; anything else at the tmpdir root is copied into `larch-logs/design/<RUN_ID>/`. That commits superseded plan content the feature only needs for Gate C comparison. The binding issue scope asks to persist the audit artifact, not a pre-review plan duplicate. **Suggested fix:** Add `plan-before-review.txt` to `_PUBLISH_EXCLUDE_TOPLEVEL_NAMES`, extend `test_design_log_publish_flow.py`, and list `design_log_publish_flow.py` under `### UPDATED:` in the plan. ### 2. [correctness] `skills/design/references/approval-gates.md` — Gate B filter helper failure is unspecified at Gate C audit Round 1 accepted one-by-one skip filtering (FINDING_4). The revised audit read list calls `filter-gate-b-skipped` when the skip marker is present, but it does not say what happens if that helper exits non-zero. Silent fallback to raw `accepted-plan-findings-all.md` can produce false fidelity failures or strong dissent, including wrongly blocking `--skip-approve`. **Suggested fix:** Fail closed: on filter non-zero, warn, stop Gate C before persist/prompt/auto-approve, same posture as `persist-accepted-audit` failure.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/cli.py:630-680
- **Concern**: `filter-gate-b-skipped` needs `_MACHINE_STDOUT_KEYS` registration, not only registry entry. Scenario: The plan limits machine-stdout registration to verbs that emit status rows, but `filter-gate-b-skipped` prints the filtered findings body on stdout for prompt-side audit classification. Without `_MACHINE_STDOUT_KEYS`, quiet routing can divert that payload away from the Bash capture and Gate C skip filtering silently breaks.
- **Proposed resolution**: Register `("plan-review", "filter-gate-b-skipped")` in `_MACHINE_STDOUT_KEYS`. Pin it in `test_design_cli_ports.py` the same way `persist-design-assessment` is pinned today.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_cli_ports.py:54-65
- **Concern**: `persist-accepted-audit` machine-stdout registration is under-specified. Scenario: Round 1 left `ACCEPTED_AUDIT_STATUS` machine-key coverage neutral. The plan adds registry assertions only; `cli.py` still says register machine keys only when verbs emit status rows. Fail-closed Gate C persistence depends on parsing `ACCEPTED_AUDIT_STATUS=ok` from helper stdout.
- **Proposed resolution**: Add `("plan-review", "persist-accepted-audit")` to `_MACHINE_STDOUT_KEYS`. Extend `test_design_cli_ports.py` to assert registry and machine-stdout membership for `persist-accepted-audit` and `filter-gate-b-skipped`, mirroring `ARCHITECTURAL_GUIDELINES_EXPECTED`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md
- **Concern**: Gate C audit lacks fail-closed handling when skip filtering fails. Scenario: The audit rerun contract fail-closes on `persist-accepted-audit` failure, but step 2 does not define behavior when `rejected-findings.md` contains the one-by-one skip marker and `filter-gate-b-skipped` exits non-zero. The orchestrator could continue with an unfiltered `-all` set and emit false dissent or fidelity failures.
- **Proposed resolution**: When the skip marker is present, require a successful filter helper exit before classification; on non-zero, print a bounded Gate C warning, stop before prompt/auto-approve/Step 5, and preserve `$DESIGN_TMPDIR` for repair (mirror the persist fail-closed block).

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:67
- **Concern**: Fidelity audit treats `accepted-plan-findings.md` as the full applied set. Scenario: `python/larch/review/plan_review_tally.py` clears `accepted-plan-findings.md` for each tally while `accepted-plan-findings-all.md` accumulates accepted findings across automatic continuation rounds. In a two-round Step 3, the pre-review to final diff includes round-1 accepted changes, but the planned Gate C fidelity check compares against only the round-2 current file. The audit can flag valid round-1 edits as unrelated damage or miss whether earlier accepted findings were applied, and `--skip-approve` can be forced into a false strong-dissent prompt.
- **Proposed resolution**: Define the fidelity set as the filtered cumulative `accepted-plan-findings-all.md`, with Gate B one-by-one skips removed, or add a new cumulative applied-set artifact. Use `accepted-plan-findings.md` only as the latest-round/current apply-set hint, not as the end-state diff authority.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md
- **Concern**: Fidelity audit uses last-round `accepted-plan-findings.md` instead of cumulative applied findings. Scenario: `plan_review_tally.py` clears and rewrites `accepted-plan-findings.md` on every tally (lines 659-660) while `_accumulate_round_accepted_all` keeps prior rounds in `accepted-plan-findings-all.md`. After a two-round happy-path loop, Gate C fidelity against `-md` alone treats round-1-applied plan changes as untraced and can false-trigger strong dissent or block `--skip-approve`.
- **Proposed resolution**: In audit step 6, trace end-state fidelity against Gate-B-filtered `accepted-plan-findings-all.md` (the cumulative applied set). Reserve `accepted-plan-findings.md` for the current-round Gate B apply set only. Mirror the same rule in `plan-review.md`.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: Failure mode requires a SKILL.md skip-approve harness pin that the plan never adds. Scenario: The plan failure-modes section requires the structural harness to pin the post-audit `--skip-approve` predicate, but `test-design-structure.sh` updates only `approval-gates.md`. Stale unconditional auto-approve prose in `skills/design/SKILL.md` (~547-549) can survive a correct `approval-gates.md` rewrite and unattended runs still auto-approve before audit.
- **Proposed resolution**: Add structural checks that `skills/design/SKILL.md` requires audit completion, binds `strong_audit_dissent`, and forbids unconditional Gate C auto-approve after Presentation only.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:72-115
- **Concern**: Gate C fidelity uses only the latest accepted-plan-findings.md even though the diff spans the whole Step 3 entry. Scenario: In an automatic two-round Step 3 run, round 1 accepted edits are applied, continuation launches round 2, and top-level accepted-plan-findings.md is overwritten with round 2 findings while accepted-plan-findings-all.md keeps both rounds; the Gate C audit then compares plan-before-review.txt to final plan but cannot trace valid round 1 edits, so it can raise false dissent or miss fidelity for cumulative accepted findings
- **Proposed resolution**: Treat the filtered cumulative accepted-plan-findings-all.md as the end-state applied set for Gate C fidelity, using accepted-plan-findings.md only as latest-round/Gate B context, and update the plan-review.md and approval-gates.md instructions accordingly
