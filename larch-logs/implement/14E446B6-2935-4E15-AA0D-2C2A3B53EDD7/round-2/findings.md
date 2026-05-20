### FINDING_1: **Important** `correctness` `skills/review/scripts/collect-findings.sh:281-284` — Once the parser sees `## Commits since merge-base`, `skip=1` is only cleared by canonical `### In-Scope Findings` / `### Out-of-Scope Observations` headings. Concrete failing scenario: reviewer output with a merge-base preamble followed by `## Findings` and `- Real bug in scripts/foo.sh:42` now yields `FINDINGS_COUNT=0`, silently dropping the real finding. Clear `skip` on the next non-preamble heading in addition to the canonical section headings, then continue fail-open parsing.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `skills/review/scripts/collect-findings.sh:281-284` — Once the parser sees `## Commits since merge-base`, `skip=1` is only cleared by canonical `### In-Scope Findings` / `### Out-of-Scope Observations` headings. Concrete failing scenario: reviewer output with a merge-base preamble followed by `## Findings` and `- Real bug in scripts/foo.sh:42` now yields `FINDINGS_COUNT=0`, silently dropping the real finding. Clear `skip` on the next non-preamble heading in addition to the canonical section headings, then continue fail-open parsing.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `security` `scripts/compose-review-findings.sh:228` — The new OOS ingestion reads `round-*/oos.md` directly, but `skills/review/scripts/tally-code-votes.sh:354-359` writes security-tagged accepted OOS blocks there before holding them back from public OOS artifacts. Concrete failing scenario: an accepted OOS block containing unfenced `focus-area = security` is appended to `round-1/oos.md`; `compose-review-findings.sh` now emits it into committed `review-findings-full.jsonl`, exposing prose that the security policy says must remain local. Add the same security-tag classifier/holdback before emitting `code-review-oos` records, or consume a visibility-safe OOS artifact instead.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/compose-review-findings.sh:228` — The new OOS ingestion reads `round-*/oos.md` directly, but `skills/review/scripts/tally-code-votes.sh:354-359` writes security-tagged accepted OOS blocks there before holding them back from public OOS artifacts. Concrete failing scenario: an accepted OOS block containing unfenced `focus-area = security` is appended to `round-1/oos.md`; `compose-review-findings.sh` now emits it into committed `review-findings-full.jsonl`, exposing prose that the security policy says must remain local. Add the same security-tag classifier/holdback before emitting `code-review-oos` records, or consume a visibility-safe OOS artifact instead.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement large trees in diff
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Intentional run logs per project policy not re-audited here. None None
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: branch diff (skills/implement/SKILL.md, step2-implement.sh, plugin.json, CHANGELOG, SECURITY, larch-logs/**, etc.)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Large unrelated behavioral and release-artifact changes ride alongside the compose-review-findings schema work Reviewers must mentally separate multiple features; bisect and rollback become harder if the JSONL work regresses Split unrelated implementer/docs/version/log changes into separate PRs from the schema-gap commit
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: git branch vs implementation_plan Files modified list
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Multiple commits and files (version bumps larch-logs lib-vote-tally routing harness run-logs SECURITY larch-log-batches) are not enumerated in the three-file compose plan. Strict plan-scoped reviewers cannot map one plan section to the whole branch diff without reading the full diff. Optional: expand the plan or PR summary to list all touched surfaces or split unrelated edits.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: scripts/compose-review-findings.sh:219-247
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] IMPLEMENT_TMPDIR tree is read without hardening against symlink or '..' path tricks. Attacker with ability to tamper session tmpdir layout could influence which files are read; same class as pre-existing accepted/rejected paths. Out of scope for this diff; would require root containment at caller or open-time validation if tightened later.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/compose-review-findings.md vs compose-review-findings.sh:74-85
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc emphasizes canonical bold Reviewer line awk also accepts plain Reviewer at line start. None minor doc drift. Align documentation with matcher or narrow matcher.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/compose-review-findings.sh:74-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] extract_reviewer_from_body duplicates the same anchored awk logic as reviewer_for_block in lib-vote-tally.sh Future edits to reviewer line shapes or edge cases can fix one script and miss the other, reintroducing FINDING vs reviewer mis-attribution or inconsistent parsing across tally vs JSONL export Consolidate into one shared helper or source a tiny common fragment used by both paths
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/compose-review-findings.sh:74-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan text said tighten parse_artifact regex; implementation adds awk helper instead None beyond mild plan/traceability friction Align commit/plan wording with the chosen implementation or refactor to match the originally described approach
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/compose-review-findings.sh:113-214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] REJ_C and OOS_C ids restart per parse_artifact so duplicate id across rounds. Two rounds each REJ_C1 consumer keyed on id alone merges distinct findings. Include round in id or document composite key id plus round_num.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/compose-review-findings.sh:184-203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] In code-review-oos any non-matching ### while a block is open is appended as inner body so a later ### FINDING_2: Title without [OUT_OF_SCOPE] is merged into the prior OOS record and no second row is emitted. oos.md has FINDING_1 [OUT_OF_SCOPE] then FINDING_2 without tag second heading is swallowed into OOS_C1 prose_body silent loss of separate finding. Restrict inner-### handling to known subsections or flush on unrecognized top-level ### headings.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/compose-review-findings.sh:74-86
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] extract_reviewer_from_body uses awk -FS ':' on the full line, so reviewer values containing additional ':' characters are reassembled with default OFS spaces, corrupting the stored reviewer string. A hypothetical label like 'Reviewer: team:component' becomes 'team component' in JSONL, mis-attributing findings to downstream consumers. Parse the reviewer line without colon-splitting the value (strip known prefix then take remainder, or use match/substr on the first delimiter only).
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/compose-review-findings.sh flush_pending rejected path
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Rejected blocks with only legacy header text and no body reviewer line become reviewer panel. Legacy files never gain body line reviewer becomes panel. Ensure producers emit body line or accept data loss.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/compose-review-findings.sh:92-109
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New JSONL keys and outcome value extend the producer contract Downstream tools that assumed only accepted|rejected and no round_num may fail closed or drop records until updated Document the contract bump and ping known consumers; keep jq shape checks in-repo aligned (already partially done in the harness)
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-compose-review-findings.md:11-12 scripts/compose-review-findings.sh:184-190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy OOS heading path is documented and implemented but not exercised by the regression harness. A typo or logic change in the ### OOS_…: branch could ship without failing CI while older oos.md files stop producing JSONL rows. Add an oos.md fixture using ### OOS_1: and assert ids outcome reviewer body.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-compose-review-findings.md:11-12 scripts/compose-review-findings.sh:184-190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy OOS heading path is documented and implemented but not exercised by the regression harness. A typo or logic change in the `### OOS_…:` branch could ship without failing CI while older `oos.md` files stop producing JSONL rows. Add an `oos.md` fixture using `### OOS_1:` (and assert ids/outcome/reviewer/body).
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-compose-review-findings.sh:175-199
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] OOS regression test omits reviewer assertion for OOS_C1. Bold Reviewer line extraction could regress for the first OOS record while C2 and C3 paths still pass. Assert OOS_C1 reviewer matches the fixture slot.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/scripts/step2-implement.sh:123-126 skills/implement/SKILL.md scripts/test-implement-step2-routing.sh skills/implement/scripts/test-step2-dispatch.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Schema-focused branch also changes default implementer selection and waterfall documentation and tests. Omitted --coder runs and routing pins depend on Cursor-first behavior; defects there are unrelated to JSONL schema but ship in the same merge increasing regression and bisect cost. Split PRs or document the implementer default change explicitly for operators and reviewers.
- **Suggested revision**: Address the concern above.

