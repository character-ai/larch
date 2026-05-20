### [rejected] FINDING_11

### FINDING_11: correctness: scripts/compose-review-findings.sh:184-203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] In code-review-oos any non-matching ### while a block is open is appended as inner body so a later ### FINDING_2: Title without [OUT_OF_SCOPE] is merged into the prior OOS record and no second row is emitted. oos.md has FINDING_1 [OUT_OF_SCOPE] then FINDING_2 without tag second heading is swallowed into OOS_C1 prose_body silent loss of separate finding. Restrict inner-### handling to known subsections or flush on unrecognized top-level ### headings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: risk-integration: scripts/compose-review-findings.sh flush_pending rejected path
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Rejected blocks with only legacy header text and no body reviewer line become reviewer panel. Legacy files never gain body line reviewer becomes panel. Ensure producers emit body line or accept data loss.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

### FINDING_14: risk-integration: scripts/compose-review-findings.sh:92-109
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New JSONL keys and outcome value extend the producer contract Downstream tools that assumed only accepted|rejected and no round_num may fail closed or drop records until updated Document the contract bump and ping known consumers; keep jq shape checks in-repo aligned (already partially done in the harness)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/test-compose-review-findings.md:11-12 scripts/compose-review-findings.sh:184-190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy OOS heading path is documented and implemented but not exercised by the regression harness. A typo or logic change in the `### OOS_…:` branch could ship without failing CI while older `oos.md` files stop producing JSONL rows. Add an `oos.md` fixture using `### OOS_1:` (and assert ids/outcome/reviewer/body).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: skills/implement/scripts/step2-implement.sh:123-126 skills/implement/SKILL.md scripts/test-implement-step2-routing.sh skills/implement/scripts/test-step2-dispatch.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Schema-focused branch also changes default implementer selection and waterfall documentation and tests. Omitted --coder runs and routing pins depend on Cursor-first behavior; defects there are unrelated to JSONL schema but ship in the same merge increasing regression and bisect cost. Split PRs or document the implementer default change explicitly for operators and reviewers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/compose-review-findings.sh:74-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] extract_reviewer_from_body duplicates the same anchored awk logic as reviewer_for_block in lib-vote-tally.sh Future edits to reviewer line shapes or edge cases can fix one script and miss the other, reintroducing FINDING vs reviewer mis-attribution or inconsistent parsing across tally vs JSONL export Consolidate into one shared helper or source a tiny common fragment used by both paths
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/compose-review-findings.sh:74-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan text said tighten parse_artifact regex; implementation adds awk helper instead None beyond mild plan/traceability friction Align commit/plan wording with the chosen implementation or refactor to match the originally described approach
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

