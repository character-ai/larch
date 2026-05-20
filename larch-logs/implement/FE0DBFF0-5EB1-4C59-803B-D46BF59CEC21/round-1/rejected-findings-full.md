### [rejected] FINDING_13

### FINDING_13: architecture: scripts/session-setup.sh:212 docs/installation-and-setup.md:242-248
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] emit used vs stated stderr warning Quiet sessions route emit to FD3 not literal stderr Also larch_err or reword docs to contract-visible
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_26

### FINDING_26: correctness: scripts/check-stale-plugin.sh:387-398
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] extract_version is first-match grep on any line containing the substring version Wrong or empty semver if an earlier JSON line also contains a version token, misclassifying skew Use jq when available or stricter top-level parsing
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

### FINDING_27: correctness: scripts/check-stale-plugin.sh:77-83
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Grep-based version extraction uses the first "version" match Version skew detection can be wrong or misleading for unusual JSON ordering Tighten the pattern or document/limit the JSON shape assumed
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

### FINDING_29: correctness: scripts/check-stale-plugin.sh:90-105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Awk numeric coercion mangles non-numeric semver tails If versions ever include pre-release tokens, ordering may be wrong Compare numeric triples only or adopt repo semver policy
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

### FINDING_30: correctness: scripts/check-stale-plugin.sh:93-104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] version_cmp compares only three semver segments Fourth segment differences compare as equal skew or match signals wrong Document 3-tuple limit or compare all split segments up to a cap
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

### FINDING_32: correctness: scripts/session-setup.sh:207-212
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Warning uses emit (FD3) not stderr (FD4) per lib-quiet semantics Automation or tooling that only captures stderr never sees the version-skew banner despite STALE_PLUGIN_CHECK=working-tree-ahead Use larch_err/larch_errf for the banner or align docs/requirements with emit-based visibility
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_33

### FINDING_33: risk-integration: docs/installation-and-setup.md:235-250
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Documents a stderr warning but implementation uses emit (stdout/FD3 per lib-quiet) Operators look on stderr and miss guidance; docs disagree with runtime behavior Align wording with emit / Bash tool visibility
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_34

### FINDING_34: risk-integration: docs/installation-and-setup.md:235-250
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Feature text says stderr; implementation uses emit/lib-quiet stream Acceptance wording mismatch; not a CI break unless stderr is mandatory Align docs/issue wording with emit contract or switch to larch_err if stderr required
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_42

### FINDING_42: security: scripts/session-setup.sh:206-212
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plugin.json version strings are embedded in orchestrator-visible emit text without validation A compromised or malformed plugin.json could inject long or instruction-like text into the session banner consumed as operational context Validate semver (or strip/limit) before emitting; omit raw values when invalid
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

