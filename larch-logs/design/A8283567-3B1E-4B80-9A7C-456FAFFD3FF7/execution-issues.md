### External Reviewer Issues

- **Step design Step 2a.2 — launch-review.sh cursor cursor-sketch-generic failed (exit 1)**:
  ```
REVIEWER_FILE=cursor-sketch-generic-output.txt
TOOL=cursor
STATUS=FAILED
EXIT_CODE=1
FAILURE_REASON=Connection lost, reconnecting (attempt 1)... Retry attempt 1... Connection lost, reconnecting (attempt 2)... Retry attempt 2... Connection lost, reconnecting (attempt 3)... Retry attempt 3... T: [resource_exhausted] Error Failed with exit code 1 after 231s. Output size: 0 bytes.
  ```

- **findings aggregator**: merged output failed validation; leaving findings.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
