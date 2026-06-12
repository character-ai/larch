# test-parse-drafter-output.sh

Offline regression harness for `scripts/parse-drafter-output.py`.

It covers scout sentinel edge cases that should remain local to the shared drafter parser:

- inline `{"archetypes":[]}` prose inside the plan passes;
- fenced scout JSON examples pass;
- an unclosed fence hiding a scout manifest fails closed;
- exact `LARCH_SCOUT_BEGIN` / `LARCH_SCOUT_END` lines inside the plan fail closed;
- malformed post-plan scout JSON is non-fatal and reports `SCOUT_FAIL_REASON=json_parse`.

Run with:

```text
make test-parse-drafter-output
```
