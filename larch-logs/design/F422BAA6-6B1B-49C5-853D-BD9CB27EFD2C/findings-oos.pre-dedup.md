### OOS_1: Scrub-fatal routing keys only on `publish.returncode != 0` without `RECOVERY_BRANCH`, so any future or rare `design log-publish` exit 1 that is not scrub-related (for example invalid `--repo` at line 395) would be reported as scrub-fatal rc 5 / `failed-publish-tail`
- **Description**: Scrub-fatal routing keys only on `publish.returncode != 0` without `RECOVERY_BRANCH`, so any future or rare `design log-publish` exit 1 that is not scrub-related (for example invalid `--repo` at line 395) would be reported as scrub-fatal rc 5 / `failed-publish-tail`. Scenario: Step 5c normally passes a validated `REPO`, so this is unlikely in production, but failure taxonomy and SECURITY.md scrub wording could overstate scrub when the subprocess died for argv validation
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/design_publish.py:420-443
- **Phase**: design



### OOS_2: Shared helper coercion uses audit `int(str(value))` while fluff today uses `int(value)`; boolean counts would diverge (`True` → 1 today, 0 after extraction)
- **Description**: Shared helper coercion uses audit `int(str(value))` while fluff today uses `int(value)`; boolean counts would diverge (`True` → 1 today, 0 after extraction). Scenario: Committed self-review tally fixtures use integer counts today, so historical fluff output likely stays unchanged; the drift risk is only for malformed or hand-edited tally JSON
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:216-220
- **Phase**: design



