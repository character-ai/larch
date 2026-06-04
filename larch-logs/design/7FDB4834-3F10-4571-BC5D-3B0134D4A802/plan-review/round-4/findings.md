### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:119-122
- **Concern**: Structure-test pin 9 requires NEVER #5 **How to apply** to omit the substring `run-statistics`, but the same PR narrows NEVER #5 to state that `run-statistics` remains owned by the post-checkpoint Step 8+ block (plan.txt:81-82).. Scenario: Implementer adds the required ownership sentence; `grep -Fq run-statistics` on the NEVER #5 paragraph still matches and the harness fails (or the author drops the ownership sentence to green the test).
- **Proposed resolution**: Scope the guard: e.g. assert `batch run-statistics` is absent only between `idempotent-rerun` and the fork carve-out, or pin a positive sentinel-only phrase such as `append … --batch oos-issues` without a paired `write … --batch run-statistics` on that branch.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1191-1195; python/ship.py:131-138
- **Concern**: Proposed manifest harvest runs only inside Step 9a.1, but the OOS trigger paths do not consider manifest-only OOS observations. Scenario: Python/Codex writes only manifest.oos_observations; ship-pr never sets OOS_PENDING and python never returns oos-filing, so the new harvest procedure is unreachable and the OOS item is silently skipped
- **Proposed resolution**: Move the manifest harvest before the ship-pr/python OOS trigger decision or update both trigger paths to materialize/check manifest.oos_observations using the same source-resolution contract before deciding no OOS is pending

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:80-81 / skills/implement/SKILL.md:955
- **Concern**: Python `oos-filing` dispatch is scoped to the `/issue` pipeline only, while the new `oos-pipeline.md` procedure is steps 1–7 (inputs, idempotency, combine/cap/deps, `/issue`, `oos-issues` NDJSON, checkpoint handoff). Scenario: On `LARCH_SHIP_PR_IMPL=python`, an implementer following the plan can run only step 4 after `needs_user_reason=oos-filing`, skipping manifest harvest/merge, cap/deps pre-passes, `oos-issues` accepted-row writes, and step 7 return to `oos-disposition-checkpoint.sh`; `ship.py` may keep returning `oos-filing` or pass `disposition_ok` without the same evidence bash uses
- **Proposed resolution**: In the Python driver selector (and matching plan bullet), require the full Step 9a.1 procedure from `oos-pipeline.md` (steps 1–7), not “`/issue` pipeline” alone; state that `oos-filing` must mirror the **OOS checkpoint** sequencing (pipeline → checkpoint → post-checkpoint `run-statistics` when checkpoint exits 0) before reinvoking `python3 …/ship.py`

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/codex-manifest-schema.md:3-7; skills/implement/references/oos-pipeline.md:proposed Step 1
- **Concern**: Proposed manifest harvest makes Step 9a.1 parse MANIFEST_PATH despite the manifest contract saying the orchestrator only handles the manifest path and never parses manifest JSON in-prompt. Scenario: Implementer follows the new reference while the schema doc still says the opposite, leaving two sources of truth for oos_observations consumption and risking future silent OOS filing drift
- **Proposed resolution**: For this minimum-change PR, drop the manifest harvest and its structure pin from oos-pipeline; if harvest is materially required, move it into an existing helper or dispatcher path and update codex-manifest-schema.md in the same change

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:40-45
- **Concern**: Step 3.5 groups exit-0 empty TSV with non-zero helper failure under one degraded-continue rule, while step 4 correctly gates --intra-batch-deps-file on exit-0 non-empty TSV only. Scenario: Oos-pipeline.md could treat a successful no-conflict pre-pass (exit 0, empty TSV) like a failure path—surfacing Tool Failures warnings or skipping Phase-2-only dep analysis semantics that SKILL.md and oos-file-conflict-deps.md treat as normal
- **Proposed resolution**: Split step 3.5: exit 0 + empty TSV → omit --intra-batch-deps-file (normal); non-zero → warning + Tool Failures + omit flag. Keep step 4 gate unchanged.

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1192-1194; python/ship.py:131-139
- **Concern**: Manifest harvest is documented inside the OOS pipeline, but the runtime entry predicates only look for accepted-OOS markdown files before entering that pipeline. Scenario: An external implementer can emit only MANIFEST_PATH oos_observations[]; no oos-accepted-main-agent.md exists yet, so ship-pr or the Python gate can proceed to PR creation without ever loading oos-pipeline.md or filing those OOS items
- **Proposed resolution**: Materialize or detect MANIFEST_PATH oos_observations before the existing OOS_PENDING or Python OOS gate decision, or write them to oos-accepted-main-agent.md during the dispatcher so the existing file-based trigger fires

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/oos-pipeline.md:33-36
- **Concern**: Step 3.4 only names the combine cascade (Rule A → Rule B → criteria 1-4 → 5 → 6) and worksheet outputs; it does not require porting the executable Rule A/B/criteria 1-6 and `oos-grouping-worksheet.md` contract from the git skeleton (`c53086d96^:skills/implement/references/anchor-template-oos-pipeline.md`). Full combine semantics exist only in that deleted anchor; current `skills/implement/SKILL.md` summarizes Rules A/B at ~459 but does not define them. Structure tests pin only the `3.4` / `3.4b` labels, not combine body text.. Scenario: An implementer following the NEW-file bullets can ship a thin `oos-pipeline.md` that cites the cascade without the merge rules. Agents with a mandatory read of that file before `/issue` would lack deterministic guidance for grouping, hard-combine overrides, and worksheet rows — undermining “restore the lost canonical Step 9a.1 procedure” without changing runtime helpers.
- **Proposed resolution**: In `### NEW: skills/implement/references/oos-pipeline.md` step 3.4, explicitly require reconstructing Rule A, Rule B, criteria 1-6, and the grouping-worksheet format from the git skeleton (gate-aligned security predicate, no anchor/PR-body surfaces), or cross-reference a single in-repo section that already contains that full text; add at least one fixed-string guard for a distinctive Rule A or worksheet anchor if hollow 3.4 prose is a concern.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-reference-traceability
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:181,197-198
- **Concern**: Failure modes claim fixed-string count for two load directives while Testing strategy and assertion 2 require at least three occurrences in SKILL.md. Scenario: Guard-rot mitigation text contradicts the structure test; implementers may under-wire the Python oos-filing path or write a count check that passes at 2 and misses the third entry
- **Proposed resolution**: Align Failure modes and Approach guard text with assertion 2: three mandatory load directives (Exit 0 OOS branch, OOS checkpoint block, Python needs_user_reason=oos-filing)

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-reference-traceability
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/larch-log-batches.md:84-107
- **Concern**: Plan cites scripts/larch-log-batches.md for the Rejected sub-block contract, but that file only documents compact JSON record shape and does not define the Rejected sub-block; the actual rejected-marker contract lives in skills/implement/SKILL.md:407, skills/implement/SKILL.md:461, and skills/implement/scripts/oos-disposition-gate.md:29-33.. Scenario: Implementer may add oos-pipeline.md with a dead/misleading source citation for rejected OOS disposition evidence, so future readers chase the wrong contract.
- **Proposed resolution**: In the proposed oos-pipeline.md step 6 text, cite SKILL.md OOS carve-outs / Terminal disposition invariant and oos-disposition-gate.md Counting rules for the Rejected sub-block; keep scripts/larch-log-batches.md only for the compact NDJSON record schema.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:40 / plan assertion 8b
- **Concern**: Assertion 8b greps oos-pipeline.md prose only; Step 9a.1 has no scripted larch-log append surface to pin. Scenario: Deleting step 6 gate-suppression wording while an orchestrator still appends partial-batch URLs to oos-issues NDJSON leaves CI green and OOS_PENDING can clear falsely
- **Proposed resolution**: Add a fixed-string pin on the combined suppression fragment (e.g. do not append accepted disposition URL rows plus oos-issues NDJSON) or accept this as doc-only and drop 8b efficacy claims

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-guard-efficacy
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan assertion 9 / skills/implement/SKILL.md:40
- **Concern**: Assertion 9 is grep-testable for doc drift (remove old NEVER #5 run-statistics-on-recovery string; pin oos-pipeline step 3; pin Exit 0/OOS checkpoint post-checkpoint run-statistics) but not runtime ordering. Scenario: NEVER #5 and oos-pipeline can satisfy grep while a live run still writes run-statistics on sentinel recovery before oos-disposition-checkpoint.sh passes
- **Proposed resolution**: Pin the exact narrowed NEVER #5 How to apply sentence as one positive fixed string; treat post-checkpoint ownership pins as necessary not sufficient

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan assertions 1-11 vs Failure modes section
- **Concern**: Three listed failure modes have no structure assertion: design-source resolution order (checkpoint uses DESIGN_TMPDIR then design-export then tmpdir per oos-disposition-checkpoint.sh:155-161), all-already-filed URL evidence materialization, and all-deduplicated batches using duplicate-of URLs as disposition evidence (assertion 7 pins parse tokens only). Scenario: Wrong design-source order or missing duplicate-of URL handling in oos-pipeline.md would not fail test-implement-structure.sh
- **Proposed resolution**: Add minimal fixed-string pins for the three-path design-source order, already-filed URL evidence branch, and treat duplicate-of URLs as valid disposition URLs

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: security
- **Location**: plan assertion 10 / skills/implement/scripts/oos-non-security-block-count.awk:13-14
- **Concern**: Assertion 10 can pass on mere presence of - **focus-area**: without requiring begins with security or the Description-line carve-out from the awk/gate contract. Scenario: Reintroducing a broader focus-area=security substring filter alongside the field-line example would still pass assertion 10 but diverge from oos-non-security-block-count.awk and cause checkpoint failure after filing
- **Proposed resolution**: Pin the full predicate fragment (begins with security plus does not mark for Description prose) or a negative pin rejecting bare focus-area=security as the exclusion rule

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:115-122, skills/implement/SKILL.md:40, skills/implement/scripts/oos-disposition-gate.md:24-31
- **Concern**: F1: Assertions 8b and 9 are specified as proof-by-grep rather than concrete guard strings.. Scenario: An implementation can keep a generic sentence about ISSUES_FAILED or post-checkpoint stats while still leaving the old NEVER #5 run-statistics write or adding gate-visible oos-issues URL rows on partial failure. The gate counts any issue URL from oos-issues.ndjson, so one leaked partial URL can satisfy the filed_urls branch.
- **Proposed resolution**: Replace proof wording with exact fixed-string pins in the runtime reference, plus one negative fixed-string check for the old NEVER #5 sentinel-recovery run-statistics fragment.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47-53, <TMPDIR>/plan.txt:112-114, <TMPDIR>/plan.txt:175
- **Concern**: F2: The duplicate-disposition assertion only pins duplicate output variable names, not their use as disposition evidence.. Scenario: All items can deduplicate, producing ISSUE_<i>_DUPLICATE_OF_URL without ISSUE_<i>_URL. A plan implementation could parse or mention those fields but fail to write duplicate-of URLs into the sentinel and oos-issues evidence, while assertion 7 still passes.
- **Proposed resolution**: Add one fixed-string assertion for the operative contract, such as Treat both created URLs and duplicate-of URLs as valid disposition URLs, scoped to skills/implement/references/oos-pipeline.md.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-guard-efficacy
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17-27, <TMPDIR>/plan.txt:176-178, <TMPDIR>/plan.txt:95-126
- **Concern**: F3: Two listed failure modes have no numbered CI assertion: design-source mismatch and filed-only early-exit evidence.. Scenario: The new reference could lose the checkpoint-aligned design source order, or omit the all-already-filed branch that preserves existing Filed URL evidence, while all 11 planned assertions still pass. Either gap can make Step 9a.1 disagree with oos-disposition-checkpoint.sh.
- **Proposed resolution**: Add minimal fixed-string pins for the three design-source paths and the all-already-filed materialize checkpoint-visible evidence sentence.
