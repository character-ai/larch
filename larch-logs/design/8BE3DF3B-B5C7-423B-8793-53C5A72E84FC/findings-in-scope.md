### FINDING_1: Clarify publish must sync difficulty metadata
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The clarify publish path can replace the `larch:plan` block without validating or syncing difficulty metadata, difficulty labels, or a `difficulty-rating.json` source. That lets `/implement` Step 0 read a clarified plan without a trustworthy design prior, even though `/design` published it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the clarify publish path to the plan: validate or preserve difficulty metadata before named-block write, sync the difficulty label only after successful plan write, and write the run-level difficulty record from a structured rating source.

### FINDING_2: Inline design rating needs a structured sidecar
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The inline `/design` rating path can publish a tier without a structured confidence source. That leaves the required `difficulty-rating.json` incomplete, or synthesized after the fact, because it needs confidence and bounded rationale in addition to the tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require the inline path to produce the same raw rating sidecar as the drafter path, with predicted_tier, confidence, and rationale, before publication or terminal summary writes consume it.

### FINDING_3: Low-confidence design prior must survive wire write
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The design prior can still lose the low-confidence bump when the plan only writes a single-token `difficulty:` line while the raw sidecar holds confidence. `/implement` Step 0 then reads only the plan token, so an unbumped tier can make the applied tier too low even though the design run recorded low confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make `difficulty:` and the label derive from the validated shared-helper design tier after confidence bumping, or store enough validated prior metadata for `/implement` to apply the same bump; add the prior-extraction test for a low-confidence design rating.
  - From Codex-Pragmatic: Define the metadata line and difficulty label as the post-bump design tier, or publish/read enough confidence data for Step 0 to apply the bump before combining with implement and floors.

### FINDING_4: Final flush must recompute floor upgrades
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Floor recomputation stops at Step 2. Later edits can add hooks or redaction code, but the pre-ship/final flush keeps the older `difficulty-rating.json`, so `applied_tier` can stay `TRIVIAL` even when the final changed-path set now requires a `MODERATE` floor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Refresh the existing record during pre-ship/final flush by recomputing floors from the current final changed-path set, preserving model ratings and only raising applied_tier/floors_applied.

### FINDING_5: Design panel manifests must preserve vendor/model
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The design plan-review panel-manifest materializer still drops vendor and resolved-model attribution. That means committed `panel-manifest.ndjson` can lose the fields that plan-review rows gained, so the acceptance condition for per-slot vendor plus model remains unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update progress_report._materialize_design_panel_manifest (and any shared copy helper) to pass through vendor and resolved-model fields from plan-review-slots.ndjson, and extend test_plan_review_panel to assert the materialized round-dir panel-manifest.ndjson after write_design_round_meta.
  - From Codex-Requirements: Preserve vendor and resolved-model fields when materializing design panel-manifest.ndjson, or write the committed round manifest from the attributed rows directly

### FINDING_6: Design sidecar path and terminal readers need pinning
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The design raw-rating sidecar path is unpinned, and terminal writers may fall back to tier-only wire metadata. Even when Step 2b captures confidence and rationale, terminal design runs can still commit schema-thin records if `design_summary` rebuilds `difficulty-rating.json` from plan metadata instead of a stable sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin one design tmpdir sidecar path in difficulty.py (mirroring scout-coder-manifest.raw.json), have design_step2b and inline /design Step 2b always write it, and make design_publish plus design_summary prefer that sidecar (fallback to wire tier only when absent).

### FINDING_7: Review difficulty logging must apply diff floors
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Standalone `/review` difficulty logging does not clearly apply floor globs from the reviewed diff. A `/review --diff` run that touches hooks or secret/redaction paths can still log a scout or fallback `TRIVIAL` applied tier if the changed-path list is never fed into the difficulty writer for floor matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the planned /review difficulty write to feed the gathered file list into the shared difficulty CLI and verify that review diff floors raise applied_tier without changing panel routing
