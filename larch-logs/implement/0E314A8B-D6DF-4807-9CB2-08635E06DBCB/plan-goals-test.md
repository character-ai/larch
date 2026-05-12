## Goal
Fix cursor specialist keychain race by serializing concurrent cursor agent startup on Darwin via a mkdir-based lock in launch-review.sh --tool cursor.

## Test plan
- Run /relevant-checks (pre-commit + agent-lint) after changes
- Run make test-launch-review to verify test suite passes
- Re-run 5-parallel specialist test locally to confirm no "Password not found" failures
