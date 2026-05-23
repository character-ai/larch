### FINDING_11: Harness/plan doc fixture count (16 vs 22) misaligned
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implementation plan / sibling doc still claim 16 fixtures while the harness contract lists 22 numbered cases plus Family A checks, creating a false completeness gap for maintainers and plan-adequacy checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Unreleased CHANGELOG contradicts strict-file / Filed URL line narrative
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Unreleased changelog still describes design OOS URLs satisfying the gate via loose `--filed-urls-file` only, conflicting with the strict-file / Filed URL line rule under [42.0.10] and risking re-opening the disposition loophole narrative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Heredoc / backslash-continuation coverage and heredoc false-positive risk
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: No heredoc (or similar) negative fixture: `${CLAUDE_PLUGIN_ROOT}/…denylist…`-shaped text inside a heredoc could false-positive as an anchor and force markers on tutorial fences; the implementation plan also promised heredoc and `\`-continued denylisted-invocation fixtures, but the harness omits them, so regressions on those shapes may ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Family A harness pins exact counts; any increase breaks CI
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Family A harness pins exact `grep -cF` equality to fixed counts, which is stricter than plan language that only forbids decreases: adding a legitimate new parallel-launch prose line can fail CI (e.g. 9→10) without a Family B regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


