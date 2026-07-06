### FINDING_1: [OUT_OF_SCOPE] bash32 lint misses some unsafe probes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The awk-based bash32 lint is still line-local and boundary-limited, so it can miss unsafe `command grep` conditionals after shell separators or across line continuations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Accept as a known static-lint limitation unless a follow-up adds continuation-line joining or a second-pass scan.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] sibling jq-less fallback is still uncovered
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `skills/design/scripts/design-step35.sh` still has a jq-less `elif grep -Eq ...` fallback, so the same bash 3.2 hazard remains there even though this diff only tightened lint coverage elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Out of this change’s scope; if macOS jq-less hosts hit Gate B the same way, apply the subshell probe there and add the script to the residual manifest.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] runtime coverage for bash 3.2 behavior is still missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The current checks only validate static source shape for the jq-less/bash 3.2 fallback; they do not execute that path, so behavioral `set -e` failures can still escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

