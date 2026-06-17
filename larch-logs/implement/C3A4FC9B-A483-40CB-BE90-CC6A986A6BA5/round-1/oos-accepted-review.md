### OOS_1: [OUT_OF_SCOPE] Empty/invalid `LARCH_PROBE_RETRIES` bypasses health-gate suppression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_max_transient_probe_retries` (`python/agents.py:631-636`) treats any present `LARCH_PROBE_RETRIES` key (including `""` or `"bad"`, which `_env_int` normalizes to `2`) as an explicit override of health-gate suppression. Launch-time health gate (`scripts/lib-external-launcher-common.sh` sets only `LARCH_EXTERNAL_AUTH_RETRIES=1`) can inherit `LARCH_PROBE_RETRIES=""` from the parent shell and run up to 3 internal probes per gate attempt instead of one, regressing fast-fail latency. Plan/docs currently document suppression only when the variable is unset; acceptance requires that contract, but inherited empty/invalid values still bypass it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: treat invalid/empty values as unset for suppression purposes, or have the health-gate caller prefix `LARCH_PROBE_RETRIES=0`.
  - From cursor-specialist-testing-output.txt: Treat invalid/empty LARCH_PROBE_RETRIES as unset for suppression (only explicit valid integers override); add test with AUTH_RETRIES=1 plus empty/invalid PROBE_RETRIES and transient rc==1 asserting one call.


### OOS_2: [OUT_OF_SCOPE] Probe `EXIT_TIMEOUT` has no retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Probe `EXIT_TIMEOUT` (`python/agents.py:866-869`) still returns immediately with no retry. Plan explicitly excludes timeout changes; this is a known partial fix relative to the original bug's cold-start timeout hypothesis. A vendor that times out on the first 30s attempt but would succeed on a second try remains `probe-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: separate scoped change for timeout retry or a higher probe timeout.


