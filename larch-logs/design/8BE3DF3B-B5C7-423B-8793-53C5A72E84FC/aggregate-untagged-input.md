### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/clarify.py:977-1021; skills/design/SKILL.md:120-152
- **Concern**: Clarify publish path bypasses the new design difficulty contract. Scenario: /design clarify publish can write a replacement larch:plan block through named-block write without validating or syncing difficulty metadata, difficulty labels, or a difficulty-rating.json source. /implement Step 0 can then read a clarified plan with no trustworthy design prior even though /design published it.
- **Proposed resolution**: Add the clarify publish path to the plan: validate or preserve difficulty metadata before named-block write, sync the difficulty label only after successful plan write, and write the run-level difficulty record from a structured rating source.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:399-434; skills/design/SKILL.md:281-325
- **Concern**: Inline design rating still lacks a structured confidence source. Scenario: The proposed inline /design contract only requires a difficulty: tier trailer and rubric injection. The required difficulty-rating.json needs confidence and bounded rationale, so inline fallback or inline drafting can publish a tier but leave the design run record incomplete or synthesized after the fact.
- **Proposed resolution**: Require the inline path to produce the same raw rating sidecar as the drafter path, with predicted_tier, confidence, and rationale, before publication or terminal summary writes consume it.

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:124-127
- **Concern**: Design prior can still lose the low-confidence bump because the plan has the drafter emit a separate single-token `difficulty:` line while the raw sidecar holds `confidence`. Scenario: The shared helper may bump a low-confidence TRIVIAL design rating to MODERATE in `difficulty-rating.json`, but `/implement` Step 0 only reads `difficulty: <TIER>` from the plan. If that line contains the unbumped tier, the applied tier is too low even though the design run recorded low confidence.
- **Proposed resolution**: Make `difficulty:` and the label derive from the validated shared-helper design tier after confidence bumping, or store enough validated prior metadata for `/implement` to apply the same bump; add the prior-extraction test for a low-confidence design rating.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_flush.py:475-520
- **Concern**: Floor recomputation stops at Step 2. Scenario: Step 2 writes difficulty-rating.json before Step 5 review fixes, CI fixes, or later main-agent edits. If those later edits add hooks/foo or redaction code, the pre-ship/final flush only preserves the old file, so applied_tier can remain TRIVIAL despite a required MODERATE floor.
- **Proposed resolution**: Refresh the existing record during pre-ship/final flush by recomputing floors from the current final changed-path set, preserving model ratings and only raising applied_tier/floors_applied.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:410-411; skills/design/SKILL.md:322
- **Concern**: Design low-confidence bump is not pinned in the wire prior. Scenario: The plan keeps only difficulty: <TIER> in the tracking issue and has /implement Step 0 read that single token. If the drafter raw sidecar says predicted_tier=TRIVIAL confidence=low but the metadata line is written as TRIVIAL, the later implement run cannot recover the confidence and the design prior is one tier too low.
- **Proposed resolution**: Define the metadata line and difficulty label as the post-bump design tier, or publish/read enough confidence data for Step 0 to apply the bump before combining with implement and floors.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1632-1648
- **Concern**: [FINDING_9 incomplete] Design plan-review panel-manifest materializer still drops vendor/model attribution. Scenario: plan_review_panel.py rows may gain vendor and resolved-model fields, but write_design_round_meta still calls _materialize_design_panel_manifest, which rewrites committed round-dir panel-manifest.ndjson with only slot, tool, and output. Design plan-review runs would still fail acceptance that panel-manifest.ndjson carry vendor plus model for every slot.
- **Proposed resolution**: Update progress_report._materialize_design_panel_manifest (and any shared copy helper) to pass through vendor and resolved-model fields from plan-review-slots.ndjson, and extend test_plan_review_panel to assert the materialized round-dir panel-manifest.ndjson after write_design_round_meta.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:1-1
- **Concern**: [FINDING_7 incomplete] Design raw-rating sidecar path is unpinned and terminal writers may read tier-only wire metadata. Scenario: The plan requires a design raw-rating sidecar with confidence and rationale, but never pins its tmpdir filename or reader contract. design_summary is told to emit difficulty-rating.json from captured plan metadata on terminal outcomes without Step 5c publish, which is only the single-token difficulty: wire line. Terminal design runs can commit schema-thin records even when the Step 2b sidecar already captured confidence and rationale.
- **Proposed resolution**: Pin one design tmpdir sidecar path in difficulty.py (mirroring scout-coder-manifest.raw.json), have design_step2b and inline /design Step 2b always write it, and make design_publish plus design_summary prefer that sidecar (fallback to wire tier only when absent).

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1632-1648
- **Concern**: Prior plan-review attribution fix is incomplete because the design round materializer still rewrites panel-manifest.ndjson with only slot tool and output. Scenario: The plan adds vendor and resolved-model fields in plan_review_panel.py, but committed design plan-review round manifests are materialized here and would drop those fields, so the acceptance item for panel-manifest.ndjson attribution remains unmet for /design plan-review rows
- **Proposed resolution**: Preserve vendor and resolved-model fields when materializing design panel-manifest.ndjson, or write the committed round manifest from the attributed rows directly

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:307-315
- **Concern**: Standalone /review difficulty logging is silent on applying floor globs from the reviewed diff. Scenario: A /review --diff run that touches hooks or secret/redaction paths can log a scout or fallback TRIVIAL applied_tier because the plan never passes FILE_LIST_FILE or equivalent changed paths into the difficulty writer for floor matching
- **Proposed resolution**: Update the planned /review difficulty write to feed the gathered file list into the shared difficulty CLI and verify that review diff floors raise applied_tier without changing panel routing
