### FINDING_26: [OUT_OF_SCOPE] test harness `bash [[ ]]` vs shipped `sh`-style operator scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Tests use Bash idioms not identical to the shipped audit operator script surface; may be acceptable test-only convention unless repo-wide strict `bash 3.2` parity is required.
- **Suggested revision**: Accept as test-only convention or refactor tests if strict portability is required repo-wide.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated


