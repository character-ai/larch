### OOS_1:
- **Description**: Python finalize.teardown kill parity is not on the live Step 18 path today. Scenario: Production Step 18 calls scripts/implement-finalize.sh teardown only; finalize.teardown is exercised in python/test_finalize.py, so python/finalize.py kill changes do not fix the reported bash exit-144 symptom unless a Python Step 18 cutover is imminent
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:12-17
- **Phase**: design

### OOS_2:
- **Description**: The teardown doc paragraph still describes pgrep -f discovery while implement-finalize.sh uses ps -A plus awk index(). Scenario: Operators debugging stale-process cleanup may look for pgrep and misread actual teardown behavior
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/implement-finalize.md:103
- **Phase**: design

