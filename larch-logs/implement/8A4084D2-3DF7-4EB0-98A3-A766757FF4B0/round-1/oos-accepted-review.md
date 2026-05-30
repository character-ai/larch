### FINDING_13: [OUT_OF_SCOPE] test-mermaid harness tolerates missing mmdc
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-mermaid-fragments.sh` can pass nested-fence lint without resolving `mermaid-lint/node_modules/.bin/mmdc`; only the lint-mermaid job covers the repointed path (pre-existing gap, file untouched by this branch). Consider tightening the harness or adding a cheap path probe for stronger regression signal later.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] Puppeteer --no-sandbox CI fallback pre-existing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-mermaid-fences.sh` Puppeteer `--no-sandbox` render fallback for CI is pre-existing. Dev/CI Chromium runs without sandbox on Linux runners; local dev risk unchanged by this PR. No change required here; track separately if hardening CI sandbox is desired.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_15: [OUT_OF_SCOPE] Global mmdc PATH fallback trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Global mmdc PATH fallback is pre-existing. A malicious `mmdc` earlier on PATH could run during local lint. Prefer repo-pinned binary only or document PATH trust for dev setups.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] SECURITY.md omits sparse-install payload boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` omits sparse-install payload boundary. Security auditors reading `SECURITY.md` alone may miss what consumer installs exclude. Add a sparse-install trust paragraph when `SECURITY.md` is next edited in sync.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] recover() ERR banner omits marketplace remove
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `recover()` ERR banner omits marketplace remove before sparse re-add (and related uninstall/marketplace teardown). Manual recovery after partial failure or mid-pipeline failure may fail on stale marketplace registration or add conflicts. Pre-existing; optional follow-up to extend `recover()` with full teardown sequence.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] docs/skills.md catalog stale (plan out of scope)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Catalog text still describes remove+re-add marketplace flow. Readers of `docs/skills.md` get an outdated mental model vs `upgrade-larch.md` and `SKILL.md`. Update the `/upgrade-larch` section to match sparse checkout and in-place marketplace update (not in plan file list).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_22: [OUT_OF_SCOPE] Fresh install docs omit --sparse (plan follow-up)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Fresh install docs omit `--sparse`. New installs via the Install section still get a full clone until first `/upgrade-larch`. Consider sparse marketplace add on first install in a follow-up (explicitly out of plan scope).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_23: [OUT_OF_SCOPE] LARCH_SPARSE_DIRS CLI usage is correct
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: nit
- **Concern**: `LARCH_SPARSE_DIRS` usage is correct: CLI paths use intentional word-splitting with `# shellcheck disable=SC2086`; recovery and verification strings only echo the expanded command for copy-paste and do not execute it.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected


