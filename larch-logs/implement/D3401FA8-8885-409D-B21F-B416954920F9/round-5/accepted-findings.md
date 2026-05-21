### FINDING_12: verbal-form dispatch logic duplicated vs `audit-resolve-prs.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Test-side dispatch mirrors production rules; divergence can yield green tests while the skill script misroutes descriptions.
- **Suggested revision**: Add per-form integration tests against the real resolver or share one parser implementation.


### FINDING_15: `audit-preflight` may echo raw `remote.origin.url` on identity parse failure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: PATs or token-in-URL remotes can leak credentials into stdout transcripts and automation captures when normalization fails or URLs are malformed.
- **Suggested revision**: Strip userinfo from URLs or print only owner/repo; never `printf` raw `remote.origin.url` on failure paths.


### FINDING_17: machine-unsafe KV lines from free-text fields (`ERROR`, `RESOLVED_ECHO`, related)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-injection-output.txt
- **Concern**: Embedded newlines/control characters and unescaped `=` in operator-controlled descriptions can append extra stdout lines, spoof keys, or break sed/KV consumers; overlaps newline-safety and injection-shaped stdout parsing hazards.
- **Suggested revision**: Normalize to single-line values (strip/replace controls), length-prefix, JSON-encode a side channel, or build records with `jq -n` and `--arg`/`--argjson` for every field.


### FINDING_18: `jstr()` insufficient escaping breaks hand-built NDJSON in `audit-scan-run.sh`
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Escaping only `\` and `"` lets `\n`/`\r`/`\t`/controls through into concatenated JSON, producing invalid JSON or split NDJSON lines that confuse downstream `jq`.
- **Suggested revision**: Extend `jstr` for common controls or stop hand-building JSON—emit objects with `jq -n` and `--arg` per string field.


### FINDING_23: `audit-resolve-prs.sh` header contradicts real unknown-argv exit behavior
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Header claims exit `0` always while unknown argv exits `1` with stderr only and no stdout KV, diverging from `audit-resolve-prs.md` and misleading automation.
- **Suggested revision**: Update the script header to match the contract (document non-zero exit and absent stdout KV for unknown argv).


### FINDING_24: `audit-pacific-timestamp` header and `.md` omit unknown-argv failure surface
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Header still implies `0` always while extra args exit `1` stderr-only; contract markdown lacks the explicit “no `PACIFIC_TIMESTAMP=` on stdout” warning pattern used elsewhere (e.g. `audit-preflight.md`).
- **Suggested revision**: Fix header exit-code claims and add a short unknown-argv subsection to `audit-pacific-timestamp.md`.


### FINDING_25: `SKILL.md` orchestrator flow diagram under-specifies `audit-resolve-prs.sh` outputs
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: The “Revised Orchestrator Flow” line summarizes only a subset of keys while verbal resolution requires parsing the full set including `ERROR`, `PR_COUNT`, and `IMPLICIT_SINCE_LAST_AUDIT`, risking silent partial-success handling.
- **Suggested revision**: Expand the diagram line to the full key set or add a pointer to `audit-resolve-prs.md`’s authoritative list.


### FINDING_4: manual Pacific timestamp fallback is not real Pacific
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When `TZ=America/Los_Angeles` is unavailable, the manual path uses coarse month bands for DST (not US transition rules), fixed Apr–Oct offsets, and skips civil day/month/year rollover when adjusting from UTC. Late March / early November and UTC-midnight boundaries can yield wrong wall-clock dates/offsets while still exiting 0, mis-dating chain-of-history titles.
- **Suggested revision**: Prefer a real TZ path; otherwise use correct DST/civil-date arithmetic, fail closed, emit an explicit unreliable flag, or fall back to UTC with a clear operator warning—do not present manual output as authoritative Pacific.


### FINDING_5: `normalize_repo` truncates dotted GitHub repo names for `*.git` SSH URLs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Dotted repo segments in SSH URLs like `git@github.com:org/foo.bar.git` can normalize to `org/foo`, disagreeing with `gh`’s `org/foo.bar` and yielding false `PREFLIGHT_OK` repo mismatch.
- **Suggested revision**: Align `.git` URL capture with the non-`.git` pattern so dots are allowed in the repo segment.


### FINDING_8: `audit-compute-counters` silent all-zero deltas when no scan NDJSON matches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Default glob behavior can read zero scan files, producing priors-only output with no warning—wrong `--scan-results-dir` or filename patterns look like a successful empty delta.
- **Suggested revision**: Emit `SCAN_FILES_FOUND=0` (or equivalent) or fail when no matching NDJSON files were read.


