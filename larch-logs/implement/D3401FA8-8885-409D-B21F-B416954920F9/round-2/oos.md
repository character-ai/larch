### FINDING_18: [OUT_OF_SCOPE] `read -a` / PR list parsing “Bash 3.2 breakage” vs documented Bash 3.2 validity
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Concern**: One reviewer claims `read -a` breaks macOS Bash 3.2 for comma PR lists in [`audit-map-runs.sh`](.claude/skills/audit-runs/scripts/audit-map-runs.sh); portability reviewer marks this out-of-scope and asserts `IFS=',' read -r -a` is valid Bash 3.2 array splitting under `#!/usr/bin/env bash`.
- **Suggested revision**: Reconcile with repo portability policy and a real macOS `/bin/bash` 3.2 check; either dismiss with evidence or replace tokenization only if a concrete incompatibility is confirmed.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Lexicographic `started_at` compare is a Bash-feature concern only if timestamps aren’t strict ISO-shaped
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: `[[ "$st" > "$best_started" ]]` is lexicographic; acceptable if inputs share stable ISO-8601 shapes; mixed/partial timestamps would be correctness, not Bash-version portability.
- **Suggested revision**: No Bash-level change required unless timestamp shape guarantees are weakened; if shapes vary, fix upstream normalization instead of string-compare semantics.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] `audit-title.md` vs `audit-title.sh` non-contiguous list formatting mismatch
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Markdown describes size-dependent formatting for non-contiguous PR lists while the shell emits one comma form for all non-contiguous cases—documentation/behavior drift outside the Bash-portability checklist.
- **Suggested revision**: Update docs to match implementation (or change implementation to match docs) so title contracts are single-sourced.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] Human “Scans” table diverges from `scans.tsv` (with partial pre-existing scope note)
- **Reviewer(s)**: dyn-registry-cross-sync-output.txt
- **Concern**: Narrative table omits machine-registered scans (notably `changelog-rebase-conflicts`); at least some older omissions (e.g. `rej-category-blank`) may predate the changelog addition but still contribute to registry/narrative drift.
- **Suggested revision**: Add a row per `scans.tsv` entry or delete the partial table and point readers to `scans.tsv` / [`audit-scan-run.md`](.claude/skills/audit-runs/scripts/audit-scan-run.md); separate “new drift” vs “pre-existing gap” in release notes if useful.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

