### FINDING_1: **Important** `correctness` `scripts/larch-log.sh:92`, `scripts/scout-dynamic-archetypes.sh:290` — The newly committed `.raw` scout sidecar is not always the raw Claude output. If Claude returns prose-wrapped fenced JSON, `scout-dynamic-archetypes.sh` calls `extract_valid_fenced_json "$raw_output" "$raw_output"`, which overwrites `${OUTPUT}.raw` with the extracted JSON before `write-round` commits it. Concrete scenario: Claude outputs `Here is the JSON:\n```json\n{...}\n````; the committed `scout-roundN-manifest.json.raw` loses the prose and fences, so the sidecar no longer supports debugging the actual model response. Write the fenced/normalized JSON to a separate temp file for parsing and leave `${OUTPUT}.raw` untouched; add a regression assertion for the existing `fence-with-prose` case.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/larch-log.sh:92`, `scripts/scout-dynamic-archetypes.sh:290` — The newly committed `.raw` scout sidecar is not always the raw Claude output. If Claude returns prose-wrapped fenced JSON, `scout-dynamic-archetypes.sh` calls `extract_valid_fenced_json "$raw_output" "$raw_output"`, which overwrites `${OUTPUT}.raw` with the extracted JSON before `write-round` commits it. Concrete scenario: Claude outputs `Here is the JSON:\n```json\n{...}\n````; the committed `scout-roundN-manifest.json.raw` loses the prose and fences, so the sidecar no longer supports debugging the actual model response. Write the fenced/normalized JSON to a separate temp file for parsing and leave `${OUTPUT}.raw` untouched; add a regression assertion for the existing `fence-with-prose` case.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: larch-logs/implement/*/code-review-tally.json (committed snapshots)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Snapshotted tally bodies may show older column/token labels than post-rename scripts. Readers of historical logs could see mixed vocabulary vs current `tally-code-votes.sh` output. Out of scope: intentional frozen run logs; update only if regenerating snapshots.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: Branch diff vs #2373 Phase 1
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Commits/diffs bundle #2381 voting-doc/test changes, version/changelog touches, and larch-logs flush with the scout allow-list work. Reviewers may treat PR as single-issue while rebasing/splitting/conflict surface spans unrelated areas. Split PRs or narrow PR description to list all issue IDs and change classes.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: Branch vs main (git log merge-base..HEAD)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Three-commit stack: larch-logs flush, scout raw, NEUTRAL to JUDGE_ERROR rename. Review scope blur when triaging regressions to a single issue. Partition review by commit or by issue when bisecting.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: CHANGELOG.md:14-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] 29.8.16 section only records `Closed: #2376` without per-feature bullets for stacked commits. Readers auditing what 29.8.16 shipped may not tie the tag to scout `.raw` logging or voter vocabulary unless #2376 is the umbrella issue. If desired, expand changelog bullets or cross-link issues; not a functional bug in scout or larch-log.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh (check_voter_parse_rate awk)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Parallel awk vote logic remains duplicated vs `lib-vote-tally.sh` `vote_for_id`. Future threshold edits could drift between copies. Out of scope: pre-existing; optional follow-up refactor to source shared helper.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/scout-dynamic-archetypes.md (new ${OUTPUT}.raw invariant)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New doc claims .raw is always subprocess-verbatim for every outcome. When Claude returns fence-wrapped JSON, scout replaces ${OUTPUT}.raw with extracted JSON (mv in extract_valid_fenced_json), so committed scout-roundN-manifest.json.raw can differ from true subprocess output; readers trust the wrong invariant. Align wording with actual behavior (verbatim only until fence normalization) or add a separate immutable raw artifact if verbatim is required.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/scout-dynamic-archetypes.md (new invariant bullet)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Doc claims scout `${OUTPUT}.raw` is committed verbatim via `larch-log.sh write-round`. Investigators comparing committed `round-N/scout-round*-manifest.json.raw` to the session tmpfile may believe redaction or staging failed because bytes differ after `larch_log_redact_file`. Clarify: on-disk sidecar next to OUTPUT is verbatim; committed copy is staged through the same tmpdir/secret redaction as other round artifacts (see `stage_round_artifact` + `larch_log_redact_file`).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/scout-dynamic-archetypes.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New invariant claims scout `${OUTPUT}.raw` is verbatim for every Claude outcome and is committed unchanged by write-round. An operator diffs round-N `scout-round*-manifest.json.raw` against the live subprocess transcript after a fenced-json scout success, or audits secrets, and assumes byte identity with launcher stdout; committed files are redacted (`larch_log_redact_file`), fence success rewrites `.raw` to extracted JSON, and `--max-archetypes 0` never creates `.raw`. Reword to separate launcher capture, optional in-place fence extraction, redaction on `write-round`, and the max-archetypes-zero no-launch path.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/scout-dynamic-archetypes.md:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New invariant claims ${OUTPUT}.raw is verbatim for every Claude outcome. When Claude returns fence-wrapped JSON, extract_valid_fenced_json overwrites ${OUTPUT}.raw with extracted JSON (scout-dynamic-archetypes.sh:290-299), so round-committed .raw can differ from the launcher file; contradicts lines 17-18 in the same doc. Reword to describe possible in-place fence normalization; optionally document that tests only byte-compare raw for non-fence paths.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/scout-dynamic-archetypes.md:22;scripts/scout-dynamic-archetypes.sh:131-157,215-221,290-293
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New doc claims scout `${OUTPUT}.raw` is always verbatim for every Claude outcome. Fence-wrapped ok runs rewrite `${OUTPUT}.raw` in place via `extract_valid_fenced_json`; `--max-archetypes 0` exits before any `${OUTPUT}.raw` exists. Operators or downstream tooling expecting true launcher-byte fidelity or a universal sidecar can misread committed round artifacts. Align `scout-dynamic-archetypes.md` wording with `scout-dynamic-archetypes.sh`: describe `.raw` as parse-input path, note in-place fence normalization on success, and note no sidecar when launch is skipped.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/design/scripts/tally-plan-review.md:19
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Quorum bullet uses phrase not the per-finding non-JUDGE_ERROR response count. Readers may misunderstand whether tier/quorum is derived from per-finding vote tallies vs panel eligible count; weakens the contract doc introduced in this branch. Rewrite to explicitly restate panel-level eligible basis without ambiguous non-JUDGE_ERROR phrasing; keep JUDGE_ERROR does not reduce tier as a separate clear sentence.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: Branch commits 924f1395 80baaf78 ffba6966 vs main
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unrelated #2381 vocabulary sweep and larch-logs flush ride with #2373 scout sidecar work in one diff range. Revert/bisect/cherry-pick for one concern affects unrelated tally and committed run-log surfaces. Split merges or use a stacked branch/PR sequence per issue.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: branch vs main (merge-base 7ee70f61; commits ffba6966 80baaf78 924f1395)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Multiple independent change themes ship in one branch diff (scout raw logging, tally rename, larch-logs flush). CI or local failures become harder to attribute and revert surgically; bisect points to a large commit set. Split PRs by concern or document/execute a full combined test matrix before merge.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-scout-dynamic-archetypes.sh:93-253
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] `assert_raw_matches` is not used for fence-wrapped scout cases where `.raw` content intentionally diverges from the stub fixture file. After doc fixes, fence regressions could slip without a test that pins the post-extraction `.raw` shape. Add expectations for stripped-json bytes (or document explicitly that only non-fence paths are cmp-stable).
- **Suggested revision**: Address the concern above.

