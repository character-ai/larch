### OOS_1: [OUT_OF_SCOPE] README omits human GO step after verdict PASS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-verdict-docs-output.txt
- **Severity**: important
- **Concern**: The `/analyze-issues` feature-matrix row at `README.md:196` documents verdict-mode mechanical gating but not the separate human GO step required before token allocation. CLI exit `0` can be misread as sufficient authorization; sibling surfaces (`.claude/skills/analyze-issues/SKILL.md`, `docs/skills.md`, `docs/point-competition.md`) document the two-step contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add one sentence that a committed GO in `docs/ground-truth-verdict.md` is still required after a passing verdict run.
  - From cursor-specialist-testing-output.txt: Add one sentence to the README row mirroring the skills docs.
  - From dyn-dyn-verdict-docs-output.txt: Extend the README description row to say verdict exit `0` is necessary but not sufficient, and that `docs/ground-truth-verdict.md` must record an explicit human GO after reviewing the generated report.

### OOS_2: [OUT_OF_SCOPE] Targeted-fetch degradation untested on live `run_main` path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Targeted-fetch degradation is regression-tested via offline `--filed-issue-details-json` with `__fetch_failed__`, but not via the live `run_main` path that calls `_fetch_filed_oos_issue_details()` and `gh issue view`. A regression in live fetch wiring could still return exit `0` while filed-OOS fate evidence is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a `run_main` verdict test with a monkeypatched `_fetch_filed_oos_issue_details` that injects `__fetch_failed__`.
  - From cursor-specialist-testing-output.txt: Optional monkeypatch test on `run_main --ground-truth-verdict` returning `__fetch_failed__` details for belt-and-suspenders coverage of the live path.

### OOS_3: [OUT_OF_SCOPE] Verdict mode omits gc-slimmed runs from exclusion bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Verdict mode sets `excluded_gc_slimmed_runs` only when a `gc-slimmed` `run_dir` is reached through classifier discovery; diagnostic mode still runs `_ground_truth_gc_slimmed_fallback` for marker-only slimmed dirs. Slimmed dirs with no classifier TSV stay invisible to the verdict corpus exclusion bucket (they still cannot qualify).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Run a verdict-mode gc-slimmed directory scan analogous to the diagnostic fallback so the verdict corpus block reports all slimmed runs.

### OOS_4: [OUT_OF_SCOPE] Severity-slice coverage missing for verdict rendered output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan calls for severity-slice coverage in verdict rendered output; `test_ground_truth_severity_slice_renders_decisive_yes_rows_and_missing_counts` only exercises diagnostic mode. The capstone artifact is meant to paste severity evidence from verdict stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend that test (or add a sibling) with `verdict_mode=True` and assert `"Severity slice for decisive YES votes:"` appears in the returned report text.

### OOS_5: [OUT_OF_SCOPE] Offline reanalysis example in `docs/skills.md` incomplete for verdict replay
- **Reviewer(s)**: dyn-dyn-verdict-docs-output.txt
- **Severity**: latent
- **Concern**: The offline reanalysis paragraph shows `analyze-issues analyze --json …` without the verdict flags that `.claude/skills/analyze-issues/SKILL.md` documents for offline replay. Offline verdict mode works in code, but the canonical skills doc example is incomplete for operators replaying a bulk JSON dump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-verdict-docs-output.txt: Extend the offline example in `docs/skills.md` to include optional `--ground-truth-verdict` and filter flags.

### OOS_6: [OUT_OF_SCOPE] Corpus Gate template does not explain `gate_reason` priority semantics
- **Reviewer(s)**: dyn-dyn-verdict-docs-output.txt
- **Severity**: latent
- **Concern**: When multiple preconditions fail, `_ground_truth_apply_gate` reports only the highest-priority `gate_reason` (incentive, then enrichment, then targeted fetch, then corpus). The committed artifact can show enrichment/targeted-fetch degradation alongside `gate_reason: calibration_incentive_check_unavailable`, but the template does not explain that `gate_reason` is the winning gate, not an exhaustive failure list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-verdict-docs-output.txt: Add a Notes bullet that secondary degradation fields may be present while `gate_reason` reflects fixed gate priority.
